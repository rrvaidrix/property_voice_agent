# voice_assistant/utils.py

import os
import logging
import time

def delete_file(file_path):
    """
    Delete a file from the filesystem.
    
    Args:
    file_path (str): The path to the file to delete.
    """
    try:
        # Add a small delay to avoid file locking issues
        time.sleep(0.1)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Deleted file: {file_path}")
        else:
            logging.warning(f"File not found: {file_path}")
    except FileNotFoundError:
        logging.warning(f"File not found: {file_path}")
    except PermissionError:
        logging.warning(f"Permission denied when trying to delete file: {file_path} - file may be in use")
        # Try again after a longer delay
        try:
            time.sleep(1)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Successfully deleted file after retry: {file_path}")
        except Exception as retry_error:
            logging.warning(f"Still cannot delete file {file_path}: {retry_error}")
    except OSError as e:
        logging.error(f"Error deleting file {file_path}: {e}")
