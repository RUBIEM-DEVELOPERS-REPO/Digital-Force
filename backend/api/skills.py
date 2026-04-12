"""Digital Force — Skills API (SkillForge viewer)"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db, GeneratedSkill
from auth import get_current_user, require_role

router = APIRouter(prefix="/api/skills", tags=["skills"])

@router.get("")
async def list_skills(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(GeneratedSkill).order_by(desc(GeneratedSkill.created_at)))
    skills = result.scalars().all()
    return [{
        "id": s.id, "name": s.name, "display_name": s.display_name,
        "description": s.description, "test_passed": s.test_passed,
        "usage_count": s.usage_count, "is_active": s.is_active,
        "created_at": s.created_at.isoformat(),
    } for s in skills]

@router.get("/{skill_id}")
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    skill = await db.get(GeneratedSkill, skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return {"id": skill.id, "name": skill.name, "display_name": skill.display_name,
            "description": skill.description, "code": skill.code,
            "test_passed": skill.test_passed, "sandbox_test_result": skill.sandbox_test_result,
            "usage_count": skill.usage_count, "is_active": skill.is_active,
            "created_at": skill.created_at.isoformat()}

@router.patch("/{skill_id}/toggle")
async def toggle_skill(skill_id: str, db: AsyncSession = Depends(get_db),
                       user: dict = Depends(require_role("admin"))):
    skill = await db.get(GeneratedSkill, skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    skill.is_active = not skill.is_active
    return {"id": skill.id, "is_active": skill.is_active}

@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, db: AsyncSession = Depends(get_db),
                       user: dict = Depends(require_role("admin"))):
    skill = await db.get(GeneratedSkill, skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    await db.delete(skill)
    return {"deleted": True}
