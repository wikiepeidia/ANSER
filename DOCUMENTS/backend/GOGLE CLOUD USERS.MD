1. Permissions Restored (Workflow Features Enabled)
I have added back the gmail.send and drive.file permissions to the login flow.

Consequence: The "Workflow" features (sending emails from the user's account) will work again.
Requirement: Because of this, you MUST add every user (including yourself) to the "Test Users" list in the Google Cloud Console, or they will get the 403 Error. There is no way around this while the app is in "Testing" mode if you want these features.
