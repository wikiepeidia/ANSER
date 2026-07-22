# WORKFLOW: ADVERSARIAL BRAIN FEATURE DEVELOPMENT
**Trigger:** `/develop_brain_feature [feature_description]`

## Step 1: Workspace Isolation & Ingestion
* **Action:** `@devops`, checkout a new git branch named `feat/[brief-description]`. 
* **Action:** `@engineer`, generate a `Technical_Proposal.md` Artifact including: Exact files to modify (e.g., `src/server.py`, `launch_demo.py`), the logic for the `ENV` model toggle, and the expected FastAPI JSON response schema.

## Step 2: Adversarial Audit (@qa)
* **Action:** `@qa`, your objective is to break `@engineer`'s proposal.
* **Validation Checklist:**
    * [ ] Is `pathlib` used for all file operations?
    * [ ] Does the local mode strictly utilize a <2B parameter model to fit inside the host's 6GB VRAM limit?
    * [ ] Will this cause an asynchronous block in `src/server.py`?
    * [ ] Are secrets dynamically loaded (no hardcoding)?
* **Output:** Generate an `Audit_Report.md`. If no flaws exist, state: `STATUS: VERIFIED AND SAFE FOR EXECUTION`.

## Step 3: Debate & Resolution Loop (CIRCUIT BREAKER: 3 ITERATIONS)
* **Action:** `@engineer` must rewrite the proposal to fix flaws found by `@qa`. 
* **Circuit Breaker:** This loop is strictly limited to 3 iterations. If consensus is not reached, `@devops` MUST instantly abort the workflow, generate a `Stalemate_Report.md`, and halt.

## Step 4: Local Deterministic Execution & API Testing
* **Action:** Upon consensus, `@engineer` writes the code.
* **Action:** `@devops` increments the modification counter (apply 5-Change Fallback rule if needed).
* **Action:** `@devops` sets `ENV=LOCAL`, runs `launch_demo.py` locally on a secondary port (e.g., 8001), and routes a dummy API request to prove the local quant model responds with valid syntax.

## Step 5: Human Approval & GitHub Deployment
* **Action:** HALT THE WORKFLOW. Present the local test results and code changes to the human developer. Wait for the explicit command: "Approved for Colab."
* **Action:** Upon human approval, `@devops` executes `git add .`, `git commit -m "feat: [brief-description]"`, and `git push origin [branch-name]`.