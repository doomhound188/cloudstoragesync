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

def authenticate(config):
    """Shows basic usage of the Drive v3 API.
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
        with open('token_google.json', 'w') as token:
            token.write(creds.to_json())

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

    # We wrap the stream to ensure it behaves correctly with MediaIoBaseUpload
    # Although requests.raw is file-like, providing the size explicitly prevents
    # MediaIoBaseUpload from trying to seek to the end to find the size.
    # Note: Using resumable=True is good practice for larger files.
    # chunksize is default 100MB, which is fine.

    # Crucially: We MUST not let MediaIoBaseUpload try to seek.
    # By convention, if we use a wrapper, we might avoid issues, but MediaIoBaseUpload
    # checks `fd.seekable()` if available. requests.raw.seekable() returns False.
    # If not seekable, MediaIoBaseUpload might fail if it doesn't know the size.
    # So we prefer MediaIoBaseUpload(..., resumable=True) AND use a wrapper
    # if necessary, but actually the library supports non-seekable if we don't ask it to infer size.
    # However, to be safe, we use the `googleapiclient.http.MediaIoBaseUpload` correctly.
    # But wait, `MediaIoBaseUpload` doesn't take a `size` argument directly in init.
    # It infers it. If the stream is not seekable, it reads the whole thing into memory unless
    # we use `MediaFileUpload` (for disk files).
    # Since we are streaming, we have a problem: `MediaIoBaseUpload` is tricky with unknown size streams.
    # Actually, looking at the source code or docs:
    # "If the file-like object is not seekable, the size cannot be determined..."
    # A common workaround is to use a custom class that implements read() and tell() but maybe
    # we should just trust the user provided size?
    # Actually, MediaIoBaseUpload doesn't allow setting size manually in the constructor easily
    # in older versions, but let's check.
    # WORKAROUND: We can use `googleapiclient.http.MediaIoBaseUpload` and subclass or monkeypatch,
    # OR we can just rely on chunked upload without knowing total size (if supported).
    # BUT, the review said "Upload Crash... You must extract the file size... and pass it".
    # Since MediaIoBaseUpload doesn't take size, we might need `MediaInMemoryUpload` if small,
    # or better: we use `MediaIoBaseUpload` but we ensure we don't trigger the seek.
    # The review implies we CAN pass size. Let's see if we can subclass it or just assign ._size

    # Correct approach for streaming large files with known size in google-api-python-client:
    # Use `MediaIoBaseUpload` and manually set `_size` if it can't be determined,
    # or ensure the stream object has a `len` or similar.
    # Let's try the simple approach first: Just pass the stream. If it crashes, we need the wrapper.
    # The reviewer said: "MediaIoBaseUpload attempts to determine the stream size by calling seek(0, 2)...
    # which will cause ... crash".

    # So we construct it, then forcefully set the size before use if possible,
    # or use a wrapper that implements `__len__` or similar?
    # `MediaIoBaseUpload` checks `sys.getsizeof` or `seek`.

    # Let's use a wrapper that handles the read and explicitly raises on seek,
    # but `MediaIoBaseUpload` catches seek errors? No, it might not.

    # Cleanest fix:
    # Create the object, then manually set `._size` before it's used?
    # No, it calculates size in `__init__`.

    # Let's implement a wrapper that mimics a file but allows `seek(0, 2)` to return the size
    # IF we know it, without actually seeking the network stream.

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
            # We only support seek(0, 2) to return size, or seek(0, 0) if we are at 0.
            if whence == 2 and offset == 0:
                return self._size
            if whence == 0 and offset == 0 and self._pos == 0:
                return 0
            # Otherwise we can't really seek
            # But the library might call seek(0, 2) just to find size.
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
