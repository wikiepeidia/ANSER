1. Infrastructure Diagram
 

2. Component Deep Dive & Code Analysis
Here is the explicit breakdown of every file in your src/ folder.
A. The Core (System Nervous System)
File	Function & Use Case	Essential Core Logic	Improvements Needed
config.py	Configuration Source of Truth. Controls paths, model IDs, and quantization settings.	Defines load_in_4bit/8bit and sets the DB_PATH.	Env Vars: Move API keys and Model paths to a .env file for security.
engine.py	The GPU Manager. Loads the heavy AI models once (Singleton pattern) and shares them across agents.	_load_all_models(): Prevents OOM (Out of Memory) by ensuring we don't load Qwen 3 times.	Async Loading: Loading blocks the main thread. In production, use vLLM server for faster inference.
memory.py	The Hippocampus. Manages SQLite interaction for Chat History, Sales Data, and User Profiles.	get_context_string(): Formats recent chat history so Qwen remembers what you said 5 seconds ago.	Postgres: SQLite locks file on writes. Move to PostgreSQL for multi-user concurrency.
context.py	The State Manager. Resolves ambiguity (e.g., "Which store are you talking about?").	resolve_login(): Forces user to select a store if they have multiple.	Redis: Store active sessions in Redis instead of RAM/DB for speed.
knowledge.py	The Long-Term Memory (RAG). Ingests PDFs/Docx into Vector DB.	search(): Uses Bi-Encoder (find) + Cross-Encoder (rank) for high-accuracy policy retrieval.	Chunking: current chunking is simple. Implement semantic chunking for complex legal docs.
B. The Agents (The Personas)
These files do not load models; they construct prompts and send them to the Engine.
File	Role & Behavior	Key Capability	Improvements Needed
manager.py	The Router & Consultant. The entry point for all logic.	analyze_task(): Uses Regex + LLM to decide if a query is Sales, Tech, or General.	Guardrails: Add stricter output parsing to prevent the router from failing on edge cases.
coder.py	The Specialist. Generates strict JSON blueprints.	write_code(): Injects "Golden Blueprints" from make_modules.json into context to ensure valid syntax.	Linting: Run a JSON linter inside the generation loop to auto-retry if syntax fails.
vision.py	The Eyes. Uses Florence-2 to describe images.	analyze_image(): Switches between "OCR Mode" (Reading) and "Caption Mode" (Marketing) dynamically.	Batching: Process multiple images at once for bulk inventory import.
researcher.py	The Librarian. Summarizes web search results.	process(): Takes raw HTML/snippets and summarizes them into Vietnamese business insights.	Citations: Force the model to cite sources (URLs) in the final answer.
C. The Execution Layer (The Hands)
File	Function	Core Logic	Improvements Needed
saas_api.py	The Bridge. Connects AI to your Store Data.	Currently uses Mock SQLite. Allows AI to run SQL queries like SELECT SUM(sales).	Real API: Replace SQLite calls with requests.get('https://api.kiotviet...').
integrations.py	The Deployer. Saves Blueprints and posts to Social Media.	deploy_internal(): Uses json_repair to fix AI mistakes before saving to the DB.	Webhooks: Actually trigger a webhook when a workflow is saved to notify the main app.
tools.py	Deterministic Utilities. Math and Logic.	health_check(): Proactively scans data for anomalies (e.g., "Zero Sales today").	Expansion: Add tools for "Currency Converter" or "Shipping Calculator".
________________________________________
3. Interaction Flow: How it Connects
Let's trace a complex request: "Check my inventory for 'Dress' and if low, create an automation to email the supplier."
1.	Entry (server.py): Receives HTTP POST. Initializes ManagerAgent.
2.	Perception (manager.py):
o	analyze_task("..."): Detects keywords "Check inventory" (DATA) and "Create automation" (TECHNICAL).
o	Decision: Complex intent. It prioritizes Data first.
3.	Tool Execution (saas_api.py):
o	Manager calls decide_tool.
o	Router selects check_inventory.
o	SaasAPI queries DB: SELECT stock FROM products WHERE name LIKE '%Dress%'.
o	Result: "Stock: 5 (Low)".
4.	Reasoning (manager.py):
o	Manager sees "Stock is Low" and the user's second intent ("create automation").
o	Manager constructs a plan: "1. Trigger: Inventory Update. 2. Condition: Stock < 10. 3. Action: Email Supplier."
5.	Generation (coder.py):
o	Manager passes the plan to Coder.
o	Coder loads make_modules.json (Registry) to see how "Email" nodes look.
o	Coder generates valid JSON.
6.	Deployment (integrations.py):
o	Server passes JSON to IntegrationManager.
o	json_repair fixes any missing commas.
o	JSON is saved to workflows table and my_workflows/ folder.
7.	Response: User receives text: "Stock is low (5). I have created an automation to email your supplier. [Download Link]"
________________________________________

