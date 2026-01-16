import json
import os
import unittest
from unittest.mock import patch, MagicMock
import google_drive

class TestAuth(unittest.TestCase):
    def setUp(self):
        if os.path.exists('token_google.json'):
            os.remove('token_google.json')
        if os.path.exists('token_google.pickle'):
            os.remove('token_google.pickle')

    def tearDown(self):
        if os.path.exists('token_google.json'):
            os.remove('token_google.json')

    @patch('google_drive.build')
    @patch('google_drive.Credentials')
    def test_auth_reads_json(self, MockCredentials, MockBuild):
        # Create a dummy token file
        dummy_token = {"token": "dummy", "refresh_token": "refresh", "token_uri": "uri", "client_id": "id", "client_secret": "secret", "scopes": []}
        with open('token_google.json', 'w') as f:
            json.dump(dummy_token, f)

        # Mock Credentials.from_authorized_user_info
        mock_creds = MagicMock()
        mock_creds.valid = True
        MockCredentials.from_authorized_user_info.return_value = mock_creds

        config = {'google': {'client_id': 'id', 'client_secret': 'secret'}}

        # Run authenticate
        service = google_drive.authenticate(config)

        # Verify
        MockCredentials.from_authorized_user_info.assert_called_with(dummy_token, google_drive.SCOPES)
        MockBuild.assert_called_with('drive', 'v3', credentials=mock_creds)
        print("Test 1 Passed: Successfully read from token_google.json")

    @patch('google_drive.build')
    @patch('google_drive.InstalledAppFlow')
    def test_auth_writes_json(self, MockFlow, MockBuild):
        # Ensure no token file exists
        if os.path.exists('token_google.json'):
            os.remove('token_google.json')

        # Mock Flow
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "new_dummy"}'
        mock_flow.run_local_server.return_value = mock_creds
        MockFlow.from_client_config.return_value = mock_flow

        config = {'google': {'client_id': 'id', 'client_secret': 'secret'}}

        # Run authenticate
        service = google_drive.authenticate(config)

        # Verify
        self.assertTrue(os.path.exists('token_google.json'))
        with open('token_google.json', 'r') as f:
            content = f.read()
            self.assertEqual(content, '{"token": "new_dummy"}')

        print("Test 2 Passed: Successfully wrote to token_google.json")

if __name__ == '__main__':
    unittest.main()
