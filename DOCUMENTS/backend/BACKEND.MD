# Backend Architecture Proposal: Workspace Automation Engine

## 1. Overview

The Workspace will function as a lightweight workflow orchestration engine (similar to a simplified Make.com or n8n). It will execute user-defined flows where data passes from one node to another.

## 2. Integration Strategies

### Strategy A: Native Integration (Free Google APIs)

For free and accessible APIs (specifically Google services), we will implement direct integrations in our Python backend.

* **Mechanism:** Python `requests` library + Google Client Libraries.
* **Authentication:** OAuth 2.0 or Service Accounts.
* **Example Flow:**
    1. **Trigger:** User clicks "Run" or a scheduled time.
    2. **Action:** Fetch rows from a Google Sheet.
    3. **Process:** Convert rows to JSON.
    4. **Output:** Pass JSON to the next node.

### Strategy B: "4th Party" Proxy (Make.com Integration)

For paid APIs, complex authentications (Slack, Jira, Salesforce), or services where we want to avoid maintaining heavy SDKs, we will use **Make.com** as an execution proxy.

* **Concept:** The Workspace acts as the "Trigger" for a Make.com scenario, and Make.com acts as the "Worker".
* **Mechanism:** Webhooks.
  * **Outbound:** Our backend sends a POST request to a specific Make.com Webhook URL with a JSON payload.
  * **Processing:** Make.com receives the data, performs the complex actions (e.g., "Post to Slack"), and optionally returns a response.
  * **Inbound:** Make.com sends the result back to our backend (synchronously or via callback).
* **Benefit:** We don't need to manage API keys for Slack/Salesforce/etc. The user manages those connections inside their own Make.com account.

## 3. Data Flow Architecture

The backend will treat the workflow as a **Directed Acyclic Graph (DAG)**.

1. **Input:** The Frontend (Builder) sends a JSON definition of the workflow:

    ```json
    {
      "nodes": [
        {"id": "1", "type": "google_sheet_read", "config": {...}},
        {"id": "2", "type": "make_com_webhook", "config": {"url": "..."}}
      ],
      "edges": [
        {"source": "1", "target": "2"}
      ]
    }
    ```

2. **Execution Engine (Python):**
    * Topological sort of nodes to determine execution order.
    * **Context Object:** A shared dictionary that holds the output of each node, keyed by Node ID.
    * **Step 1:** Execute Node 1 (Google). Store result in Context.
    * **Step 2:** Execute Node 2 (Make). Inject result from Node 1 into the payload. Store result in Context.
3. **Output:** Final status returned to the UI.

## 4. Proposed API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/workflow/execute` | Receives the full workflow JSON and runs it immediately. |
| `POST` | `/api/node/test` | Runs a single node in isolation (useful for the "Test" button in UI). |
| `GET` | `/api/integrations/google/auth` | Initiates OAuth flow for Google services. |

## 5. Implementation Roadmap

1. **Phase 1: The Engine.** Create the Python class that can parse the JSON and run dummy nodes.
2. **Phase 2: Make.com Node.** Implement the generic `WebhookNode` that sends data to Make.com.
3. **Phase 3: Google Node.** Implement `GoogleSheetNode` with basic read capabilities.
