## 2024-05-23 - [CRITICAL] Missing .gitignore for Sensitive Files
**Vulnerability:** The project lacks a `.gitignore` file, while it generates and uses sensitive files (`config.json`, `token_onedrive.bin`, `token_google.pickle`).
**Learning:** Even with secure code, environment configuration can lead to catastrophic secret leakage if users inadvertently commit these files.
**Prevention:** Always initialize projects with a restrictive `.gitignore` that explicitly excludes configuration and token cache files. Added `.gitignore` instructions to `SETUP.md` or similar documentation (though strictly I am fixing code today).

## 2024-05-23 - [HIGH] Google Drive API Query Injection
**Vulnerability:** The `google_drive.py` module constructed queries using manual string concatenation, only escaping single quotes (`'`). It failed to escape backslashes (`\`), allowing attackers (or weird filenames) to escape the closing quote and inject arbitrary query clauses or cause syntax errors.
**Learning:** When building queries for APIs (like Google Drive or SQL), always escape ALL special characters defined by the syntax. For Google Drive, `\` is an escape character and must itself be escaped.
**Prevention:** Use `name.replace("\\", "\\\\").replace("'", "\\'")` when constructing Google Drive queries, or use parameterized queries if the API supports them (Google Drive API `q` parameter does not support bind variables in the traditional sense).
