# 🏗️ Project A: Intelligent Retail Automation Architect

**Technical Design & Integration Master Plan**

## 1. Executive Summary

**Project A** is a Vietnamese Retail Automation Platform (RPAaaS) similar to Make.com/n8n.
The core differentiator is an **AI Architect** capable of understanding natural language requests (e.g., *"Tự động đăng bài Facebook khi có hàng mới"*) and generating executable workflow blueprints instantly.

---

## 2. System Architecture: "Brain in a Jar"

To bypass hardware limitations on the web server, we decouple the AI processing from the main application.

### 🧩 The Components

1. **The Body (Main App)**: Your existing Flask/Python application. Lightweight, handles UI, User Auth, and Workflow Execution.
2. **The Brain (AI Server)**: A Google Colab instance (L4 GPU) running the LLMs.
3. **The Nervous System**: `Ngrok` tunnel connecting The Brain to The Body via HTTP.

### Diagram

```mermaid
[User (Browser)] 
      │
      ▼
[Flask Web App (Local/Cloud)] 
      │
      ├── (1) Sends Request: "Build automation for X"
      │
      ▼
[Ngrok Tunnel] 
      │
      ▼
[Colab API Server (FastAPI)]
      │
      ├── [DeepSeek R1] (Manager/Planner)
      ├── [Qwen 2.5 Coder] (JSON Engineer)
      └── [Mistral 7B] (Tool/Search Expert)
      │
      ▼
(2) Returns: Simplified Logic JSON
      │
      ▼
[Flask Web App]
      │
      ├── (3) BlueprintConverter (Python)
      │      └─ Maps Simple JSON -> Complex App Schema
      │
      ▼
[Workflow Builder Canvas]
