"""
Digital Force — Skill Registry & Dynamic Loader

This is the bridge that was missing: generated skills are no longer just
written to disk and forgotten — they are indexed, loaded on demand, and
called by agents at runtime.

How it works:
  1. SkillForge saves a skill to backend/agent/skills/generated/<name>.py
  2. SkillRegistry indexes it (name → function signature → description)
  3. Any agent calls: skill_registry.run("skill_name", **kwargs)
  4. The registry dynamically imports and executes the function
  5. The result flows back into the agent's state

Agents that use this:
  - Publisher: checks registry before attempting a platform post
  - Researcher: can call search tools forged for specific data sources
  - SkillForge: re-runs the skill after forging it to confirm it works
"""

import importlib.util
import logging
import json
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "generated"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache: skill_name → loaded module
_loaded_modules: dict[str, Any] = {}

# Skill index: skill_name → { description, function_name, input_params, file_path }
_skill_index: dict[str, dict] = {}


def _load_skill_index():
    """Scan SKILLS_DIR and build the index from all .py files and their sibling .meta.json files."""
    _skill_index.clear()

    for skill_file in SKILLS_DIR.glob("*.py"):
        name = skill_file.stem
        meta_file = skill_file.with_suffix(".meta.json")

        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
            except Exception:
                pass

        _skill_index[name] = {
            "function_name": meta.get("function_name", name),
            "description": meta.get("description", "No description"),
            "input_params": meta.get("input_params", {}),
            "display_name": meta.get("display_name", name.replace("_", " ").title()),
            "created_at": meta.get("created_at", "unknown"),
            "file_path": str(skill_file),
        }

    logger.info(f"[SkillRegistry] Indexed {len(_skill_index)} skills: {list(_skill_index.keys())}")


def _import_skill(skill_name: str) -> Any:
    """Dynamically import a skill module from disk (cached)."""
    if skill_name in _loaded_modules:
        return _loaded_modules[skill_name]

    skill_path = SKILLS_DIR / f"{skill_name}.py"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' not found at {skill_path}")

    spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", skill_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for skill '{skill_name}'")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    _loaded_modules[skill_name] = module
    logger.info(f"[SkillRegistry] Loaded skill module: {skill_name}")
    return module


def _hot_patch_skill(skill_name: str, old_selector: str, new_selector: str) -> bool:
    """Overwrites the python file on disk to patch a broken DOM selector."""
    file_path = SKILLS_DIR / f"{skill_name}.py"
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        if old_selector in content:
            content = content.replace(old_selector, new_selector)
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"[SkillRegistry] Hot-patched {skill_name}.py: '{old_selector}' -> '{new_selector}'")
            return True
    return False


async def run_skill(skill_name: str, **kwargs) -> dict:
    """
    Load and execute a generated skill by name.

    Returns the skill's return dict, always including a "success" key.
    Example:
        result = await run_skill("post_to_mastodon", text="Hello!", instance="mastodon.social")
    """
    if skill_name not in _skill_index:
        _load_skill_index()

    if skill_name not in _skill_index:
        return {"success": False, "error": f"Skill '{skill_name}' does not exist in registry"}

    try:
        module = _import_skill(skill_name)
        func_name = _skill_index[skill_name]["function_name"]
        func = getattr(module, func_name, None)

        if func is None:
            return {"success": False, "error": f"Function '{func_name}' not found in skill module"}

        import asyncio
        if asyncio.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = func(**kwargs)

        if not isinstance(result, dict):
            result = {"success": True, "result": result}

        # ─── DOM AUTO-HEALER ──────────────────────────────
        if not result.get("success") and result.get("error_type") == "TimeoutError" and result.get("screenshot_path"):
            old_selector = result.get("failed_selector", "")
            logger.warning(f"[SkillRegistry] TimeoutError detected in {skill_name}. Engaging Vision Healer for '{old_selector}'...")
            
            from agent.llm import heal_dom_selector
            new_selector = await heal_dom_selector(
                screenshot_path=result.get("screenshot_path"),
                failed_selector=old_selector
            )
            
            if new_selector and new_selector != old_selector:
                logger.info(f"[SkillRegistry] Vision Healer mapped new selector: {new_selector}. Hot-patching...")
                patched = _hot_patch_skill(skill_name, old_selector, new_selector)
                if patched:
                    # Evict module cache and retry with the patched source
                    _loaded_modules.pop(skill_name, None)
                    module = _import_skill(skill_name)
                    func = getattr(module, func_name, None)
                    if func:
                        import asyncio
                        logger.info(f"[SkillRegistry] Retrying {skill_name} with healed selector.")
                        if asyncio.iscoroutinefunction(func):
                            result = await func(**kwargs)
                        else:
                            result = func(**kwargs)
        # ──────────────────────────────────────────────────

        logger.info(f"[SkillRegistry] Ran '{skill_name}' → success={result.get('success')}")
        return result

    except Exception as e:
        logger.error(f"[SkillRegistry] Error running skill '{skill_name}': {e}")
        return {"success": False, "error": str(e), "skill": skill_name}


def list_skills() -> list[dict]:
    """Return all registered skills with their metadata."""
    _load_skill_index()
    return [
        {"name": name, **meta}
        for name, meta in _skill_index.items()
    ]


def skills_for_task(task_description: str) -> list[str]:
    """
    Find skills that might be relevant to a given task description.
    Simple keyword match — good enough for routing decisions.
    """
    _load_skill_index()
    task_lower = task_description.lower()
    matches = []
    for name, meta in _skill_index.items():
        searchable = f"{name} {meta.get('description', '')} {meta.get('display_name', '')}".lower()
        # Score: count of words from task that appear in skill metadata
        score = sum(1 for word in task_lower.split() if len(word) > 3 and word in searchable)
        if score > 0:
            matches.append((score, name))

    matches.sort(reverse=True)
    return [name for _, name in matches[:5]]


def save_skill_metadata(skill_name: str, meta: dict):
    """
    Save skill metadata alongside the .py file so the registry can describe it.
    Called by SkillForge immediately after saving the .py file.
    """
    meta_file = SKILLS_DIR / f"{skill_name}.meta.json"
    meta_file.write_text(json.dumps(meta, indent=2))
    # Reload index to pick up new skill
    _load_skill_index()
    # Evict the module from cache so it's re-imported if it changed
    _loaded_modules.pop(skill_name, None)
    logger.info(f"[SkillRegistry] Registered new skill: {skill_name}")


# Initialise on import
_load_skill_index()
