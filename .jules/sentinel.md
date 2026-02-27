## 2024-05-23 - [CRITICAL] Missing .gitignore for Sensitive Files
**Vulnerability:** The project lacks a `.gitignore` file, while it generates and uses sensitive files (`config.json`, `token_onedrive.bin`, `token_google.pickle`).
**Learning:** Even with secure code, environment configuration can lead to catastrophic secret leakage if users inadvertently commit these files.
**Prevention:** Always initialize projects with a restrictive `.gitignore` that explicitly excludes configuration and token cache files. Added `.gitignore` instructions to `SETUP.md` or similar documentation (though strictly I am fixing code today).

## 2024-05-23 - [HIGH] Google Drive API Query Injection
**Vulnerability:** The `google_drive.py` module constructed queries using manual string concatenation, only escaping single quotes (`'`). It failed to escape backslashes (`\`), allowing attackers (or weird filenames) to escape the closing quote and inject arbitrary query clauses or cause syntax errors.
**Learning:** When building queries for APIs (like Google Drive or SQL), always escape ALL special characters defined by the syntax. For Google Drive, `\` is an escape character and must itself be escaped.
**Prevention:** Use `name.replace("\\", "\\\\").replace("'", "\\'")` when constructing Google Drive queries, or use parameterized queries if the API supports them (Google Drive API `q` parameter does not support bind variables in the traditional sense).

## 2026-01-16 - [HIGH] Insecure Deserialization of Google Credentials
**Vulnerability:** The application used Python's `pickle` module to store and load Google Drive credentials (`token_google.pickle`). Pickle is unsafe and allows arbitrary code execution if the file is compromised.
**Learning:** Legacy examples from library documentation often use `pickle`, which is now considered a security antipattern for persisting data.
**Prevention:** Replaced `pickle` with JSON serialization using `Credentials.to_json()` and `Credentials.from_authorized_user_info()`. Added `token_google.json` to `.gitignore`.

## 2026-01-30 - [HIGH] Insecure Token Cache Permissions
**Vulnerability:** The application saved sensitive authentication tokens (`token_google.json`, `token_onedrive.bin`) with default file permissions (often `0o644`), allowing other users on the system to read them.
**Learning:** Default `open(..., 'w')` behavior honors the system `umask`, which is typically permissive. For sensitive files, explicit permission management is required at creation time.
**Prevention:** Use `os.open` with `os.O_CREAT | os.O_WRONLY | os.O_TRUNC` and `0o600` mode, then wrap the file descriptor with `os.fdopen`.

## 2026-02-05 - [MEDIUM] Missing Timeout on External API Calls
**Vulnerability:** The application made HTTP requests to the Microsoft Graph API using `requests.get()` without specifying a `timeout`.
**Learning:** Python's `requests` library does not apply a timeout by default, meaning a hung connection could cause the application to freeze indefinitely, potentially leading to a Denial of Service (DoS) if resources are exhausted.
**Prevention:** Always specify a `timeout` (e.g., `timeout=60`) in all network calls. Added a global `TIMEOUT` constant and applied it to all `requests.get()` calls in `onedrive.py`.
