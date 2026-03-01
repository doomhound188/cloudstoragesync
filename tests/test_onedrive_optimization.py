import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import onedrive
sys.path.append(os.getcwd())
import onedrive

class TestOneDriveOptimization(unittest.TestCase):

    @patch('onedrive.atexit')
    @patch('onedrive.msal')
    @patch('onedrive.requests')
    def test_get_drive_items_optimization(self, mock_requests, mock_msal, mock_atexit):
        # Setup Mocks
        mock_app = MagicMock()
        mock_msal.PublicClientApplication.return_value = mock_app
        mock_app.acquire_token_silent.return_value = {'access_token': 'fake_token'}

        # Mock requests.Session and its get method
        mock_session = MagicMock()
        mock_requests.Session.return_value = mock_session

        # Mock session.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [],
            '@odata.nextLink': None
        }
        mock_session.get.return_value = mock_response

        # Instantiate Client
        config = {'microsoft': {'client_id': 'fake_id'}}
        client = onedrive.OneDriveClient(config)
        client.authenticate()

        # Call get_drive_items
        # Consume the generator
        items = list(client.get_drive_items('root'))

        # Verify session.get was called with optimized URL
        # We need to ensure we are checking the session object used by the client
        # Since we mocked requests.Session, client.session should be our mock_session
        self.assertEqual(client.session, mock_session)

        args, kwargs = mock_session.get.call_args
        url = args[0]

        self.assertIn('$top=1000', url)
        # We removed $select to ensure safety against missing fields in future usages
        self.assertNotIn('$select=', url)
        print(f"Verified URL: {url}")

if __name__ == '__main__':
    unittest.main()
