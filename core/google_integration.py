import time
import os.path
import json
from datetime import datetime, timezone

from core.logger import get_logger

logger = get_logger(__name__)

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


def _escape_drive_query_value(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")

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
        logger.warning("Google API libraries not installed. Using Mock mode.")
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
        except (ValueError, OSError) as e:
            logger.warning("Error parsing token expiry: %s", e)
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
            logger.error("Error loading provided token info: %s", e, exc_info=True)
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
            logger.warning("Error loading %s: %s — token file may be corrupt or missing refresh_token.", token_path_to_use, e)
            creds = None # Force re-auth logic below

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning("Token refresh failed: %s", e)
                creds = None

        # If still not valid (refresh failed or didn't exist)
        if not creds or not creds.valid:
            # If we were trying to use a specific user token (token_info), do NOT fallback to interactive login
            if token_info:
                logger.warning("User token is invalid or expired and could not be refreshed.")
                return None

            # Only try interactive login if we are NOT using a passed token (which implies server context)
            # and if we are in a local environment where we can open a browser.
            # For now, we keep the old logic as fallback for local testing.
            if not os.path.exists(CREDENTIALS_FILE):
                logger.warning("client_secret.json not found at: %s. Using Mock mode.", CREDENTIALS_FILE)
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
                logger.error(
                    "Authentication failed: %s — "
                    "if using a Web Client ID, run 'python test/authenticate.py' to generate token.json manually.",
                    e, exc_info=True,
                )
                return None

    try:
        if not creds:
            logger.warning("No credentials object available. Cannot build service.")
            return None
        elif not creds.valid:
            logger.warning("Credentials object exists but is invalid. Cannot build service.")
            return None

        service = build(service_name, version, credentials=creds)
        return service
    except Exception as e:
        logger.error("Error building Google service '%s' v%s: %s", service_name, version, e, exc_info=True)
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
        safe = _escape_drive_query_value(query_text)
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
        logger.error("list_files error: %s", e, exc_info=True)
        return {'files': [], 'nextPageToken': None, 'error': str(e)}

def read_sheet(sheet_id, range_name, token_info=None):
    """
    Reads data from a Google Sheet.
    Tries to use real API if available, otherwise falls back to mock.
    """
    service = get_google_service('sheets', 'v4', token_info)

    if service:
        try:
            logger.info("REAL API: Reading Sheet %s range %s", sheet_id, range_name)
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            error_str = str(e)

            # --- Smart Retry for Sheet Names (e.g. "Sheet1" vs "Trang tính1") ---
            if "Unable to parse range" in error_str or "400" in error_str:
                logger.info("Range error detected. Attempting to auto-detect correct sheet name...")
                try:
                    # Fetch metadata to find real sheet names
                    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    sheets = metadata.get('sheets', [])
                    if sheets:
                        # Get the title of the very first sheet
                        first_sheet_title = sheets[0].get('properties', {}).get('title')
                        logger.info("Found first sheet: '%s'", first_sheet_title)

                        # Extract the cell part of the original range (e.g. "A1:B10" from "Sheet1!A1:B10")
                        if '!' in range_name:
                            cell_range = range_name.split('!', 1)[1]
                        else:
                            cell_range = range_name

                        new_range = f"'{first_sheet_title}'!{cell_range}"
                        logger.info("Retrying with corrected range: %s", new_range)

                        result = sheet.values().get(spreadsheetId=sheet_id, range=new_range).execute()
                        values = result.get('values', [])
                        return values
                except Exception as inner_e:
                    logger.error("Sheet name auto-detection failed: %s", inner_e, exc_info=True)

            logger.error("REAL API read_sheet failed: %s", error_str)

            if "Method doesn't allow unregistered callers" in error_str:
                logger.critical(
                    "CRITICAL: The API call was rejected because the OAuth token is missing or invalid. "
                    "Delete 'test/token.json' and run 'python test/authenticate.py' again."
                )

            logger.info("Falling back to mock.")

    # --- Mock Fallback ---
    logger.info("MOCK: Reading Sheet %s range %s", sheet_id, range_name)
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
            logger.info("REAL API: Reading Doc %s", doc_id)
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
            logger.error("REAL API read_doc failed: %s", error_str)

            if "Method doesn't allow unregistered callers" in error_str:
                logger.critical(
                    "CRITICAL: The API call was rejected because the OAuth token is missing or invalid. "
                    "Delete 'test/token.json' and run 'python test/authenticate.py' again."
                )

            logger.info("Falling back to mock.")

    logger.info("MOCK: Reading Doc %s", doc_id)
    time.sleep(0.5)
    return "This is the content of the Google Doc."

def write_doc(doc_id, content, token_info=None):
    """
    Writes (appends) text content to a Google Doc.
    """
    service = get_google_service('docs', 'v1', token_info)

    if service:
        try:
            logger.info("REAL API: Writing to Doc %s", doc_id)
            # Insert text at the end of the document
            requests_body = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': str(content) + '\n'
                    }
                }
            ]
            result = service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests_body}
            ).execute()
            return {"status": "success", "message": f"Written to Doc {doc_id}", "replies": result.get('replies', [])}
        except Exception as e:
            error_str = str(e)
            logger.error("REAL API write_doc failed: %s", error_str)
            logger.info("Falling back to mock.")

    logger.info("MOCK: Writing to Doc %s", doc_id)
    time.sleep(0.5)
    return {"status": "success", "message": f"MOCK: Written to Doc {doc_id}", "content_length": len(str(content))}

