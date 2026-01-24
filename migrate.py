import os
import json
import logging
import datetime
import concurrent.futures
import threading

# Import our modules
import google_drive
from onedrive import OneDriveClient

# Global thread-local storage for thread-safe Google Drive service access
thread_local_data = threading.local()

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

def get_thread_safe_service(creds):
    """
    Returns a thread-local Google Drive service instance.
    """
    if not hasattr(thread_local_data, 'service'):
        # Re-build service for this thread to ensure thread safety
        thread_local_data.service = google_drive.build('drive', 'v3', credentials=creds)
    return thread_local_data.service

def process_file_upload(od_client, creds, item, gd_parent_id, current_path, gd_folder_contents):
    """
    Handles the upload of a single file in a thread-safe manner.
    """
    try:
        # Use thread-local service
        gd_service = get_thread_safe_service(creds)

        item_name = item.get('name')
        item_id = item.get('id')

        # Check cache instead of making API call
        existing_file = gd_folder_contents.get(item_name)
        existing_file_id = None

        if existing_file and existing_file['mimeType'] != 'application/vnd.google-apps.folder':
            existing_file_id = existing_file['id']

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

def sync_folder(od_client, gd_service, od_folder_id, gd_parent_id, path_prefix="", executor=None, futures=None, creds=None):
    """
    Recursively syncs a OneDrive folder to a Google Drive folder.
    """
    logger.info(f"Scanning folder: {path_prefix if path_prefix else 'Root'}")

    # Optimization: Pre-fetch Google Drive folder contents to avoid N API calls
    try:
        gd_folder_contents = google_drive.list_folder_contents(gd_service, gd_parent_id)
    except Exception as e:
        logger.error(f"Failed to list Google Drive folder {gd_parent_id}: {e}")
        return

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
                # Check cache first
                existing_folder = gd_folder_contents.get(item_name)
                if existing_folder and existing_folder['mimeType'] == 'application/vnd.google-apps.folder':
                    gd_folder_id = existing_folder['id']
                    logger.info(f"Found existing folder '{item_name}' (ID: {gd_folder_id})")
                else:
                    # Not in cache (or name conflict with file), create it
                    # Note: create_folder_if_not_exists performs a check, which is redundant if we trust our cache.
                    # Optimization: Use create_folder directly to avoid the redundant API call.
                    gd_folder_id = google_drive.create_folder(gd_service, item_name, gd_parent_id)

                # Recurse
                sync_folder(od_client, gd_service, item_id, gd_folder_id, current_path, executor, futures, creds)
            except Exception as e:
                logger.error(f"Error processing folder {current_path}: {e}")

        elif item_type == 'file':
            # Handle File
            if executor and creds:
                # Submit to thread pool
                future = executor.submit(process_file_upload, od_client, creds, item, gd_parent_id, current_path, gd_folder_contents)
                if futures is not None:
                    futures.append(future)
            else:
                # Fallback or initialization error
                logger.warning("Executor or credentials missing, running synchronously.")
                # We need a creds object here if we use process_file_upload, or pass gd_service if we used the old way.
                # But since we refactored, process_file_upload expects creds.
                if creds:
                    process_file_upload(od_client, creds, item, gd_parent_id, current_path, gd_folder_contents)
                else:
                    logger.error(f"Cannot process file {current_path}: Credentials missing.")

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
        # Get credentials separately for thread safety
        creds = google_drive.get_credentials(config)
        # Create main thread service
        gd_service = google_drive.build('drive', 'v3', credentials=creds)
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

    # Get Google Drive Root ID
    gd_root_id = 'root'

    # Optimization: Use ThreadPoolExecutor for parallel file uploads
    max_workers = 5
    logger.info(f"Using {max_workers} worker threads for file uploads.")

    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        sync_folder(od_client, gd_service, od_root_id, gd_root_id, executor=executor, futures=futures, creds=creds)

        # Wait for all uploads to complete
        logger.info("Scanning complete. Waiting for file uploads to finish...")
        concurrent.futures.wait(futures)

    logger.info("Migration completed.")

if __name__ == "__main__":
    main()
