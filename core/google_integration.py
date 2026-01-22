import time
import os.path
import json
from datetime import datetime, timezone

# --- Google API Setup (Placeholder/Real) ---
# In a real environment, you would install:
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib google-analytics-data

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest
except ImportError:
    BetaAnalyticsDataClient = None
    RunReportRequest = None

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/analytics.readonly'
]

# Get the directory where this script is located
# core/google_integration.py -> core/ -> root/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'secrets', 'google_oauth.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'secrets', 'token.json')
ADMIN_TOKEN_FILE = os.path.join(BASE_DIR, 'secrets', 'token adminmail.json')

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

    def _load_client_credentials():
        """Load client_id/client_secret from secrets file or environment."""
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        try:
            with open(CREDENTIALS_FILE) as f:
                data = json.load(f)
                client_id = data.get('GOOGLE_CLIENT_ID') or data.get('client_id') or client_id
                client_secret = data.get('GOOGLE_CLIENT_SECRET') or data.get('client_secret') or client_secret
        except FileNotFoundError:
            pass
        return client_id, client_secret

    def _build_credentials_from_token(token_data):
        """Normalize Authlib token payload into google.oauth2.credentials.Credentials."""
        client_id, client_secret = _load_client_credentials()
        token_uri = token_data.get('token_uri') or 'https://oauth2.googleapis.com/token'
        scopes = token_data.get('scopes') or token_data.get('scope') or SCOPES
        if isinstance(scopes, str):
            scopes = scopes.split()

        # Convert expiry to naive UTC datetime to avoid offset-naive/aware comparisons.
        expiry_raw = token_data.get('expiry') or token_data.get('expires_at')
        expiry = None
        try:
            if isinstance(expiry_raw, (int, float)):
                # Use timezone-aware UTC then convert to naive if needed
                expiry = datetime.fromtimestamp(expiry_raw, timezone.utc).replace(tzinfo=None)
            elif isinstance(expiry_raw, str):
                # Handle 'Z' suffix for ISO format
                if expiry_raw.endswith('Z'):
                    expiry_raw = expiry_raw[:-1] + '+00:00'
                dt = datetime.fromisoformat(expiry_raw)
                # If aware, move to UTC then drop tzinfo to keep naive UTC
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                expiry = dt
            elif hasattr(expiry_raw, 'tzinfo'):
                dt = expiry_raw
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                expiry = dt
        except Exception as e:
            print(f"[Google] Error parsing token expiry: {e}")
            expiry = None

        return Credentials(
            token=token_data.get('token') or token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            expiry=expiry
        )

    creds = None
    
    if token_info:
        try:
            # Use provided token info (from DB)
            creds = _build_credentials_from_token(token_info)
        except Exception as e:
            print(f"[Google] Error loading provided token info: {e}")
            creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    # Check for ADMIN_TOKEN_FILE first if we are sending email (or generally prefer it if it exists)
    # For now, we check ADMIN_TOKEN_FILE first, then TOKEN_FILE
    
    token_path_to_use = TOKEN_FILE
    if os.path.exists(ADMIN_TOKEN_FILE):
        token_path_to_use = ADMIN_TOKEN_FILE
        
    if not creds and os.path.exists(token_path_to_use):
        try:
            creds = Credentials.from_authorized_user_file(token_path_to_use, SCOPES)
        except ValueError as e:
            print(f"[Google] Error loading {token_path_to_use}: {e}")
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


