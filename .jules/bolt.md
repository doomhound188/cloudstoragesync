# Bolt's Journal

## 2024-10-27 - Initial Setup
**Learning:** This is a Python-based migration tool (OneDrive -> Google Drive) with no existing tests.
**Action:** I will implement optimizations carefully and create a test script to verify logic since I cannot run integration tests against real APIs.

## 2024-10-27 - Optimize Google Drive Folder Creation
**Learning:** `google_drive.create_folder_if_not_exists` makes a redundant `files().list()` call even when the caller (migration script) already knows the folder doesn't exist via its local cache.
**Action:** Implemented `create_folder` to skip the check and updated `migrate.py` to use it when the cache misses. This saves 1 API call per new folder.
