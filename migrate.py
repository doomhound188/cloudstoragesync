import os
import json
import logging
import datetime
from pathlib import Path

# Import our modules
import google_drive
from onedrive import OneDriveClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        logger.error(f"Configuration file {config_path} not found. Please rename config_template.json and fill in your keys.")
        raise FileNotFoundError("config.json not found")

    with open(config_path, 'r') as f:
        return json.load(f)

def get_timestamped_name(filename):
    """
    Appends a timestamp to the filename.
    Example: image.jpg -> image_20231027_103000.jpg
    """
    name, ext = os.path.splitext(filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name}_{timestamp}{ext}"

def sync_folder(od_client, gd_service, od_folder_id, gd_parent_id, path_prefix=""):
    """
    Recursively syncs a OneDrive folder to a Google Drive folder.
    """
    logger.info(f"Scanning folder: {path_prefix if path_prefix else 'Root'}")

    try:
        items = od_client.get_drive_items(od_folder_id)
    except Exception as e:
        logger.error(f"Failed to list items for folder {path_prefix}: {e}")
        return

    for item in items:
        item_name = item.get('name')
        item_id = item.get('id')
        item_type = 'folder' if 'folder' in item else 'file'

        current_path = os.path.join(path_prefix, item_name)

        if item_type == 'folder':
            # Handle Folder
            try:
                # Find or create corresponding folder in Google Drive
                gd_folder_id = google_drive.create_folder_if_not_exists(gd_service, item_name, gd_parent_id)
                # Recurse
                sync_folder(od_client, gd_service, item_id, gd_folder_id, current_path)
            except Exception as e:
                logger.error(f"Error processing folder {current_path}: {e}")

        elif item_type == 'file':
            # Handle File
            try:
                # Check if file exists in the destination Google Drive folder
                existing_file_id = google_drive.file_exists(gd_service, item_name, gd_parent_id)

                target_name = item_name
                if existing_file_id:
                    # Conflict: Rename the NEW file (the one coming from OneDrive)
                    target_name = get_timestamped_name(item_name)
                    logger.info(f"File conflict for '{item_name}'. Uploading as '{target_name}'")

                logger.info(f"Transferring file: {current_path} -> {target_name}")

                # Get file metadata
                file_size = item.get('size', 0)
                file_mime = item.get('file', {}).get('mimeType', 'application/octet-stream')

                # Get stream from OneDrive
                file_stream = od_client.get_file_stream(item_id)

                # Upload to Google Drive
                google_drive.upload_file(gd_service, target_name, gd_parent_id, file_stream, file_size, file_mime)

            except Exception as e:
                logger.error(f"Error transferring file {current_path}: {e}")

def main():
    logger.info("Starting Migration Tool...")

    # 1. Load Config
    try:
        config = load_config()
    except Exception as e:
        logger.error(e)
        return

    # 2. Authenticate Google Drive
    logger.info("Authenticating with Google Drive...")
    try:
        gd_service = google_drive.authenticate(config)
    except Exception as e:
        logger.error(f"Google Drive Authentication failed: {e}")
        return

    # 3. Authenticate OneDrive
    logger.info("Authenticating with OneDrive...")
    try:
        od_client = OneDriveClient(config)
        od_client.authenticate()
    except Exception as e:
        logger.error(f"OneDrive Authentication failed: {e}")
        return

    # 4. Start Sync
    logger.info("Authentication successful. Starting sync from OneDrive Root.")

    # Get OneDrive Root ID (usually 'root')
    od_root_id = 'root'

    # Get Google Drive Root ID (we can use None or 'root' depending on API, usually we just don't specify parent or use 'root' alias)
    # However, to avoid cluttering the root, maybe we should create a 'OneDrive Backup' folder?
    # The requirement was "Sync entire content". Usually implies mirroring root-to-root.
    # I'll stick to root-to-root for now, or let the user decide.
    # Let's assume root-to-root, so we check if top-level folders exist in 'root'.
    # In Google Drive API, 'root' is an alias for the root folder ID.
    gd_root_id = 'root'

    sync_folder(od_client, gd_service, od_root_id, gd_root_id)

    logger.info("Migration completed.")

if __name__ == "__main__":
    main()
