# Agentic Supercharging Task List

- `[x]` **Phase 1: Ghost Browser Layer**
  - `[x]` Create `backend/agent/browser/ghost.py` (FastAPI Lifespan stateful Playwright session manager).
  - `[x]` Update `backend/main.py` to initialize and gracefully close `ghost.py` in the lifespan.
  - `[x]` Update `backend/agent/nodes/publisher.py` fallback logic to prioritize the `ghost.py` session over remote execution.
- `[x]` **Phase 2: Self-Healing DOM Selectors**
  - `[x]` Modify `backend/agent/skills/registry.py` to wrap `run_skill` with a Playwright `TimeoutError` interceptor.
  - `[x]` Implement fallback vision LLM call to generate a valid CSS selector dynamically via screenshot analysis.
  - `[x]` Add auto-patching routine to overwrite broken `.py` generated skills at runtime.
- `[x]` **Phase 3: Ghost-Enabled Vision Researcher**
  - `[x]` Update `backend/agent/nodes/researcher.py` to utilize `ghost.py` for semantic visual scraping.
  - `[x]` Integrate `groq-llama-3.2-90b-vision` prompt mapping to evaluate Instagram/Facebook competitor feeds natively.
- `[x]` **Phase 4: True Swarm Parallelization**
  - `[x]` Refactor `backend/agent/nodes/manager.py` to yield a LangGraph `Send` mapping array for parallel content tasks.
  - `[x]` Update `backend/agent/graph.py` to handle the `Send` reduction logic concurrently.
