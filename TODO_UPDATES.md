
## ✅ Completed Tasks (Current Session)
- [x] **Scenarios Page Fixes**: Removed "garbage" tabs and fixed "Create Scenario" button redirect.
- [x] **Google Auth for Employees**: Implemented "Connect Mode" to link Google accounts to existing employee users.
- [x] **Database Migration**: Created SQLAlchemy models (`app/models.py`) and migration script (`scripts/migrate_sqlite_to_postgres.py`).
- [x] **AI Chat Widget**: Created frontend interface (HTML/CSS/JS) and integrated into `base.html`.
- [x] **AI Backend Integration**:
    - Created `secrets/ai_config.json` with HF Token and URL.
    - Added `/api/ai/chat` route in `app.py` to proxy requests to Hugging Face.
    - Updated `static/js/chat.js` to call the real API.

## 🚀 Next Steps
1.  **Run Database Migration**:
    - Test the migration script on a local Postgres instance.
    - Update `app.py` to use the new SQLAlchemy `db` session instead of raw SQLite queries.
2.  **Refine AI Responses**:
    - Handle "automation" actions in the frontend (e.g., show a button to view the created workflow).
    - Render Markdown or HTML in the chat bubbles (currently plain text).
