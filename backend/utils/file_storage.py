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

# For Lambda, use /tmp which is writable; otherwise use local uploads folder
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    UPLOAD_DIR = Path('/tmp/uploads')
else:
    UPLOAD_DIR = ROOT_DIR / 'uploads'

# Create directory only if it doesn't exist (handle read-only filesystem)
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    # In Lambda, /tmp should work, but if not, just log and continue
    logger.warning(f"Could not create upload directory: {UPLOAD_DIR} - {e}")

# AWS S3 Configuration (for future use)
AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET', '')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-west-2')  # Default to us-west-2 to match deployment
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
    """Save file to AWS S3"""
    import boto3
    from botocore.exceptions import ClientError
    
    # Read region at runtime to ensure we get the latest value
    s3_region = os.environ.get('AWS_S3_REGION', 'us-west-2')
    s3_bucket = os.environ.get('AWS_S3_BUCKET', AWS_S3_BUCKET)
    
    try:
        s3_client = boto3.client('s3', region_name=s3_region)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = Path(filename).suffix
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in Path(filename).stem)
        unique_filename = f"{timestamp}_{safe_name}{file_ext}"
        
        # S3 key (path)
        s3_key = f"{subfolder}/{unique_filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=file_content,
            ContentType=_get_content_type(file_ext),
            ServerSideEncryption='AES256'
        )
        
        # Return relative path
        relative_path = f"/uploads/{subfolder}/{unique_filename}"
        logger.info(f"File saved to S3: s3://{s3_bucket}/{s3_key} in region {s3_region}")
        return relative_path
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        raise


def _get_content_type(file_ext: str) -> str:
    """Get content type from file extension"""
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
    }
    return content_types.get(file_ext.lower(), 'application/octet-stream')


def get_file_url(file_path: str) -> str:
    """
    Get full URL for a file path
    
    Args:
        file_path: Relative file path from save_file
        
    Returns:
        Full URL to access the file
    """
    # Read at runtime to ensure we get the latest values
    storage_type = os.environ.get('STORAGE_TYPE', STORAGE_TYPE)
    s3_bucket = os.environ.get('AWS_S3_BUCKET', AWS_S3_BUCKET)
    s3_region = os.environ.get('AWS_S3_REGION', AWS_S3_REGION)
    
    if storage_type == 's3' and s3_bucket:
        # Remove /uploads/ prefix if present (S3 keys don't have this prefix)
        s3_key = file_path.lstrip('/')
        if s3_key.startswith('uploads/'):
            s3_key = s3_key[8:]  # Remove 'uploads/' prefix
        
        # Return S3 URL with correct region
        url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
        logger.info(f"Generated S3 URL: {url} (bucket: {s3_bucket}, region: {s3_region}, key: {s3_key})")
        return url
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
    """Delete file from S3"""
    import boto3
    from botocore.exceptions import ClientError
    
    # Read at runtime
    s3_region = os.environ.get('AWS_S3_REGION', AWS_S3_REGION)
    s3_bucket = os.environ.get('AWS_S3_BUCKET', AWS_S3_BUCKET)
    
    try:
        s3_client = boto3.client('s3', region_name=s3_region)
        
        # Remove /uploads prefix if present
        if file_path.startswith('/uploads/'):
            s3_key = file_path[9:]  # Remove '/uploads/'
        else:
            s3_key = file_path.lstrip('/')
        
        # Delete from S3
        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
        logger.info(f"File deleted from S3: s3://{s3_bucket}/{s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Error deleting from S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting from S3: {e}")
        return False

