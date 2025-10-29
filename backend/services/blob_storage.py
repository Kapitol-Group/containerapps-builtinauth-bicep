"""
Azure Blob Storage service for managing tender documents
"""
import logging
import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
from io import BytesIO

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings
from azure.identity import DefaultAzureCredential
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Service for managing tender documents in Azure Blob Storage"""

    def __init__(self, account_name: str, container_name: str = 'tenders'):
        """
        Initialize the blob storage service

        Args:
            account_name: Azure Storage account name
            container_name: Container name for tender documents
        """
        self.account_name = account_name
        self.container_name = container_name

        if not account_name:
            print(
                "Warning: AZURE_STORAGE_ACCOUNT_NAME not set. Blob storage will not work.")
            self.container_client = None
            return

        # Use DefaultAzureCredential for managed identity authentication
        account_url = f"https://{account_name}.blob.core.windows.net"
        credential = DefaultAzureCredential()

        self.blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )

        self.container_client = self.blob_service_client.get_container_client(
            container_name)

        # Ensure container exists
        try:
            self.container_client.get_container_properties()
        except Exception:
            self.container_client.create_container()

    def list_tenders(self) -> List[Dict]:
        """
        List all tenders (top-level folders in the container)

        Returns:
            List of tender dictionaries
        """
        if not self.container_client:
            return []

        tenders = {}
        blob_list = self.container_client.list_blobs(include=['metadata'])

        for blob in blob_list:
            # Extract tender_id from blob path (format: tender_id/...)
            parts = blob.name.split('/')
            if len(parts) < 2:
                continue

            tender_id = parts[0]

            # Check if this is the metadata file for the tender
            if blob.name.endswith('.tender_metadata'):
                if tender_id not in tenders:
                    tenders[tender_id] = {
                        'id': tender_id,
                        'name': blob.metadata.get('tender_name', tender_id) if blob.metadata else tender_id,
                        'created_at': blob.metadata.get('created_at') if blob.metadata else None,
                        'created_by': blob.metadata.get('created_by') if blob.metadata else None,
                        'file_count': 0
                    }
                else:
                    # Update tender metadata from the metadata file
                    tenders[tender_id]['name'] = blob.metadata.get(
                        'tender_name', tender_id) if blob.metadata else tender_id
                    tenders[tender_id]['created_at'] = blob.metadata.get(
                        'created_at') if blob.metadata else None
                    tenders[tender_id]['created_by'] = blob.metadata.get(
                        'created_by') if blob.metadata else None
                continue

            # Initialize tender if not exists (in case metadata file hasn't been seen yet)
            if tender_id not in tenders:
                tenders[tender_id] = {
                    'id': tender_id,
                    'name': tender_id,
                    'created_at': None,
                    'created_by': None,
                    'file_count': 0
                }

            # Only count actual files (not directories or empty blobs)
            if blob.size > 0 and not blob.name.endswith('/'):
                filename = blob.name.split('/')[-1]
                if filename:  # Ensure there's a filename
                    tenders[tender_id]['file_count'] += 1

        return list(tenders.values())

    def create_tender(self, tender_name: str, created_by: str, metadata: Dict = None) -> Dict:
        """
        Create a new tender (creates a folder with metadata file)

        Args:
            tender_name: Name of the tender
            created_by: User who created the tender
            metadata: Additional metadata for the tender

        Returns:
            Tender information dictionary
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        # Generate tender ID from name
        tender_id = tender_name.replace(' ', '-').lower()

        # Create a metadata blob to mark the tender folder
        metadata_blob_name = f"{tender_id}/.tender_metadata"

        tender_metadata = {
            'tender_name': tender_name,
            'created_by': created_by,
            'created_at': datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        blob_client = self.container_client.get_blob_client(metadata_blob_name)
        blob_client.upload_blob(
            data=b'',
            metadata=tender_metadata,
            overwrite=True
        )

        return {
            'id': tender_id,
            'name': tender_name,
            **tender_metadata
        }

    def get_tender(self, tender_id: str) -> Optional[Dict]:
        """
        Get tender details

        Args:
            tender_id: Tender identifier

        Returns:
            Tender information or None if not found
        """
        if not self.container_client:
            return None

        metadata_blob_name = f"{tender_id}/.tender_metadata"

        try:
            blob_client = self.container_client.get_blob_client(
                metadata_blob_name)
            properties = blob_client.get_blob_properties()

            return {
                'id': tender_id,
                'name': properties.metadata.get('tender_name', tender_id),
                **properties.metadata
            }
        except Exception:
            return None

    def delete_tender(self, tender_id: str):
        """
        Delete a tender and all its files

        Args:
            tender_id: Tender identifier
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        logger.info(f"Deleting tender: {tender_id}")

        # Delete all blobs with the tender_id prefix
        blob_list = self.container_client.list_blobs(
            name_starts_with=f"{tender_id}/")

        deleted_count = 0
        errors = []

        # Separate files and directories
        files_to_delete = []
        directories = []

        for blob in blob_list:
            # Skip only directory markers (blobs ending with /)
            # Keep .tender_metadata and actual files even if size is 0
            if blob.name.endswith('/'):
                directories.append(blob.name)
                logger.debug(f"Skipping directory marker: {blob.name}")
                continue

            files_to_delete.append(blob.name)

        logger.info(
            f"Found {len(files_to_delete)} files and {len(directories)} directory markers for tender {tender_id}")

        # Delete all files (directories will be removed automatically in hierarchical namespace)
        for blob_name in files_to_delete:
            try:
                blob_client = self.container_client.get_blob_client(blob_name)
                blob_client.delete_blob()
                deleted_count += 1
                logger.debug(f"Deleted blob: {blob_name}")
            except Exception as e:
                error_msg = f"Failed to delete blob {blob_name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Successfully deleted {deleted_count} files for tender {tender_id}")

        if errors:
            raise Exception(
                f"Failed to delete some files: {'; '.join(errors)}")

    def list_files(self, tender_id: str, exclude_batched: bool = False) -> List[Dict]:
        """
        List all files in a tender

        Args:
            tender_id: Tender identifier
            exclude_batched: If True, exclude files that belong to a batch

        Returns:
            List of file information dictionaries
        """
        if not self.container_client:
            return []

        files = []
        blob_list = self.container_client.list_blobs(
            name_starts_with=f"{tender_id}/",
            include=['metadata']
        )

        for blob in blob_list:
            # Skip metadata file and batch files
            if blob.name.endswith('.tender_metadata') or '/.batch_' in blob.name:
                continue

            # Skip empty/virtual directory blobs (blobs with no size or ending with /)
            if blob.size == 0 or blob.name.endswith('/'):
                continue

            # Skip blobs without a filename (e.g., just directories)
            filename = blob.name.split('/')[-1]
            if not filename:
                continue

            # Check if file belongs to a batch
            has_batch_id = blob.metadata and blob.metadata.get(
                'batch_id') if blob.metadata else False

            # Skip batched files if exclude_batched is True
            if exclude_batched and has_batch_id:
                continue

            files.append({
                'name': filename,
                'path': blob.name,
                'size': blob.size,
                'content_type': blob.content_settings.content_type if blob.content_settings else None,
                'category': blob.metadata.get('category', 'uncategorized') if blob.metadata else 'uncategorized',
                'uploaded_by': blob.metadata.get('uploaded_by') if blob.metadata else None,
                'uploaded_at': blob.metadata.get('uploaded_at') if blob.metadata else None,
                'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                'source': blob.metadata.get('source', 'local') if blob.metadata else 'local',
                'batch_id': blob.metadata.get('batch_id') if blob.metadata else None
            })

        return files

    def upload_file(self, tender_id: str, file: FileStorage, category: str = 'uncategorized',
                    uploaded_by: str = 'Unknown', source: str = 'local') -> Dict:
        """
        Upload a file to a tender

        Args:
            tender_id: Tender identifier
            file: File to upload
            category: File category
            uploaded_by: User who uploaded the file
            source: Source of the file ('local' or 'sharepoint')

        Returns:
            File information dictionary
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        # Construct blob path: tender_id/category/filename
        blob_name = f"{tender_id}/{category}/{file.filename}"

        file_metadata = {
            'category': category,
            'uploaded_by': uploaded_by,
            'uploaded_at': datetime.utcnow().isoformat(),
            'original_filename': file.filename,
            'source': source
        }

        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            data=file.stream,
            metadata=file_metadata,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)
        )

        return {
            'name': file.filename,
            'path': blob_name,
            'category': category,
            'source': source,
            **file_metadata
        }

    def download_file(self, tender_id: str, file_path: str) -> Dict:
        """
        Download a file from a tender

        Args:
            tender_id: Tender identifier
            file_path: Full blob path of the file

        Returns:
            Dictionary with file content and metadata
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        blob_client = self.container_client.get_blob_client(file_path)

        download_stream = blob_client.download_blob()
        properties = blob_client.get_blob_properties()

        return {
            'content': download_stream.readall(),
            'filename': file_path.split('/')[-1],
            'content_type': properties.content_settings.content_type if properties.content_settings else 'application/octet-stream',
            'metadata': properties.metadata
        }

    def update_file_metadata(self, tender_id: str, file_path: str, metadata: Dict):
        """
        Update file metadata

        Args:
            tender_id: Tender identifier
            file_path: Full blob path of the file
            metadata: New metadata to set
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        blob_client = self.container_client.get_blob_client(file_path)

        # Get existing metadata
        properties = blob_client.get_blob_properties()
        existing_metadata = properties.metadata or {}

        # Update with new metadata
        existing_metadata.update(metadata)

        blob_client.set_blob_metadata(existing_metadata)

    def delete_file(self, tender_id: str, file_path: str):
        """
        Delete a file from a tender

        Args:
            tender_id: Tender identifier
            file_path: Full blob path of the file
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        blob_client = self.container_client.get_blob_client(file_path)
        blob_client.delete_blob()

    # Batch Management Methods

    def create_batch(self, tender_id: str, batch_name: str, discipline: str,
                     file_paths: List[str], title_block_coords: Dict,
                     submitted_by: str, job_id: Optional[str] = None) -> Dict:
        """
        Create a new extraction batch

        Args:
            tender_id: Tender identifier
            batch_name: User-friendly name for the batch
            discipline: Selected discipline (Architectural, Structural, etc.)
            file_paths: List of file paths included in the batch
            title_block_coords: Dictionary with x, y, width, height coordinates
            submitted_by: User who submitted the batch
            job_id: UiPath job ID (optional)

        Returns:
            Batch information dictionary
        """
        if not self.container_client:
            raise Exception("Blob storage not configured")

        # Generate unique batch ID
        batch_id = str(uuid.uuid4())

        # Create batch metadata blob
        batch_blob_name = f"{tender_id}/.batch_{batch_id}"

        batch_metadata = {
            'batch_id': batch_id,
            'batch_name': batch_name,
            'discipline': discipline,
            'file_paths': json.dumps(file_paths),
            'title_block_coords': json.dumps(title_block_coords),
            'status': 'pending',
            'submitted_at': datetime.utcnow().isoformat(),
            'submitted_by': submitted_by,
            'file_count': str(len(file_paths)),
            'job_id': job_id or ''
        }

        blob_client = self.container_client.get_blob_client(batch_blob_name)
        blob_client.upload_blob(
            data=b'',
            metadata=batch_metadata,
            overwrite=True
        )

        logger.info(
            f"Created batch {batch_id} for tender {tender_id} with {len(file_paths)} files")

        return {
            'batch_id': batch_id,
            'batch_name': batch_name,
            'discipline': discipline,
            'file_paths': file_paths,
            'title_block_coords': title_block_coords,
            'status': 'pending',
            'submitted_at': batch_metadata['submitted_at'],
            'submitted_by': submitted_by,
            'file_count': len(file_paths),
            'job_id': job_id
        }

    def list_batches(self, tender_id: str) -> List[Dict]:
        """
        List all batches for a tender

        Args:
            tender_id: Tender identifier

        Returns:
            List of batch dictionaries sorted by submitted_at (descending)
        """
        if not self.container_client:
            return []

        batches = []
        blob_list = self.container_client.list_blobs(
            name_starts_with=f"{tender_id}/.batch_",
            include=['metadata']
        )

        for blob in blob_list:
            if blob.metadata:
                try:
                    batch = {
                        'batch_id': blob.metadata.get('batch_id'),
                        'batch_name': blob.metadata.get('batch_name'),
                        'discipline': blob.metadata.get('discipline'),
                        'file_paths': json.loads(blob.metadata.get('file_paths', '[]')),
                        'title_block_coords': json.loads(blob.metadata.get('title_block_coords', '{}')),
                        'status': blob.metadata.get('status', 'pending'),
                        'submitted_at': blob.metadata.get('submitted_at'),
                        'submitted_by': blob.metadata.get('submitted_by'),
                        'file_count': int(blob.metadata.get('file_count', 0)),
                        'job_id': blob.metadata.get('job_id', '')
                    }
                    batches.append(batch)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(
                        f"Error parsing batch metadata for {blob.name}: {e}")
                    continue

        # Sort by submitted_at descending
        batches.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)

        logger.info(f"Found {len(batches)} batches for tender {tender_id}")
        return batches

    def get_batch(self, tender_id: str, batch_id: str) -> Optional[Dict]:
        """
        Get batch details by ID

        Args:
            tender_id: Tender identifier
            batch_id: Batch identifier

        Returns:
            Batch information dictionary or None if not found
        """
        if not self.container_client:
            return None

        batch_blob_name = f"{tender_id}/.batch_{batch_id}"

        try:
            blob_client = self.container_client.get_blob_client(
                batch_blob_name)
            properties = blob_client.get_blob_properties()

            if properties.metadata:
                return {
                    'batch_id': properties.metadata.get('batch_id'),
                    'batch_name': properties.metadata.get('batch_name'),
                    'discipline': properties.metadata.get('discipline'),
                    'file_paths': json.loads(properties.metadata.get('file_paths', '[]')),
                    'title_block_coords': json.loads(properties.metadata.get('title_block_coords', '{}')),
                    'status': properties.metadata.get('status', 'pending'),
                    'submitted_at': properties.metadata.get('submitted_at'),
                    'submitted_by': properties.metadata.get('submitted_by'),
                    'file_count': int(properties.metadata.get('file_count', 0)),
                    'job_id': properties.metadata.get('job_id', '')
                }
        except Exception as e:
            logger.error(f"Error getting batch {batch_id}: {e}")
            return None

    def update_batch_status(self, tender_id: str, batch_id: str, status: str) -> Optional[Dict]:
        """
        Update batch status

        Args:
            tender_id: Tender identifier
            batch_id: Batch identifier
            status: New status (pending, running, completed, failed)

        Returns:
            Updated batch information or None if not found
        """
        if not self.container_client:
            return None

        # Validate status
        valid_statuses = ['pending', 'running', 'completed', 'failed']
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        batch_blob_name = f"{tender_id}/.batch_{batch_id}"

        try:
            blob_client = self.container_client.get_blob_client(
                batch_blob_name)
            properties = blob_client.get_blob_properties()

            if not properties.metadata:
                return None

            # Update metadata
            metadata = dict(properties.metadata)
            metadata['status'] = status

            blob_client.set_blob_metadata(metadata)

            logger.info(f"Updated batch {batch_id} status to {status}")

            # Return updated batch
            return self.get_batch(tender_id, batch_id)

        except Exception as e:
            logger.error(f"Error updating batch {batch_id} status: {e}")
            return None

    def get_batch_files(self, tender_id: str, batch_id: str) -> List[Dict]:
        """
        Get all files belonging to a batch

        Args:
            tender_id: Tender identifier
            batch_id: Batch identifier

        Returns:
            List of file information dictionaries
        """
        if not self.container_client:
            return []

        # Get batch to retrieve file paths
        batch = self.get_batch(tender_id, batch_id)
        if not batch:
            return []

        file_paths = batch.get('file_paths', [])
        files = []

        for file_path in file_paths:
            try:
                blob_client = self.container_client.get_blob_client(file_path)
                properties = blob_client.get_blob_properties()

                filename = file_path.split('/')[-1]
                files.append({
                    'name': filename,
                    'path': file_path,
                    'size': properties.size,
                    'content_type': properties.content_settings.content_type if properties.content_settings else None,
                    'category': properties.metadata.get('category', 'uncategorized') if properties.metadata else 'uncategorized',
                    'uploaded_by': properties.metadata.get('uploaded_by') if properties.metadata else None,
                    'uploaded_at': properties.metadata.get('uploaded_at') if properties.metadata else None,
                    'last_modified': properties.last_modified.isoformat() if properties.last_modified else None,
                    'source': properties.metadata.get('source', 'local') if properties.metadata else 'local',
                    'batch_id': properties.metadata.get('batch_id') if properties.metadata else None
                })
            except Exception as e:
                logger.error(f"Error getting file {file_path}: {e}")
                continue

        return files

    def update_files_category(self, tender_id: str, file_paths: List[str],
                              category: str, batch_id: str) -> int:
        """
        Bulk update category and batch_id for multiple files

        Args:
            tender_id: Tender identifier
            file_paths: List of file paths to update
            category: New category to set
            batch_id: Batch ID to reference

        Returns:
            Number of files successfully updated
        """
        if not self.container_client:
            return 0

        updated_count = 0

        for file_path in file_paths:
            try:
                blob_client = self.container_client.get_blob_client(file_path)
                properties = blob_client.get_blob_properties()

                # Get existing metadata and update
                metadata = dict(
                    properties.metadata) if properties.metadata else {}
                metadata['category'] = category
                metadata['batch_id'] = batch_id
                metadata['submitted_at'] = datetime.utcnow().isoformat()

                blob_client.set_blob_metadata(metadata)
                updated_count += 1

            except Exception as e:
                logger.error(f"Error updating file {file_path} metadata: {e}")
                continue

        logger.info(
            f"Updated {updated_count}/{len(file_paths)} files with category={category}, batch_id={batch_id}")
        return updated_count

    def delete_batch(self, tender_id: str, batch_id: str) -> bool:
        """
        Delete a batch (admin only - metadata blob only, files remain)

        Args:
            tender_id: Tender identifier
            batch_id: Batch identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.container_client:
            return False

        batch_blob_name = f"{tender_id}/.batch_{batch_id}"

        try:
            blob_client = self.container_client.get_blob_client(
                batch_blob_name)
            blob_client.delete_blob()
            logger.info(f"Deleted batch {batch_id} metadata")
            return True
        except Exception as e:
            logger.error(f"Error deleting batch {batch_id}: {e}")
            return False
