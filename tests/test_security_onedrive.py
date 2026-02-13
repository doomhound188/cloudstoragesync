import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import onedrive
sys.path.append(os.getcwd())
import onedrive

class TestOneDriveSecurity(unittest.TestCase):

    @patch('onedrive.atexit')
    @patch('onedrive.msal')
    @patch('onedrive.requests')
    def test_get_drive_items_timeout(self, mock_requests, mock_msal, mock_atexit):
        """Verify that get_drive_items uses a timeout."""
        # Setup Mocks
        mock_app = MagicMock()
        mock_msal.PublicClientApplication.return_value = mock_app
        mock_app.acquire_token_silent.return_value = {'access_token': 'fake_token'}

        # Mock requests.get response
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

        # Call get_drive_items
        list(client.get_drive_items('root'))

        # Verify requests.get was called with a timeout
        args, kwargs = mock_requests.get.call_args
        self.assertIn('timeout', kwargs, "requests.get call missing 'timeout' parameter")
        self.assertGreater(kwargs['timeout'], 0, "timeout should be greater than 0")

    @patch('onedrive.atexit')
    @patch('onedrive.msal')
    @patch('onedrive.requests')
    def test_get_file_stream_timeout(self, mock_requests, mock_msal, mock_atexit):
        """Verify that get_file_stream uses a timeout."""
        # Setup Mocks
        mock_app = MagicMock()
        mock_msal.PublicClientApplication.return_value = mock_app
        mock_app.acquire_token_silent.return_value = {'access_token': 'fake_token'}

        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        # Instantiate Client
        config = {'microsoft': {'client_id': 'fake_id'}}
        client = onedrive.OneDriveClient(config)
        client.authenticate()

        # Call get_file_stream
        client.get_file_stream('file_id')

        # Verify requests.get was called with a timeout
        args, kwargs = mock_requests.get.call_args
        self.assertIn('timeout', kwargs, "requests.get call missing 'timeout' parameter")
        self.assertGreater(kwargs['timeout'], 0, "timeout should be greater than 0")

if __name__ == '__main__':
    unittest.main()
