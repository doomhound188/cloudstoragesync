import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import migrate
sys.path.append(os.getcwd())
import migrate

class TestMigrateSync(unittest.TestCase):

    def setUp(self):
        # Reset thread local storage if present
        if hasattr(migrate, 'thread_local_data'):
             if hasattr(migrate.thread_local_data, 'service'):
                 del migrate.thread_local_data.service

    @patch('migrate.google_drive')
    def test_process_file_upload_new_file(self, mock_gd):
        # We need to mock get_thread_safe_service if we can't depend on real one
        mock_service = MagicMock()

        with patch('migrate.get_thread_safe_service', return_value=mock_service):
            mock_od_client = MagicMock()
            mock_od_client.get_file_stream.return_value = "stream_data"

            mock_creds = MagicMock()

            item = {'name': 'new.txt', 'id': 'od_1', 'file': {'mimeType': 'text/plain'}, 'size': 100}
            gd_folder_contents = {}

            # Execute
            migrate.process_file_upload(mock_od_client, mock_creds, item, 'gd_root', '', gd_folder_contents)

            # Verify
            mock_od_client.get_file_stream.assert_called_with('od_1')
            mock_gd.upload_file.assert_called_with(mock_service, 'new.txt', 'gd_root', 'stream_data', 100, 'text/plain')

    @patch('migrate.google_drive')
    def test_process_file_upload_existing_file(self, mock_gd):
        mock_service = MagicMock()

        with patch('migrate.get_thread_safe_service', return_value=mock_service):
            mock_od_client = MagicMock()
            mock_od_client.get_file_stream.return_value = "stream_data"
            mock_creds = MagicMock()

            item = {'name': 'exist.txt', 'id': 'od_2', 'file': {'mimeType': 'text/plain'}, 'size': 100}
            # Simulate file exists in cache
            gd_folder_contents = {'exist.txt': {'id': 'gd_2', 'mimeType': 'text/plain'}}

            # Execute
            with patch('migrate.get_timestamped_name', return_value='exist_timestamped.txt'):
                migrate.process_file_upload(mock_od_client, mock_creds, item, 'gd_root', '', gd_folder_contents)

            # Verify upload called with RENAMED file (preserving behavior)
            mock_gd.upload_file.assert_called_with(mock_service, 'exist_timestamped.txt', 'gd_root', 'stream_data', 100, 'text/plain')

    @patch('migrate.google_drive')
    def test_process_file_upload_conflict(self, mock_gd):
        mock_service = MagicMock()

        with patch('migrate.get_thread_safe_service', return_value=mock_service):
            mock_od_client = MagicMock()
            mock_od_client.get_file_stream.return_value = "stream_data"
            mock_creds = MagicMock()

            item = {'name': 'conflict.txt', 'id': 'od_3', 'file': {'mimeType': 'text/plain'}, 'size': 100}
            # Exists but NOT a folder (so file conflict)
            gd_folder_contents = {'conflict.txt': {'id': 'gd_3', 'mimeType': 'text/plain'}}

            # Execute
            with patch('migrate.get_timestamped_name', return_value='conflict_timestamped.txt'):
                migrate.process_file_upload(mock_od_client, mock_creds, item, 'gd_root', '', gd_folder_contents)

            # Verify upload called with new name
            mock_gd.upload_file.assert_called_with(mock_service, 'conflict_timestamped.txt', 'gd_root', 'stream_data', 100, 'text/plain')

    @patch('migrate.google_drive')
    def test_sync_folder_parallel_submission(self, mock_gd):
        mock_executor = MagicMock()
        mock_od_client = MagicMock()
        mock_gd_service = MagicMock()
        mock_creds = MagicMock()

        # Mock 2 files
        mock_od_client.get_drive_items.return_value = [
            {'name': 'f1.txt', 'id': '1', 'file': {}},
            {'name': 'f2.txt', 'id': '2', 'file': {}}
        ]
        mock_gd.list_folder_contents.return_value = {}

        futures = []

        migrate.sync_folder(mock_od_client, mock_gd_service, 'od_root', 'gd_root', futures=futures, executor=mock_executor, creds=mock_creds)

        # Verify 2 submissions
        self.assertEqual(mock_executor.submit.call_count, 2)
        self.assertEqual(len(futures), 2)

        # Verify arguments to submit
        # args[0] is function, args[1:] are arguments
        call_args = mock_executor.submit.call_args_list[0]
        func = call_args[0][0]
        self.assertEqual(func.__name__, 'process_file_upload')

if __name__ == '__main__':
    unittest.main()
