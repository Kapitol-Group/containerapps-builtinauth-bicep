"""
Azure Blob Storage service for managing tender documents
"""
import os
from datetime import datetime
from typing import Dict, List, Optional
from io import BytesIO

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings
from azure.identity import DefaultAzureCredential
from werkzeug.datastructures import FileStorage


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

        # Delete all blobs with the tender_id prefix
        blob_list = self.container_client.list_blobs(
            name_starts_with=f"{tender_id}/")

        for blob in blob_list:
            blob_client = self.container_client.get_blob_client(blob.name)
            blob_client.delete_blob()

    def list_files(self, tender_id: str) -> List[Dict]:
        """
        List all files in a tender

        Args:
            tender_id: Tender identifier

        Returns:
            List of file information dictionaries
        """
        if not self.container_client:
            return []

        files = []
        blob_list = self.container_client.list_blobs(
            name_starts_with=f"{tender_id}/")

        for blob in blob_list:
            # Skip metadata file
            if blob.name.endswith('.tender_metadata'):
                continue

            # Skip empty/virtual directory blobs (blobs with no size or ending with /)
            if blob.size == 0 or blob.name.endswith('/'):
                continue

            # Skip blobs without a filename (e.g., just directories)
            filename = blob.name.split('/')[-1]
            if not filename:
                continue

            files.append({
                'name': filename,
                'path': blob.name,
                'size': blob.size,
                'content_type': blob.content_settings.content_type if blob.content_settings else None,
                'category': blob.metadata.get('category', 'uncategorized') if blob.metadata else 'uncategorized',
                'uploaded_by': blob.metadata.get('uploaded_by') if blob.metadata else None,
                'uploaded_at': blob.metadata.get('uploaded_at') if blob.metadata else None,
                'last_modified': blob.last_modified.isoformat() if blob.last_modified else None
            })

        return files

    def upload_file(self, tender_id: str, file: FileStorage, category: str = 'uncategorized',
                    uploaded_by: str = 'Unknown') -> Dict:
        """
        Upload a file to a tender

        Args:
            tender_id: Tender identifier
            file: File to upload
            category: File category
            uploaded_by: User who uploaded the file

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
            'original_filename': file.filename
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
