# Setup Guide

This tool requires access to your personal OneDrive and Google Drive. Because these are your private accounts, you must create your own "App Keys" (Client IDs) to allow this script to log in on your behalf.

Follow these steps carefully.

## Prerequisites

1.  Python installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Rename `config_template.json` to `config.json`. You will paste the keys you generate below into this file.

---

## Part 1: Google Drive Setup

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a **New Project** (name it "Drive Migration" or similar).
3.  **Enable the API:**
    *   In the search bar, type "Google Drive API" and select it.
    *   Click **Enable**.
4.  **Configure Consent Screen:**
    *   Go to **APIs & Services > OAuth consent screen**.
    *   Choose **External** (since you are a personal user) and click **Create**.
    *   Fill in required fields (App name, support email, developer contact info).
    *   Click **Save and Continue**.
    *   **Scopes:** Click **Add or Remove Scopes**. Search for and select `.../auth/drive.file` (See, edit, create, and delete only the specific Google Drive files you use with this app) OR `.../auth/drive` (See, edit, create, and delete all of your Google Drive files). **Recommended: `.../auth/drive`** since we are syncing everything.
    *   **Test Users:** Add your own Google email address as a test user. (Crucial, otherwise you cannot log in).
5.  **Create Credentials:**
    *   Go to **APIs & Services > Credentials**.
    *   Click **Create Credentials > OAuth client ID**.
    *   Application type: **Desktop app**.
    *   Name: "Migration Script".
    *   Click **Create**.
6.  **Copy the Keys:**
    *   You will see a popup with "Your Client ID" and "Your Client Secret".
    *   Copy these into the `google` section of your `config.json` file.

---

## Part 2: Microsoft (OneDrive) Setup

1.  Go to the [Azure App Registrations Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
    *   Note: You might need to sign in with your personal Microsoft account.
2.  Click **New registration**.
3.  **Register an application:**
    *   Name: "OneDrive Migration".
    *   Supported account types: **Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)**. (This is the 3rd option usually).
    *   Redirect URI (optional): Select **Public client/native (mobile & desktop)** and enter `http://localhost`.
    *   Click **Register**.
4.  **Copy Client ID:**
    *   On the Overview page, copy the **Application (client) ID**. Paste this into `config.json` under `microsoft` > `client_id`.
5.  **Create Client Secret:**
    *   In the left menu, click **Certificates & secrets**.
    *   Click **New client secret**.
    *   Description: "auth". Expires: 6 months (or whatever you prefer).
    *   Click **Add**.
    *   **Copy the Value** (not the Secret ID) immediately. It will be hidden later. Paste this into `config.json` under `microsoft` > `client_secret`.
    *   *Note:* For strictly public client apps (like this script), a secret is sometimes not required if we use PKCE, but providing it ensures standard web flow compatibility if we need it. However, for the `msal` library with `PublicClientApplication`, we often just need the Client ID. If the script asks for a secret and you only have an ID, check the code implementation. *Update: This script uses PublicClientApplication which typically only needs Client ID, but we will support Secret if configured for Confidential Client flows. For personal accounts, usually Client ID is sufficient.*

## Part 3: Running the Tool

1.  Run the script:
    ```bash
    python migrate.py
    ```
2.  The script will open your browser to log in to Google.
3.  The script will open your browser (or give you a link) to log in to Microsoft.
4.  Wait for the sync to complete.
