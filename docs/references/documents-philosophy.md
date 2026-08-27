
Module docs (`docs/en/*.md`, top-of-file docstrings in source) contain **facts only**:
- What the module/file IS, what it does, where each piece lives
- Function signatures, contracts, side effects
- Tables of state vars, routes, sections, file paths
- Pure description. No recommendation, no priority, no "how to fix"

**What does NOT go in module docs:**
- Workflow / procedure / "how to use this" — that lives in agent skills or memory, not in code-adjacent docs
- "Open issues" / "TODO" / priority order — those go in issues/PRs, not in module docs
- "Why this shape" / meta-commentary — also skills, not module docs
- The user's corrections or agent's mistakes — those go in memory/skills, not in code

**Top-of-file docstrings in source code** are a special case: they may repeat module-doc content (file roles, cascade contracts, HTTP facts) so the file is self-contained for a reader who lands on it cold. They are still facts only — no workflow, no procedure.

If unsure, the test is: *would this fact still be true in 6 months regardless of what the user or I is working on right now?* If yes → module doc. If no (depends on current task, current conversation, current corrections) → skill or memory.
