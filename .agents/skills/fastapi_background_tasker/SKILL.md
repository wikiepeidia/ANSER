# Skill: FastAPI Background Tasker

## Goal
Convert long-running AI inference endpoints into asynchronous "fire-and-forget" routes to prevent HTTP timeouts.

## Execution Requirements
Whenever instructed to build an endpoint that triggers `Qwen2.5-Coder-32B` or `Qwen2-VL`:
1.  **Do NOT await the model inference in the main HTTP thread.**
2.  **Generate a UUID:** Instantly generate a unique `job_id` for the request.
3.  **Background Task:** Use FastAPI's `BackgroundTasks` (or `asyncio.create_task`) to hand off the model inference function to a background thread.
4.  **Immediate Return:** The endpoint MUST immediately return an HTTP 202 Accepted status with the `job_id` and a `status: "processing"` payload.
5.  **State Management:** Write the `job_id` state to a lightweight local dictionary or Redis instance so the Body can poll its status later.

## Verification
* Does the endpoint return a response in under 500ms, regardless of how long the LLM takes?
* Is `async def` properly utilized for the endpoint?