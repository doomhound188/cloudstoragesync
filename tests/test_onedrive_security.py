import os
import unittest
from unittest.mock import MagicMock
import onedrive

class TestOneDriveSecurity(unittest.TestCase):
    def setUp(self):
        if os.path.exists('test_token.bin'):
            os.remove('test_token.bin')

    def tearDown(self):
        if os.path.exists('test_token.bin'):
            os.remove('test_token.bin')

    def test_save_token_cache_permissions(self):
        cache = MagicMock()
        cache.has_state_changed = True
        cache.serialize.return_value = "serialized_data"

        onedrive.save_token_cache('test_token.bin', cache)

        self.assertTrue(os.path.exists('test_token.bin'))

        st = os.stat('test_token.bin')
        mode = st.st_mode & 0o777
        self.assertEqual(mode, 0o600, f"Permissions too open: {oct(mode)}")

if __name__ == '__main__':
    unittest.main()