def write_sheet(sheet_id, range_name, values, method='append', token_info=None):
    """
    Writes data to a Google Sheet.
    method: 'append' (add rows) or 'update' (overwrite cells)
    """
    service = get_google_service('sheets', 'v4', token_info)

    if service:
        try:
            logger.info("REAL API: %s to Sheet %s range %s", method.upper(), sheet_id, range_name)
            logger.info("Write payload: %s", values)
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
                logger.info("Range error detected during WRITE. Attempting to auto-detect correct sheet name...")
                try:
                    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    sheets = metadata.get('sheets', [])
                    if sheets:
                        first_sheet_title = sheets[0].get('properties', {}).get('title')
                        logger.info("Found first sheet: '%s'", first_sheet_title)

                        if '!' in range_name:
                            cell_range = range_name.split('!', 1)[1]
                        else:
                            cell_range = range_name

                        new_range = f"'{first_sheet_title}'!{cell_range}"
                        logger.info("Retrying WRITE with corrected range: %s", new_range)

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
                    logger.error("Sheet name auto-detection failed during WRITE: %s", inner_e, exc_info=True)

            logger.error("REAL API write_sheet failed: %s", error_str)
            return {"status": "error", "message": error_str}

    # --- Mock Fallback ---
    logger.info("MOCK: Writing to Sheet %s", sheet_id)
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

            logger.info("REAL API: Sending email to %s", to)

            message = MIMEText(body_text)
            message['to'] = to
            message['subject'] = subject

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            body = {'raw': raw_message}

            result = service.users().messages().send(userId='me', body=body).execute()
            logger.info("Email sent to %s, message ID: %s", to, result['id'])
            return result
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to, e, exc_info=True)
            return None

    logger.info("MOCK: Sending email to %s", to)
    return {"id": "mock_email_id"}

def get_analytics_report(property_id):
    """
    Fetches active users and page views from Google Analytics 4.
    """
    if not BetaAnalyticsDataClient:
        logger.warning("Google Analytics library not installed.")
        return None

    service_account_path = os.path.join(BASE_DIR, 'secrets', 'analytics_service_account.json')
    if not os.path.exists(service_account_path):
        logger.warning("Analytics service account file not found at %s", service_account_path)
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
        logger.error("Error fetching Google Analytics data for property %s: %s", property_id, e, exc_info=True)
        return None
