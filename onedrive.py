import os
import atexit
import logging
import requests
import msal

# MS Graph API endpoints
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
SCOPES = ['Files.Read']  # We only need read access to migrate

# Security: Set a default timeout for all requests to prevent hanging indefinitely
DEFAULT_TIMEOUT = 60

logger = logging.getLogger(__name__)

class OneDriveClient:
    def __init__(self, config):
        self.client_id = config['microsoft']['client_id']
        self.client_secret = config['microsoft'].get('client_secret')
        self.authority = "https://login.microsoftonline.com/common"
        self.token_cache_file = "token_onedrive.bin"
        self.app = self._build_app()
        self.access_token = None

    def _build_app(self):
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_file):
            with open(self.token_cache_file, "r") as f:
                cache.deserialize(f.read())

        atexit.register(self._save_token_cache, cache)

        if self.client_secret:
             return msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
                token_cache=cache
            )
        else:
            return msal.PublicClientApplication(
                self.client_id,
                authority=self.authority,
                token_cache=cache
            )

    def _save_token_cache(self, cache):
        if cache.has_state_changed:
            # Securely create file with 600 permissions
            fd = os.open(self.token_cache_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(cache.serialize())

    def authenticate(self):
        accounts = self.app.get_accounts()
        result = None
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])

        if not result:
            logger.info("No suitable token exists in cache. Let's get a new one from User.")
            # For a CLI tool, device flow is often better, but PublicClientApplication can also do interactive
            # However, for simplicity and typical personal use, let's try interactive if supported,
            # or provide the URL for device flow if not.
            # Actually, most Personal setups are easier with Device Code Flow or Interactive.
            # Let's try Device Code Flow as it's very reliable for CLI.

            flow = self.app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                raise ValueError("Fail to create device flow. Err: %s" % flow)

            print(flow["message"])
            result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.access_token = result['access_token']
            logger.info("OneDrive authentication successful.")
        else:
            logger.error(result.get("error"))
            logger.error(result.get("error_description"))
            raise Exception("Could not authenticate with OneDrive")

    def get_headers(self):
        return {'Authorization': 'Bearer ' + self.access_token}

    def get_drive_items(self, item_id='root'):
        """
        Generator that yields items (files and folders) from a specific folder.
        Handles pagination.
        """
        # Optimization: Increase page size ($top) to reduce number of API calls.
        # We avoid $select to ensure we don't accidentally miss fields needed by consumers.
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{item_id}/children?$top=1000'

        while url:
            response = requests.get(url, headers=self.get_headers(), timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                logger.error(f"Error fetching items: {response.text}")
                raise Exception(f"Error fetching OneDrive items for {item_id}")

            data = response.json()
            for item in data.get('value', []):
                yield item

            url = data.get('@odata.nextLink')

    def get_file_stream(self, file_id):
        """
        Returns a response object capable of streaming the file content.
        The caller should use response.iter_content() or similar,
        or pass the raw stream to the upload function.
        """
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{file_id}/content'
        # stream=True is crucial here to not load the whole file into memory
        response = requests.get(url, headers=self.get_headers(), stream=True, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"Error downloading file {file_id}: {response.text}")
            raise Exception(f"Error downloading file {file_id}")
        return response.raw
