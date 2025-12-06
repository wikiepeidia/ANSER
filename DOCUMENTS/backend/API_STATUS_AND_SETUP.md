# App Connectivity Status & Setup Guide

## ❓ Can it connect yet?

**YES.** The application logic is fully implemented to connect to both Google and Make.com.

### 1. Google Integration Status

* **Current State:** 🟡 **Mock Mode** (Simulated)
* **Why?** The app is currently using a dummy `client_secret.json` file. When it can't find real credentials, it simulates data (returns "Alice", "Bob", etc.) so you can test the UI without breaking things.
* **How to make it REAL:**
    1. Follow the **Google Setup Steps** below to get your `client_secret.json`.
    2. Replace the dummy file in the `test/` folder with your real one.
    3. Install the required Python libraries.
    4. Restart the app.

### 2. Make.com Integration Status

* **Current State:** 🟢 **Ready**
* **Why?** Make.com integration is simpler. It just needs a URL.
* **How to use it:**
    1. Follow the **Make.com Setup Steps** below to create a webhook.
    2. Paste the URL into our App's node settings.

---

## 🛠️ Setup Instructions ("The Giggles")

### Step 1: Install Python Libraries

Open your terminal in the project folder and run:

```bash
pip install -r test/requirements.txt
```

---

### Step 2: Google Setup (Get the API Key)

We connect directly to Google so users can log in with their own accounts.

#### 1. Google Cloud Console

1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a **New Project** (e.g., "My Workspace App").

#### 2. Enable APIs

1. In the sidebar, go to **APIs & Services > Library**.
2. Search for and **Enable** the following:
    * **Google Sheets API**
    * **Google Drive API**
    * **Google Docs API**

#### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**.
2. Choose **External** (so any Google account can test it).
3. Fill in the App Name and Support Email.
4. Add **Scopes** (Permissions):
    * `.../auth/spreadsheets.readonly` (Read Sheets)
    * `.../auth/drive.readonly` (Read Drive)
5. Add **Test Users**: Add your own email address so you can log in during development.
6. **DO NOT PUBLISH:** Keep the status as **Testing**.
    * *Note:* When you log in, Google will show a scary warning ("Google hasn't verified this app").
    * *Fix:* Click **Advanced** -> **Go to [App Name] (unsafe)** to continue. This is normal for personal dev apps.

#### 4. Get Credentials

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Application Type: **Web application**.
4. **Authorized Redirect URIs**:
    * `http://localhost:5000/callback` (This is where Google sends the user back after login).
5. Click **Create**.
6. **Download the JSON file**.
7. **Rename** it to `client_secret.json`.
8. **Move** it to the `test/` folder (overwrite the existing one).

---

### Step 3: Make.com Setup (The "4th Party")

We use Make.com to handle complex APIs (Slack, Jira, etc.).

#### 1. Create the Scenario

1. Log in to **[Make.com](https://www.make.com/)**.
2. Click **Create a new scenario**.

#### 2. The Trigger (Receive Data)

1. Click the big `+` button.
2. Search for **Webhooks**.
3. Select **Custom webhook**.
4. Click **Add** to create a new webhook. Name it "Workspace Node".
5. **Copy the URL** (e.g., `https://hook.us1.make.com/abc123xyz...`).
    * *Save this URL! You will paste it into our App.*

#### 3. The Action (Do Work)

1. Add a module next to the Webhook (e.g., Slack, Gmail, Trello).
2. Connect your account and map the data.

#### 4. The Response (Return Success)

*Crucial Step: If you don't do this, our app will hang.*

1. Add a module at the end of the flow.
2. Search for **Webhooks**.
3. Select **Webhook Response**.
4. **Status:** `200`.
5. **Body:** `{"status": "success"}`.
6. **Save** and turn the scenario **ON**.

---

### Step 4: Run & Test

1. Run the app:

    ```bash
    python test/testapp.py
    ```

2. Go to `http://localhost:5000/test`.
3. **Test Google:** Drag a Google Node, enter a real Sheet ID, and run.
4. **Test Make:** Drag a Make Node, paste your Webhook URL, and run.
