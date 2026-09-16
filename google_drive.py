import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# If modifying these scopes, delete the file token_google.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

logger = logging.getLogger(__name__)

def get_credentials(config):
    """
    Retrieves or generates Google Drive credentials.
    """
    creds = None
    # The file token_google.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token_google.json'):
        try:
            with open('token_google.json', 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
        except Exception as e:
            logger.error(f"Error loading token_google.json: {e}")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            if 'google' not in config:
                raise ValueError("Google configuration missing in config.json")

            # We construct the client config on the fly to avoid needing a separate client_secret.json file
            client_config = {
                "installed": {
                    "client_id": config['google']['client_id'],
                    "client_secret": config['google']['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        # Securely create file with 600 permissions
        fd = os.open('token_google.json', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as token:
            token.write(creds.to_json())

    return creds

def authenticate(config):
    """Shows basic usage of the Drive v3 API.
    """
    creds = get_credentials(config)
    service = build('drive', 'v3', credentials=creds)
    return service

def create_folder(service, name, parent_id=None):
    """
    Creates a folder with the given name and parent.
    Does NOT check if it already exists. Use this when you are sure it doesn't exist.
    """
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    file = service.files().create(body=file_metadata, fields='id').execute()
    logger.info(f"Created new folder '{name}' (ID: {file.get('id')})")
    return file.get('id')


def create_folder_if_not_exists(service, name, parent_id=None):
    """
    Checks if a folder exists with the given name and parent.
    If yes, returns its ID.
    If no, creates it and returns the new ID.
    """
    # Escape backslashes first, then single quotes to prevent query injection
    safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
    query = f"mimeType='application/vnd.google-apps.folder' and name='{safe_name}' and trashed=false"
    if parent_id:
        safe_parent_id = parent_id.replace("\\", "\\\\").replace("'", "\\'")
        query += f" and '{safe_parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        # Return the first found folder
        logger.info(f"Found existing folder '{name}' (ID: {items[0]['id']})")
        return items[0]['id']
    else:
        return create_folder(service, name, parent_id)

def file_exists(service, name, parent_id=None):
    """
    Checks if a file exists. Returns the ID if it does, None otherwise.
    """
    # Escape backslashes first, then single quotes to prevent query injection
    safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
    query = f"name='{safe_name}' and trashed=false and mimeType!='application/vnd.google-apps.folder'"
    if parent_id:
        safe_parent_id = parent_id.replace("\\", "\\\\").replace("'", "\\'")
        query += f" and '{safe_parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    return None

class StreamWrapper:
    """
    Wraps a non-seekable stream to pretend it has a read method suitable for MediaIoBaseUpload.
    This is necessary because requests.raw is not fully compatible with what googleapiclient expects
    for some operations, though largely it works if we avoid seeking.
    """
    def __init__(self, stream, size):
        self._stream = stream
        self._size = size
        self._pos = 0

    def read(self, n=None):
        chunk = self._stream.read(n)
        self._pos += len(chunk)
        return chunk

    def tell(self):
        return self._pos

def upload_file(service, name, parent_id, data_stream, file_size, mimetype='application/octet-stream'):
    """
    Uploads a file from a stream to Google Drive.
    """
    file_metadata = {'name': name}
    if parent_id:
        file_metadata['parents'] = [parent_id]

    # Wrap the stream in a wrapper that implements `seek(0, 2)` to return the size
    # without seeking the network stream, preventing MediaIoBaseUpload from crashing.
    class SizeableStream:
        def __init__(self, stream, size):
            self._stream = stream
            self._size = size
            self._pos = 0

        def read(self, n=None):
            chunk = self._stream.read(n)
            if chunk:
                self._pos += len(chunk)
            return chunk

        def tell(self):
            return self._pos

        def seek(self, offset, whence=0):
            if whence == os.SEEK_END and offset == 0:
                self._pos = self._size
                return self._size
            if whence == os.SEEK_SET:
                self._pos = offset
                return self._pos

            return self._pos

        def seekable(self):
            return True

    wrapped_stream = SizeableStream(data_stream, file_size)
    media = MediaIoBaseUpload(wrapped_stream, mimetype=mimetype, resumable=True)

    logger.info(f"Uploading file '{name}'...")
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    logger.info(f"Uploaded file '{name}' (ID: {file.get('id')})")
    return file.get('id')


def list_folder_contents(service, parent_id):
    """
    Lists all files and folders in a specific Google Drive folder.
    Returns a dictionary mapping names to metadata (id, name, mimeType).
    """
    files_map = {}
    page_token = None

    # Escape backslashes and single quotes for safety
    safe_parent_id = parent_id.replace("\\", "\\\\").replace("'", "\\'")

    # We want all children, not trashed
    query = f"'{safe_parent_id}' in parents and trashed=false"

    while True:
        try:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token,
                pageSize=1000  # Maximize page size to reduce calls
            ).execute()
        except Exception as e:
            logger.error(f"Error listing folder contents: {e}")
            raise

        for file in results.get('files', []):
            files_map[file['name']] = file

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return files_map