def list_files(token_info=None, mime_types=None, query_text=None, page_size=50, page_token=None):
    """List Drive files using provided token. Respects drive.file scope."""
    service = get_google_service('drive', 'v3', token_info)
    if not service:
        return {'files': [], 'nextPageToken': None, 'error': 'service_unavailable'}

    q_parts = ["trashed=false"]
    if mime_types:
        mime_filters = [f"mimeType='{m}'" for m in mime_types]
        q_parts.append("(" + " or ".join(mime_filters) + ")")
    if query_text:
        safe = query_text.replace("'", "\'")
        q_parts.append(f"name contains '{safe}'")
    q = " and ".join(q_parts)

    try:
        resp = service.files().list(
            q=q,
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType, modifiedTime, owners(displayName,emailAddress))',
            pageSize=page_size,
            pageToken=page_token
        ).execute()
        return {
            'files': resp.get('files', []),
            'nextPageToken': resp.get('nextPageToken')
        }
    except Exception as e:
        print(f"[Google] list_files error: {e}")
        return {'files': [], 'nextPageToken': None, 'error': str(e)}

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
                        
                        # Fix for implicit Sheet1 (common in English tutorials/defaults) vs "Trang tính1" (Vietnamese default)
                        # If the cell_range is literally "Sheet1" (or quoted 'Sheet1'), it means "Read All of Sheet1".
                        # We should replace it with "Read All of [ActualFirstSheet]" instead of "[ActualFirstSheet]!Sheet1"
                        clean_cell_range = cell_range.replace("'", "").replace('"', "")
                        if clean_cell_range.lower() == 'sheet1':
                            new_range = f"'{first_sheet_title}'"
                        else:
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

def write_doc(doc_id, content, token_info=None):
    """
    Appends text to a Google Doc.
    """
    service = get_google_service('docs', 'v1', token_info)

    if service:
        try:
            text = str(content) if content is not None else ""
            print(f"[Google] REAL API: Writing to Doc {doc_id}...")

            document = service.documents().get(documentId=doc_id).execute()
            body = document.get('body', {})
            contents = body.get('content', [])
            end_index = 1
            if contents:
                end_index = contents[-1].get('endIndex', 1)

            # Insert before the last end index to append text
            requests = [
                {
                    "insertText": {
                        "location": {"index": max(1, end_index - 1)},
                        "text": text
                    }
                }
            ]

            result = service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()

            return result
        except Exception as e:
            error_str = str(e)
            print(f"[Google] REAL API Failed: {error_str}")
            if "Method doesn't allow unregistered callers" in error_str:
                print("\n[Google] CRITICAL ERROR: The API call was rejected because the OAuth token is missing or invalid.")
                print("[Google] FIX: Please delete 'test/token.json' and run 'python test/authenticate.py' again.\n")
            print("[Google] Falling back to mock.")

    print(f"[Google] MOCK: Writing to Doc {doc_id}...")
    time.sleep(0.5)
    return {"status": "mock_success", "message": "Doc updated (simulated)"}

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
            print(f"[Google] Failed to send email: {e}")
            return None
            
    print(f"[Google] MOCK: Sending email to {to}...")
    return {"id": "mock_email_id"}

def get_analytics_report(property_id):
    """
    Fetches active users and page views from Google Analytics 4.
    """
    if not BetaAnalyticsDataClient:
        print("[Google Analytics] Library not installed.")
        return None
    
    service_account_path = os.path.join(BASE_DIR, 'secrets', 'analytics_service_account.json')
    if not os.path.exists(service_account_path):
        print(f"[Google Analytics] Service account file not found at {service_account_path}")
        return None

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
    
    try:
        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "date"}],
            metrics=[{"name": "activeUsers"}, {"name": "screenPageViews"}],
            date_ranges=[{"start_date": "30daysAgo", "end_date": "today"}],
        )
        response = client.run_report(request)
        
        # Format data
        labels = []
        active_users = []
        page_views = []
        
        for row in response.rows:
            labels.append(row.dimension_values[0].value)
            active_users.append(int(row.metric_values[0].value))
            page_views.append(int(row.metric_values[1].value))
            
        return {
            "labels": labels,
            "active_users": active_users,
            "page_views": page_views,
            "total_users": sum(active_users),
            "total_views": sum(page_views)
        }
    except Exception as e:
        print(f"[Google Analytics] Error fetching data: {e}")
        return None
