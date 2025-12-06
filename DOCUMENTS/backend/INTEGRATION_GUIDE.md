# Integration Setup Guide

This guide explains where to get the API credentials for our two main integration strategies.

---

## 1. Google APIs (Native Integration)

We will connect directly to Google so users can log in with their own accounts.

### Step 1: Google Cloud Console

1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a **New Project** (e.g., "My Workspace App").

### Step 2: Enable APIs

1. In the sidebar, go to **APIs & Services > Library**.
2. Search for and **Enable** the following:
    * **Google Sheets API**
    * **Google Drive API**
    * **Google Docs API**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**.
2. Choose **External** (so any Google account can test it) or **Internal** (if you have a Workspace org).
3. Fill in the App Name and Support Email.
4. Add **Scopes** (Permissions):
    * `.../auth/spreadsheets.readonly` (Read Sheets)
    * `.../auth/drive.readonly` (Read Drive)
5. Add **Test Users**: Add your own email address so you can log in during development.

### Step 4: Get Credentials

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Application Type: **Web application**.
4. **Authorized Redirect URIs**:
    * `http://localhost:5000/callback` (This is where Google sends the user back after login).
5. Click **Create**.
6. **Download the JSON file**. Rename it to `client_secret.json` and put it in your project folder.

---

## 2. Make.com (The "4th Party" Proxy)

We use Make.com to handle complex APIs (Slack, Jira, etc.) so we don't have to write code for them.

### The Concept

* **Our App:** Sends data to a Make Webhook URL.
* **Make:** Receives data -> Does the work (e.g., Post to Slack) -> Sends a response back.

### Step 1: Create the Scenario

1. Log in to **[Make.com](https://www.make.com/)**.
2. Click **Create a new scenario**.

### Step 2: The Trigger (Receive Data)

1. Click the big `+` button.
2. Search for **Webhooks**.
3. Select **Custom webhook**.
4. Click **Add** to create a new webhook. Name it "Workspace Slack Node".
5. **Copy the URL** (e.g., `https://hook.us1.make.com/abc123xyz...`).
    * *This URL is what you paste into our App's Node Settings.*

### Step 3: The Action (Do Work)

1. Add a module next to the Webhook.
2. Search for **Slack**.
3. Select **Create a Message**.
4. Connect your Slack account.
5. In the **Text** field, map the data coming from the Webhook (e.g., `{{1.source_data.message}}`).

### Step 4: The Response (Return Success)

*Crucial Step: If you don't do this, our app will hang waiting for a response.*

1. Add a module at the end of the flow.
2. Search for **Webhooks**.
3. Select **Webhook Response**.
4. **Status:** `200`.
5. **Body:**

    ```json
    {
      "status": "success",
      "platform": "slack",
      "message_id": "12345"
    }
    ```

6. **Save** and turn the scenario **ON**.

---

## Summary

* **Google:** You need `client_secret.json` from Google Cloud Console.
* **Make:** You need the **Webhook URL** generated inside a Make Scenario.
