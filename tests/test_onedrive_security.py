import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import onedrive
sys.path.append(os.getcwd())
import onedrive

class TestOneDriveSecurity(unittest.TestCase):

    @patch('onedrive.requests')
    @patch('onedrive.msal')
    @patch('onedrive.atexit')
    def test_timeout_in_api_calls(self, mock_atexit, mock_msal, mock_requests):
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
        # For stream
        mock_response.raw = MagicMock()

        mock_requests.get.return_value = mock_response

        # Instantiate Client
        config = {'microsoft': {'client_id': 'fake_id'}}
        client = onedrive.OneDriveClient(config)
        client.authenticate()

        # 1. Test get_drive_items
        list(client.get_drive_items('root'))

        # Check calls
        args, kwargs = mock_requests.get.call_args
        self.assertIn('timeout', kwargs, "Timeout must be specified for get_drive_items")
        self.assertEqual(kwargs['timeout'], 60, "Timeout should be 60 seconds")

        # 2. Test get_file_stream
        client.get_file_stream('file_id')

        # Check calls (most recent)
        args, kwargs = mock_requests.get.call_args
        self.assertIn('timeout', kwargs, "Timeout must be specified for get_file_stream")
        self.assertEqual(kwargs['timeout'], 60, "Timeout should be 60 seconds")

if __name__ == '__main__':
    unittest.main()
