"""
File Storage Utility
Handles local file storage with AWS S3 provision
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Storage configuration
STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'local')  # 'local' or 's3'
# Upload directory at project root to match static file serving
ROOT_DIR = Path(__file__).parent.parent.parent  # Go up to project root
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

# AWS S3 Configuration (for future use)
AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET', '')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')


async def save_file(file_content: bytes, filename: str, subfolder: str = 'images') -> str:
    """
    Save file to storage (local or S3)
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        subfolder: Subfolder within uploads directory
        
    Returns:
        URL/path to the saved file
    """
    if STORAGE_TYPE == 's3':
        return await _save_to_s3(file_content, filename, subfolder)
    else:
        return await _save_to_local(file_content, filename, subfolder)


async def _save_to_local(file_content: bytes, filename: str, subfolder: str) -> str:
    """Save file to local storage"""
    # Create subfolder
    subfolder_path = UPLOAD_DIR / subfolder
    subfolder_path.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename with timestamp
    # Sanitize filename to remove spaces and special characters for URL safety
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_ext = Path(filename).suffix
    # Remove spaces and special chars, keep only alphanumeric, dots, hyphens, underscores
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in Path(filename).stem)
    unique_filename = f"{timestamp}_{safe_name}{file_ext}"
    
    # Save file
    file_path = subfolder_path / unique_filename
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Return relative path for serving (URL encode if needed)
    from urllib.parse import quote
    relative_path = f"/uploads/{subfolder}/{quote(unique_filename)}"
    logger.info(f"File saved locally: {file_path}, URL: {relative_path}")
    return relative_path


async def _save_to_s3(file_content: bytes, filename: str, subfolder: str) -> str:
    """Save file to AWS S3 (future implementation)"""
    # TODO: Implement S3 upload when needed
    # For now, fallback to local
    logger.warning("S3 storage not yet implemented, using local storage")
    return await _save_to_local(file_content, filename, subfolder)


def get_file_url(file_path: str) -> str:
    """
    Get full URL for a file path
    
    Args:
        file_path: Relative file path from save_file
        
    Returns:
        Full URL to access the file
    """
    if STORAGE_TYPE == 's3' and AWS_S3_BUCKET:
        # Return S3 URL
        return f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{file_path.lstrip('/')}"
    else:
        # Return local URL (assuming backend serves static files)
        # Use REACT_APP_BACKEND_URL if available, otherwise default to localhost
        backend_url = os.environ.get('REACT_APP_BACKEND_URL') or os.environ.get('BACKEND_URL', 'http://localhost:8001')
        # Ensure no double slashes
        if file_path.startswith('/'):
            return f"{backend_url}{file_path}"
        else:
            return f"{backend_url}/{file_path}"


async def delete_file(file_path: str) -> bool:
    """
    Delete a file from storage
    
    Args:
        file_path: Relative file path
        
    Returns:
        True if deleted, False otherwise
    """
    if STORAGE_TYPE == 's3':
        return await _delete_from_s3(file_path)
    else:
        return await _delete_from_local(file_path)


async def _delete_from_local(file_path: str) -> bool:
    """Delete file from local storage"""
    try:
        # Remove /uploads prefix if present
        if file_path.startswith('/uploads/'):
            file_path = file_path[9:]  # Remove '/uploads/'
        
        full_path = UPLOAD_DIR / file_path
        if full_path.exists():
            full_path.unlink()
            logger.info(f"File deleted: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False


async def _delete_from_s3(file_path: str) -> bool:
    """Delete file from S3 (future implementation)"""
    # TODO: Implement S3 delete when needed
    logger.warning("S3 delete not yet implemented")
    return False

