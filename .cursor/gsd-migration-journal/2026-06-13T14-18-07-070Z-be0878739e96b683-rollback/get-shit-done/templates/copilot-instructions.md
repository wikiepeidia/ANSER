# Instructions for GSD

- This repository is GSD-managed. Use `.planning/` as the live source of truth.
- At the start of a fresh session or before the first GSD action, read `.planning/STATE.md`. Read `.planning/PROJECT.md` and `.planning/ROADMAP.md` when you need milestone, scope, or current-phase context.
- Treat `/gsd:...`, `/gsd-...`, and `gsd-*` as GSD invocations.
- When the user is new to GSD or asks for help choosing a workflow, inspect the available local GSD assets in the current tool folder and choose the smallest correct workflow, skill, or agent.
- Use local `agents/`, `skills/`, `commands/`, and `get-shit-done/` directories when they exist. Fall back to `.github/` only when the current tool folder does not provide the needed asset.
- Assume some users are new to Git. Explain risky actions in plain language before doing them.
- Check the current branch before branch-affecting work.
- Only push, merge, rebase, reset, checkout, or sync branches when the user explicitly asks.
- Treat `main` and `demo` as protected or stable branches unless the user explicitly says otherwise.
- Do not apply a full GSD workflow unless the user explicitly asks for GSD or the task is about planning, state, roadmap, or workflow artifacts.
- After completing a GSD request or a GSD-produced deliverable, offer the next sensible step so the user knows what to do next.
