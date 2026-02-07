# Bolt's Journal

## 2024-10-27 - Initial Setup
**Learning:** This is a Python-based migration tool (OneDrive -> Google Drive) with no existing tests.
**Action:** I will implement optimizations carefully and create a test script to verify logic since I cannot run integration tests against real APIs.

## 2024-10-27 - Optimize Google Drive Folder Creation
**Learning:** `google_drive.create_folder_if_not_exists` makes a redundant `files().list()` call even when the caller (migration script) already knows the folder doesn't exist via its local cache.
**Action:** Implemented `create_folder` to skip the check and updated `migrate.py` to use it when the cache misses. This saves 1 API call per new folder.

## 2026-01-24 - Parallelize Google Drive Uploads
**Learning:** `google-api-python-client` service objects using the default `httplib2` transport are NOT thread-safe for concurrent requests because `httplib2.Http` is not thread-safe.
**Action:** When parallelizing uploads, use `threading.local()` to store a separate `service` instance for each thread to ensure safety.

## 2026-01-31 - Safe API Optimization
**Learning:** Adding `$select` to restrict API fields is a high-risk optimization if all downstream consumers are not fully audited, as it can cause unexpected `KeyError`s.
**Action:** For general-purpose optimizations, prioritize `$top` (page size) increases over `$select` (field restriction) unless payload size is a critical bottleneck and consumers are strictly controlled.

## 2026-02-07 - OneDrive Connection Pooling
**Learning:** `requests.get` creates a new TCP/SSL connection for every call. In a migration tool iterating over thousands of pages/files, the handshake overhead is significant (50-100ms per call).
**Action:** Use `requests.Session()` to persist connections. This is especially effective for pagination loops (`get_drive_items`) where multiple sequential requests go to the same host (`graph.microsoft.com`).
