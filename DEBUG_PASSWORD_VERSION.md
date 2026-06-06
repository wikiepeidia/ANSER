# NeonDB Schema Fix — password_version Column

## 🔴 Problem Found

**Root Cause**: NeonDB is missing the `password_version` column in the `users` table.

**Symptom**: 
```
SELECT id, email, name, ... password_version FROM users WHERE email = ?
→ ERROR: column "password_version" does not exist
→ Exception caught silently in auth.py
→ Returns None
→ User sees "Wrong password" error
```

---

## ✅ Solutions Applied

### 1. **Diagnostic Script**
- **File**: `debug/check_neon_schema.py`
- **What it does**: Connects to NeonDB and validates the complete schema
- **Run**: `python debug/check_neon_schema.py`
- **Output**: Lists all tables and columns, highlights missing `password_version`

### 2. **Automatic Fix Script**
- **File**: `debug/fix_neon_password_version.py`
- **What it does**: Adds the missing column to NeonDB
- **Run**: `python debug/fix_neon_password_version.py`
- **Action**: 
  ```sql
  ALTER TABLE users ADD COLUMN password_version INTEGER DEFAULT 0
  ```

### 3. **Defensive Code Changes**
- **File**: `core/auth.py`
- **What it does**: Updated `verify_user()` and `register_user()` methods to handle missing columns gracefully
- **Benefit**: Auth continues to work even if the column doesn't exist (falls back to legacy sha256)

---

## 🚀 Quick Start to Fix NeonDB

### Step 1: Check the current schema
```bash
python debug/check_neon_schema.py
```

**Expected output**:
```
❌ MISSING: password_version column NOT FOUND in users table
   → This is the ROOT CAUSE of auth failures
```

### Step 2: Run the fix
```bash
python debug/fix_neon_password_version.py
```

**Expected output**:
```
✅ Column added successfully
✅ 42 existing users marked as legacy (password_version = 0)
   → On next login, passwords will be automatically rehashed with bcrypt

✅ FIX COMPLETE
```

### Step 3: Verify the fix
```bash
python debug/check_neon_schema.py
```

**Expected output**:
```
✅ password_version column EXISTS
```

### Step 4: Restart the application
```bash
python app.py
```

### Step 5: Test login
- Existing users: Will be auto-rehashed on first login (password_version 0 → 1)
- New users: Will be registered with bcrypt hashes directly (password_version 1)

---

## 🔍 How It Was Causing Auth Failures

### Before the Fix
1. User enters: `email=admin@test.com, password=secret123`
2. App tries: `SELECT ... password_version FROM users ...`
3. PostgreSQL error: `column "password_version" does not exist`
4. Exception caught at line 59 in `core/auth.py`
5. Returns `None` → User sees "Wrong password"

### After the Fix
1. User enters: `email=admin@test.com, password=secret123`
2. **Option A** (if column exists): Query succeeds, password verified normally
3. **Option B** (if column still missing): Query fails gracefully, falls back to legacy sha256 verification
4. Returns user object → Login succeeds ✅

---

## 📋 Schema Details

### Before (Missing Column)
```sql
users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  -- password_version MISSING! ❌
  name TEXT,
  role TEXT,
  ...
)
```

### After (Column Added)
```sql
users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  password_version INTEGER DEFAULT 0,  -- ✅ ADDED
  name TEXT,
  role TEXT,
  ...
)
```

---

## 🔄 Password Migration Flow

### Existing Users (password_version = 0)
```
Initial state:  password_version = 0 (SHA256 legacy hash)
First login:    verify with SHA256 → auto-rehash with bcrypt
After login:    password_version = 1 (bcrypt hash) ✅
```

### New Users (after fix)
```
Registration:   password_version = 1 (bcrypt hash) ✅
All logins:     verify with bcrypt
```

---

## 🛡️ Defensive Code Changes

### `verify_user()` Enhanced
```python
try:
    # Try to SELECT password_version
    c.execute('SELECT ... password_version FROM users ...')
except Exception as schema_err:
    # Column doesn't exist → fetch without it
    logger.warning("password_version column not found — falling back to legacy mode")
    c.execute('SELECT ... FROM users ...')  # without password_version
    password_version_available = False

# Use version 0 if column not available
password_version = 0 if not password_version_available else (user.get('password_version') or 0)
```

### `register_user()` Enhanced
```python
columns = self.db.get_table_columns('users')
has_password_version = 'password_version' in columns
has_manager_id = 'manager_id' in columns

# Build INSERT dynamically based on available columns
if has_password_version and has_manager_id:
    c.execute('INSERT INTO users (..., password_version, ...) ...')
elif has_password_version:
    c.execute('INSERT INTO users (..., password_version) ...')
# ... etc
```

---

## 📞 Troubleshooting

### Still seeing "Wrong password" after fix?

1. **Check the fix was applied**:
   ```bash
   python debug/check_neon_schema.py
   ```
   Should show: `✅ password_version column EXISTS`

2. **Clear app cache and restart**:
   ```bash
   python app.py
   ```

3. **Check logs for exceptions**:
   - Look at `logs/` or console output
   - Should NOT see `column "password_version" does not exist`

4. **Verify in PostgreSQL directly**:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'users' ORDER BY ordinal_position;
   ```
   Should include: `password_version`

### Script says column exists but auth still fails?

- Check if you're connecting to the correct NeonDB URL
- Verify `Config.POSTGRES_URL` environment variable
- Ensure the app is restarted after the schema change

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `debug/check_neon_schema.py` | Diagnose schema issues |
| `debug/fix_neon_password_version.py` | Apply the fix |
| `core/auth.py` | Authentication with defensive code |
| `migrations/versions/001_initial_schema.py` | Alembic migration (already has password_version) |
| `core/db/connection.py` | Database connection and schema init |

---

## ✨ Timeline

- **Issue Discovered**: NeonDB missing `password_version` column
- **Defensive Code**: Updated `auth.py` to handle missing columns gracefully
- **Automatic Fix**: Created `fix_neon_password_version.py` to add column to NeonDB
- **Diagnostic Tool**: Created `check_neon_schema.py` for future schema validation

---

## 🎯 Next Steps

1. Run `python debug/fix_neon_password_version.py`
2. Restart app: `python app.py`
3. Test login with any user account
4. Verify in logs: Should NOT see `column "password_version" does not exist`

**All users will be auto-migrated to bcrypt on their next login** ✅
