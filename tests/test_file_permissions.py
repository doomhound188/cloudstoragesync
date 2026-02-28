import unittest
import os
from unittest.mock import patch, MagicMock
import google_drive
import onedrive

class TestFilePermissions(unittest.TestCase):

    @patch('os.open')
    @patch('os.fdopen')
    @patch('google_drive.InstalledAppFlow')
    def test_google_drive_token_permissions(self, MockFlow, MockFdOpen, MockOsOpen):
        """Verify token_google.json is created with 0o600 permissions."""
        # Setup mocks
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "dummy"}'
        mock_flow.run_local_server.return_value = mock_creds
        MockFlow.from_client_config.return_value = mock_flow

        MockOsOpen.return_value = 123

        config = {'google': {'client_id': 'id', 'client_secret': 'secret'}}

        # Ensure file doesn't exist so we trigger the login flow
        with patch('os.path.exists', return_value=False):
            google_drive.get_credentials(config)

        # Verify os.open called with correct arguments
        MockOsOpen.assert_called_once()
        args, _ = MockOsOpen.call_args
        self.assertEqual(args[0], 'token_google.json')
        self.assertTrue(args[1] & os.O_CREAT)
        self.assertTrue(args[1] & os.O_WRONLY)
        self.assertEqual(args[2], 0o600)

    @patch('onedrive.atexit.register')
    @patch('onedrive.msal.ConfidentialClientApplication')
    @patch('onedrive.msal.PublicClientApplication')
    @patch('onedrive.msal.SerializableTokenCache')
    @patch('os.open')
    @patch('os.fdopen')
    def test_onedrive_token_permissions(self, MockFdOpen, MockOsOpen, MockCache, MockPublicApp, MockConfApp, MockAtexit):
        """Verify token_onedrive.bin is created with 0o600 permissions."""
        # Setup mocks
        config = {'microsoft': {'client_id': 'id', 'client_secret': 'secret'}}

        # We mock os.path.exists to avoid trying to read existing file in __init__
        with patch('os.path.exists', return_value=False):
            client = onedrive.OneDriveClient(config)

        mock_cache_instance = MagicMock()
        mock_cache_instance.has_state_changed = True
        mock_cache_instance.serialize.return_value = "data"

        MockOsOpen.return_value = 456

        # Call the method directly
        client._save_token_cache(mock_cache_instance)

        # Verify os.open called with correct arguments
        MockOsOpen.assert_called_once()
        args, _ = MockOsOpen.call_args
        self.assertEqual(args[0], 'token_onedrive.bin')
        self.assertTrue(args[1] & os.O_CREAT)
        self.assertTrue(args[1] & os.O_WRONLY)
        self.assertEqual(args[2], 0o600)

if __name__ == '__main__':
    unittest.main()
