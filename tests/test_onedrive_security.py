import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to sys.path to import onedrive
sys.path.append(os.getcwd())
import onedrive
import requests

class TestOneDriveSecurity(unittest.TestCase):

    @patch('onedrive.atexit')
    @patch('onedrive.msal')
    @patch('onedrive.requests')
    def test_requests_have_timeout(self, mock_requests, mock_msal, mock_atexit):
        # Setup Mocks
        mock_app = MagicMock()
        mock_msal.PublicClientApplication.return_value = mock_app
        mock_app.acquire_token_silent.return_value = {'access_token': 'fake_token'}

        # Mock requests.get response for listing files
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [],
            '@odata.nextLink': None
        }
        mock_requests.get.return_value = mock_response

        # Instantiate Client
        config = {'microsoft': {'client_id': 'fake_id'}}
        client = onedrive.OneDriveClient(config)
        client.authenticate()

        # Test get_drive_items
        list(client.get_drive_items('root'))

        # Verify get_drive_items call
        args, kwargs = mock_requests.get.call_args
        if 'timeout' not in kwargs:
             self.fail("requests.get missing 'timeout' argument in get_drive_items")

        # Test get_file_stream
        client.get_file_stream('file_id')

        # Verify get_file_stream call
        args, kwargs = mock_requests.get.call_args
        if 'timeout' not in kwargs:
             self.fail("requests.get missing 'timeout' argument in get_file_stream")

if __name__ == '__main__':
    unittest.main()
