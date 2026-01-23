import os
import unittest
from unittest.mock import patch, MagicMock
import google_drive

class TestPermissions(unittest.TestCase):
    def setUp(self):
        if os.path.exists('token_google.json'):
            os.remove('token_google.json')

    def tearDown(self):
        if os.path.exists('token_google.json'):
            os.remove('token_google.json')

    @patch('google_drive.build')
    @patch('google_drive.InstalledAppFlow')
    def test_token_permissions_secure(self, MockFlow, MockBuild):
        # Mock Flow
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "secure"}'
        mock_flow.run_local_server.return_value = mock_creds
        MockFlow.from_client_config.return_value = mock_flow

        config = {'google': {'client_id': 'id', 'client_secret': 'secret'}}

        # Run authenticate
        google_drive.authenticate(config)

        # Verify file exists
        self.assertTrue(os.path.exists('token_google.json'))

        # Verify Permissions
        st = os.stat('token_google.json')
        mode = st.st_mode & 0o777
        print(f"File mode: {oct(mode)}")

        # We expect 0o600. If it's 0o644 or 0o664, this should fail.
        self.assertEqual(mode, 0o600, f"Permissions too open: {oct(mode)}")

if __name__ == '__main__':
    unittest.main()
