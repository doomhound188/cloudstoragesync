import unittest
import os
import stat
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Import the class to test
from onedrive import OneDriveClient

class TestOneDriveSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            'microsoft': {
                'client_id': 'test_id',
                'client_secret': 'test_secret'
            }
        }
        # Patch msal to avoid actual network calls or errors during init
        self.msal_patcher = patch('onedrive.msal')
        self.mock_msal = self.msal_patcher.start()

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        self.msal_patcher.stop()

    def test_save_cache_permissions(self):
        """Test that _save_cache creates files with 0o600 permissions."""
        # Override token_cache_file to be in our temp dir
        token_file = os.path.join(self.test_dir, "token_onedrive.bin")

        # Instantiate client
        # We assume _build_app might fail or do things we don't want, so we mock it or let the patched msal handle it
        # Since we patched msal, _build_app should be fine.
        client = OneDriveClient(self.config)
        client.token_cache_file = token_file

        # Create a mock cache object
        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = "secret_data"

        # Call the method
        client._save_cache(mock_cache)

        # Verify file exists
        self.assertTrue(os.path.exists(token_file))

        # Verify permissions
        st = os.stat(token_file)
        permissions = st.st_mode & 0o777
        self.assertEqual(permissions, 0o600, f"Expected 0o600 but got {oct(permissions)}")

        # Verify content
        with open(token_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "secret_data")

if __name__ == "__main__":
    unittest.main()
