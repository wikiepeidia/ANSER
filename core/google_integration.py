import time
import os.path
import json

# --- Google API Setup (Placeholder/Real) ---
# In a real environment, you would install:
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']

# Get the directory where this script is located
# core/google_integration.py -> core/ -> root/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'secrets', 'google_oauth.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'secrets', 'token.json')

def get_google_service(service_name, version, token_info=None):
    """
    Attempts to authenticate and return a Google API service.
    Returns None if credentials are missing or libraries are not installed.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("[Google] Google API libraries not installed. Using Mock mode.")
        return None

    creds = None
    
    if token_info:
        try:
            # Use provided token info (from DB)
            # Ensure token_info has all required fields or handle missing ones
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except ValueError as e:
            print(f"[Google] Error loading provided token info: {e}")
            creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if not creds and os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except ValueError as e:
            print(f"[Google] Error loading token.json: {e}")
            print("[Google] The token file seems corrupt or missing the refresh_token.")
            creds = None # Force re-auth logic below
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[Google] Token refresh failed: {e}")
                creds = None

        # If still not valid (refresh failed or didn't exist)
        if not creds or not creds.valid:
            # If we were trying to use a specific user token (token_info), do NOT fallback to interactive login
            if token_info:
                print("[Google] User token is invalid or expired and could not be refreshed.")
                return None

            # Only try interactive login if we are NOT using a passed token (which implies server context)
            # and if we are in a local environment where we can open a browser.
            # For now, we keep the old logic as fallback for local testing.
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"[Google] client_secret.json not found at: {CREDENTIALS_FILE}")
                print("[Google] client_secret.json not found. Using Mock mode.")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                # Try to use a random port. If this fails due to redirect_uri_mismatch (common with Web Client IDs),
                # we catch it and suggest the manual script.
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"[Google] Authentication failed: {e}")
                print("[Google] It seems you are using a Web Client ID which requires a specific Redirect URI.")
                print("[Google] Please run 'python test/authenticate.py' to generate token.json manually.")
                return None

    try:
        if not creds:
            print("[Google] DEBUG: No credentials object available. Cannot build service.")
            return None
        elif not creds.valid:
            print("[Google] DEBUG: Credentials object exists but is invalid. Cannot build service.")
            return None
        else:
            # print(f"[Google] DEBUG: Credentials valid. Scopes: {creds.scopes}")
            pass

        service = build(service_name, version, credentials=creds)
        return service
    except Exception as e:
        print(f"[Google] Error building service: {e}")
        return None

def read_sheet(sheet_id, range_name, token_info=None):
    """
    Reads data from a Google Sheet.
    Tries to use real API if available, otherwise falls back to mock.
    """
    service = get_google_service('sheets', 'v4', token_info)
    
    if service:
        try:
            print(f"[Google] REAL API: Reading Sheet {sheet_id} range {range_name}...")
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            error_str = str(e)
            
            # --- Smart Retry for Sheet Names (e.g. "Sheet1" vs "Trang tính1") ---
            if "Unable to parse range" in error_str or "400" in error_str:
                print(f"[Google] Range error detected. Attempting to auto-detect correct sheet name...")
                try:
                    # Fetch metadata to find real sheet names
                    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    sheets = metadata.get('sheets', [])
                    if sheets:
                        # Get the title of the very first sheet
                        first_sheet_title = sheets[0].get('properties', {}).get('title')
                        print(f"[Google] Found first sheet: '{first_sheet_title}'")
                        
                        # Extract the cell part of the original range (e.g. "A1:B10" from "Sheet1!A1:B10")
                        if '!' in range_name:
                            cell_range = range_name.split('!', 1)[1]
                        else:
                            cell_range = range_name
                            
                        new_range = f"'{first_sheet_title}'!{cell_range}"
                        print(f"[Google] Retrying with corrected range: {new_range}")
                        
                        result = sheet.values().get(spreadsheetId=sheet_id, range=new_range).execute()
                        values = result.get('values', [])
                        return values
                except Exception as inner_e:
                    print(f"[Google] Auto-detection failed: {inner_e}")

            print(f"[Google] REAL API Failed: {error_str}")
            
            if "Method doesn't allow unregistered callers" in error_str:
                print("\n[Google] CRITICAL ERROR: The API call was rejected because the OAuth token is missing or invalid.")
                print("[Google] FIX: Please delete 'test/token.json' and run 'python test/authenticate.py' again.\n")
            
            print("[Google] Falling back to mock.")
    
    # --- Mock Fallback ---
    print(f"[Google] MOCK: Reading Sheet {sheet_id} range {range_name}...")
    time.sleep(1) # Simulate network delay
    
    # Return dummy data structure (list of lists)
    return [
        ["Name", "Email", "Status"],
        ["Alice", "alice@example.com", "Active"],
        ["Bob", "bob@example.com", "Inactive"],
        ["Charlie", "charlie@example.com", "Active"]
    ]

def read_doc(doc_id, token_info=None):
    """
    Reads a Google Doc.
    """
    service = get_google_service('docs', 'v1', token_info)
    
    if service:
        try:
            print(f"[Google] REAL API: Reading Doc {doc_id}...")
            document = service.documents().get(documentId=doc_id).execute()
            # Extract text from the document structure (simplified)
            text = ""
            for content in document.get('body').get('content'):
                if 'paragraph' in content:
                    elements = content.get('paragraph').get('elements')
                    for elem in elements:
                        if 'textRun' in elem:
                            text += elem.get('textRun').get('content')
            return text
        except Exception as e:
            error_str = str(e)
            print(f"[Google] REAL API Failed: {error_str}")
            
            if "Method doesn't allow unregistered callers" in error_str:
                print("\n[Google] CRITICAL ERROR: The API call was rejected because the OAuth token is missing or invalid.")
                print("[Google] FIX: Please delete 'test/token.json' and run 'python test/authenticate.py' again.\n")
                
            print("[Google] Falling back to mock.")

    print(f"[Google] MOCK: Reading Doc {doc_id}...")
    time.sleep(0.5)
    return "This is the content of the Google Doc."

def write_sheet(sheet_id, range_name, values, method='append', token_info=None):
    """
    Writes data to a Google Sheet.
    method: 'append' (add rows) or 'update' (overwrite cells)
    """
    service = get_google_service('sheets', 'v4', token_info)
    
    if service:
        try:
            print(f"[Google] REAL API: {method.upper()} to Sheet {sheet_id} range {range_name}...")
            print(f"[Google] Data: {values}")
            body = {
                'values': values
            }
            
            if method == 'update':
                result = service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, 
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                # Update returns slightly different structure than append
                updates = result # For update, the result IS the update info
            else:
                # Default to append
                result = service.spreadsheets().values().append(
                    spreadsheetId=sheet_id, 
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                updates = result.get('updates', {})
            
            return updates
        except Exception as e:
            error_str = str(e)
            
            # --- Smart Retry for Sheet Names ---
            if "Unable to parse range" in error_str or "400" in error_str:
                print(f"[Google] Range error detected during WRITE. Attempting to auto-detect correct sheet name...")
                try:
                    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    sheets = metadata.get('sheets', [])
                    if sheets:
                        first_sheet_title = sheets[0].get('properties', {}).get('title')
                        print(f"[Google] Found first sheet: '{first_sheet_title}'")
                        
                        if '!' in range_name:
                            cell_range = range_name.split('!', 1)[1]
                        else:
                            cell_range = range_name
                            
                        new_range = f"'{first_sheet_title}'!{cell_range}"
                        print(f"[Google] Retrying WRITE with corrected range: {new_range}")
                        
                        if method == 'update':
                            result = service.spreadsheets().values().update(
                                spreadsheetId=sheet_id, 
                                range=new_range,
                                valueInputOption='USER_ENTERED',
                                body=body
                            ).execute()
                            updates = result
                        else:
                            result = service.spreadsheets().values().append(
                                spreadsheetId=sheet_id, 
                                range=new_range,
                                valueInputOption='USER_ENTERED',
                                body=body
                            ).execute()
                            updates = result.get('updates', {})
                            
                        return updates
                except Exception as inner_e:
                    print(f"[Google] Auto-detection failed: {inner_e}")

            print(f"[Google] REAL API Failed: {error_str}")
            print(f"[Google] Write Success: {updates.get('updatedCells')} cells updated.")
            return {"updatedCells": updates.get('updatedCells'), "updatedRange": updates.get('updatedRange')}
            
        except Exception as e:
            error_str = str(e)
            
            # --- Smart Retry for Sheet Names ---
            if "Unable to parse range" in error_str or "400" in error_str:
                print(f"[Google] Range error detected. Attempting to auto-detect correct sheet name...")
                try:
                    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    sheets = metadata.get('sheets', [])
                    if sheets:
                        first_sheet_title = sheets[0].get('properties', {}).get('title')
                        print(f"[Google] Found first sheet: '{first_sheet_title}'")
                        
                        if '!' in range_name:
                            cell_range = range_name.split('!', 1)[1]
                        else:
                            cell_range = range_name
                            
                        new_range = f"'{first_sheet_title}'!{cell_range}"
                        print(f"[Google] Retrying with corrected range: {new_range}")
                        
                        result = service.spreadsheets().values().append(
                            spreadsheetId=sheet_id, 
                            range=new_range,
                            valueInputOption='USER_ENTERED',
                            body=body
                        ).execute()
                        
                        updates = result.get('updates', {})
                        return {"updatedCells": updates.get('updatedCells'), "updatedRange": updates.get('updatedRange')}
                except Exception as inner_e:
                    print(f"[Google] Auto-detection failed: {inner_e}")

            print(f"[Google] REAL API Failed: {error_str}")
            return {"status": "error", "message": error_str}

    # --- Mock Fallback ---
    print(f"[Google] MOCK: Writing to Sheet {sheet_id}...")
    time.sleep(1)
    return {"status": "mock_success", "message": "Data written (simulated)"}

def send_email(to, subject, body_text, token_info=None):
    """
    Sends an email using the Gmail API.
    """
    service = get_google_service('gmail', 'v1', token_info)
    
    if service:
        try:
            from email.mime.text import MIMEText
            import base64
            
            print(f"[Google] REAL API: Sending email to {to}...")
            
            message = MIMEText(body_text)
            message['to'] = to
            message['subject'] = subject
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            body = {'raw': raw_message}
            
            result = service.users().messages().send(userId='me', body=body).execute()
            print(f"[Google] Email sent! ID: {result['id']}")
            return result
        except Exception as e:
            print(f"[Google] REAL API Failed: {e}")
            return {"status": "error", "message": str(e)}
            
    print(f"[Google] MOCK: Sending email to {to}...")
    time.sleep(1)
    return {"status": "mock_success", "message": "Email sent (simulated)"}
