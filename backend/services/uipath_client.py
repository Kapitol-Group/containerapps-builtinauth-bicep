"""
UiPath REST API client for drawing metadata extraction with Entity Store integration
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from cuid2 import Cuid
import time

# Entity Store client imports
from entity_store_transformation_client import AuthenticatedClient
from entity_store_transformation_client.api.tender_project import (
    query_tender_project,
    add_tender_project
)
from entity_store_transformation_client.api.tender_submission import add_tender_submission
from entity_store_transformation_client.api.tender_file import (
    add_tender_file,
    batch_delete_tender_file
)
from entity_store_transformation_client.api.title_block_validation_users import (
    query_title_block_validation_users
)
from entity_store_transformation_client.models.tender_project import TenderProject
from entity_store_transformation_client.models.tender_submission import TenderSubmission
from entity_store_transformation_client.models.tender_file import TenderFile
from entity_store_transformation_client.models.title_block_validation_users import TitleBlockValidationUsers
from entity_store_transformation_client.models.tender_process_status import TenderProcessStatus
from entity_store_transformation_client.models.query_request import QueryRequest
from entity_store_transformation_client.models.query_filter_group import QueryFilterGroup
from entity_store_transformation_client.models.query_filter import QueryFilter


class UiPathClient:
    """Client for interacting with UiPath Cloud API and Entity Store"""

    def __init__(self,
                 tenant_name: Optional[str],
                 app_id: Optional[str],
                 api_key: Optional[str],
                 folder_id: Optional[str],
                 queue_name: Optional[str],
                 data_fabric_url: Optional[str],
                 data_fabric_key: Optional[str]):
        """
        Initialize the UiPath client with Entity Store integration

        Args:
            tenant_name: UiPath tenant identifier (e.g., "kapitolgroup")
            app_id: OAuth client ID for UiPath authentication
            api_key: OAuth client secret for UiPath authentication
            folder_id: Organization unit ID (UUID format)
            queue_name: Target queue name for extraction jobs
            data_fabric_url: Entity Store (Data Fabric) API base URL
            data_fabric_key: Entity Store API authentication key
        """
        self.tenant_name = tenant_name
        self.app_id = app_id
        self.api_key = api_key
        self.folder_id = folder_id
        self.queue_name = queue_name
        self.data_fabric_url = data_fabric_url
        self.data_fabric_key = data_fabric_key

        # Token expiration tracking
        self.token_expiry = None
        self.token_scopes = "DataFabric.Data.Read DataFabric.Data.Write DataFabric.Schema.Read"

        # Initialize Entity Store client
        self.entity_client = None
        if data_fabric_url and data_fabric_key:
            self._initialize_entity_client()

        # Check if running in mock mode
        self.mock_mode = not (
            tenant_name and app_id and api_key and folder_id and queue_name)

        if self.mock_mode:
            print(
                "Warning: UiPath credentials not fully configured. Running in mock mode.")

        if not data_fabric_url or not data_fabric_key:
            print(
                "Warning: Data Fabric credentials not configured. Entity Store integration disabled.")

    def _authenticate_uipath(self, scopes: str) -> str:
        """
        Authenticate with UiPath Cloud using OAuth 2.0 client credentials flow

        Returns:
            Bearer token for API requests

        Raises:
            Exception: If authentication fails
        """
        try:
            # UiPath Cloud OAuth token endpoint (no tenant in path for identity service)
            token_url = "https://cloud.uipath.com/identity_/connect/token"

            payload = {
                'client_id': self.app_id,
                'client_secret': self.api_key,
                'grant_type': 'client_credentials',
                'scope': scopes
            }

            print(
                f"Authenticating with UiPath Cloud (client_id: {self.app_id[:8]}...)")
            print(f"Token URL: {token_url}")
            print(f"Requested scopes: {scopes}")

            response = requests.post(
                token_url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                raise Exception("No access token in response")

            print("UiPath authentication successful")
            return access_token

        except requests.exceptions.HTTPError as e:
            # Log the response text to see the error details
            error_detail = ""
            if e.response is not None:
                try:
                    error_detail = f" - Response: {e.response.text}"
                except:
                    error_detail = " - Unable to read response text"
            raise Exception(
                f"UiPath authentication failed: {str(e)}{error_detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"UiPath authentication failed: {str(e)}")

    def _get_token_with_expiry(self, scopes: str) -> tuple[str, datetime]:
        """
        Authenticate with UiPath and return both token and expiry time

        Returns:
            Tuple of (access_token, expiry_datetime)

        Raises:
            Exception: If authentication fails
        """
        try:
            token_url = "https://cloud.uipath.com/identity_/connect/token"

            payload = {
                'client_id': self.app_id,
                'client_secret': self.api_key,
                'grant_type': 'client_credentials',
                'scope': scopes
            }

            print(
                f"Authenticating with UiPath Cloud for Entity Store (client_id: {self.app_id[:8]}...)")

            response = requests.post(
                token_url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get('access_token')
            # Default to 1 hour if not provided
            expires_in = token_data.get('expires_in', 3600)

            if not access_token:
                raise Exception("No access token in response")

            # Calculate expiry time with 5-minute buffer to refresh before actual expiry
            expiry_time = datetime.now() + timedelta(seconds=expires_in - 300)

            print(
                f"Entity Store authentication successful (expires at {expiry_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return access_token, expiry_time

        except requests.exceptions.HTTPError as e:
            error_detail = ""
            if e.response is not None:
                try:
                    error_detail = f" - Response: {e.response.text}"
                except:
                    error_detail = " - Unable to read response text"
            raise Exception(
                f"UiPath authentication failed: {str(e)}{error_detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"UiPath authentication failed: {str(e)}")

    def _initialize_entity_client(self) -> None:
        """
        Initialize or refresh the Entity Store client with a new token
        """
        try:
            access_token, expiry_time = self._get_token_with_expiry(
                self.token_scopes)

            self.entity_client = AuthenticatedClient(
                base_url=self.data_fabric_url,
                token=access_token
            )
            self.token_expiry = expiry_time

        except Exception as e:
            print(f"Failed to initialize Entity Store client: {str(e)}")
            raise

    def _ensure_valid_token(self) -> None:
        """
        Check if Entity Store token is still valid and refresh if needed
        Should be called before any Entity Store operation
        """
        if not self.entity_client:
            return

        # Check if token is expired or close to expiry
        if self.token_expiry is None or datetime.now() >= self.token_expiry:
            print("Entity Store token expired or missing, refreshing...")
            self._initialize_entity_client()
        else:
            # Calculate remaining time for logging
            remaining = self.token_expiry - datetime.now()
            print(
                f"Entity Store token valid (expires in {int(remaining.total_seconds() / 60)} minutes)")

    def _get_or_create_tender_project(self, tender_id: str) -> TenderProject:
        """
        Lookup or create a TenderProject in Entity Store

        Args:
            tender_id: Tender identifier (project name)

        Returns:
            TenderProject record with ID

        Raises:
            Exception: If query or creation fails
        """
        # Ensure token is valid before proceeding
        self._ensure_valid_token()

        try:
            print(f"Looking up TenderProject with Name='{tender_id}'")

            # Build query to find existing project by name
            query_req = QueryRequest(
                filter_group=QueryFilterGroup(
                    query_filters=[
                        QueryFilter(
                            field_name="Name",
                            operator="=",
                            value=tender_id
                        )
                    ]
                ),
                limit=1
            )

            # Execute query
            response = query_tender_project.sync(
                client=self.entity_client,
                body=query_req
            )

            # Check if project exists (use 'value' attribute, not 'records')
            if response and response.value and len(response.value) > 0:
                project = response.value[0]
                print(f"Found existing TenderProject: ID={project.id}")
                return project

            # Project not found, create new one
            print(
                f"TenderProject not found. Creating new project: Name='{tender_id}'")

            new_project = TenderProject(name=tender_id)
            create_response = add_tender_project.sync_detailed(
                client=self.entity_client,
                body=new_project
            )

            # Check response status
            if create_response.status_code != 200:
                error_msg = f"Failed to create TenderProject. Status: {create_response.status_code}"
                if create_response.content:
                    try:
                        error_msg += f", Response: {create_response.content.decode('utf-8')}"
                    except:
                        error_msg += f", Response bytes: {create_response.content[:200]}"
                raise Exception(error_msg)

            created_project = create_response.parsed
            if not created_project:
                raise Exception(
                    "TenderProject creation returned None despite 200 status")

            print(f"Created TenderProject: ID={created_project.id}")
            return created_project

        except Exception as e:
            raise Exception(f"Failed to get/create TenderProject: {str(e)}")

    def _get_validation_user(self, user_email: str) -> TitleBlockValidationUsers:
        """
        Lookup validation user in Entity Store

        Args:
            user_email: User email address

        Returns:
            TitleBlockValidationUsers record

        Raises:
            ValueError: If user not found (fail-fast requirement)
            Exception: If query fails
        """
        # Ensure token is valid before proceeding
        self._ensure_valid_token()

        try:
            print(
                f"Looking up TitleBlockValidationUsers with UserEmail='{user_email}'")

            # Build query to find user by email
            query_req = QueryRequest(
                filter_group=QueryFilterGroup(
                    query_filters=[
                        QueryFilter(
                            field_name="UserEmail",
                            operator="=",
                            value=user_email
                        )
                    ]
                ),
                limit=1
            )

            # Execute query
            response = query_title_block_validation_users.sync(
                client=self.entity_client,
                body=query_req
            )

            # Check if user exists (use 'value' attribute, not 'records')
            if response and response.value and len(response.value) > 0:
                user = response.value[0]
                print(
                    f"Found TitleBlockValidationUsers: ID={user.id}, Email={user.user_email}")
                return user

            # User not found - fail immediately
            raise ValueError(
                f"User '{user_email}' is not registered in TitleBlockValidationUsers")

        except ValueError:
            # Re-raise ValueError as-is (user not found)
            raise
        except Exception as e:
            raise Exception(f"Failed to lookup validation user: {str(e)}")

    def _generate_cuid(self) -> str:
        """
        Generate a collision-resistant unique identifier (CUID)

        Returns:
            CUID string that links TenderSubmission to UiPath queue items
        """
        return Cuid().generate()

    def _create_tender_submission(self,
                                  project: TenderProject,
                                  reference: str,
                                  user: TitleBlockValidationUsers,
                                  sharepoint_path: Optional[str] = None,
                                  output_location: Optional[str] = None,
                                  folder_list: Optional[List[str]] = None) -> TenderSubmission:
        """
        Create a TenderSubmission record in Entity Store

        Args:
            project: TenderProject to link to
            reference: CUID reference for tracking
            user: User who submitted and will validate
            sharepoint_path: SharePoint folder path for input documents
            output_location: SharePoint folder path for output location

        Returns:
            Created TenderSubmission with ID

        Raises:
            Exception: If creation fails
        """
        # Ensure token is valid before proceeding
        self._ensure_valid_token()

        try:
            print(
                f"Creating TenderSubmission: Reference={reference}, ProjectID={project.id}")

            # Convert folder_list to semicolon-delimited string
            folder_list_str = None
            if folder_list:
                folder_list_str = ';'.join(folder_list)
                print(f"Folder list: {folder_list_str}")

            submission = TenderSubmission(
                project_id=project,
                reference=reference,
                submitted_by=user,
                validated_by=user,  # Same user for now
                archive_name="n/a",
                is_addendum=False,
                sharepoint_path=sharepoint_path,
                output_location=output_location,
                folder_list=folder_list_str
            )

            # Make direct HTTP request to avoid parsing issues with expansion_level=0
            from entity_store_transformation_client.api.tender_submission.add_tender_submission import _get_kwargs
            import json

            kwargs = _get_kwargs(body=submission, expansion_level=0)
            response = self.entity_client.get_httpx_client().request(**kwargs)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to create TenderSubmission. Status: {response.status_code}, Response: {response.text}")

            # Parse response manually to extract just the ID
            response_json = response.json()
            submission_id = UUID(response_json.get('Id'))

            # Create a minimal TenderSubmission object with just the ID for return
            created_submission = TenderSubmission(
                id=submission_id,
                project_id=project,
                reference=reference,
                submitted_by=user,
                validated_by=user,
                archive_name="n/a",
                is_addendum=False,
                sharepoint_path=sharepoint_path,
                output_location=output_location
            )

            print(f"Created TenderSubmission: ID={created_submission.id}")
            return created_submission

        except Exception as e:
            raise Exception(f"Failed to create TenderSubmission: {str(e)}")

    def _create_tender_file(self,
                            submission: TenderSubmission,
                            file_path: str) -> TenderFile:
        """
        Create a TenderFile record in Entity Store

        Args:
            submission: TenderSubmission to link to
            file_path: Full blob storage path (e.g., "tender-id/category/filename.pdf")

        Returns:
            Created TenderFile with ID

        Raises:
            Exception: If creation fails
        """
        # Ensure token is valid before proceeding
        self._ensure_valid_token()

        try:
            # Extract filename from path
            filename = file_path.split('/')[-1]

            print(
                f"Creating TenderFile: SubmissionID={submission.id}, Path={file_path}")

            tender_file = TenderFile(
                submission_id=submission,
                original_path=file_path,
                original_filename=filename,
                status=TenderProcessStatus.QUEUED
            )

            # Make direct HTTP request to avoid parsing issues with expansion_level=0
            from entity_store_transformation_client.api.tender_file.add_tender_file import _get_kwargs
            import json

            kwargs = _get_kwargs(body=tender_file, expansion_level=0)
            response = self.entity_client.get_httpx_client().request(**kwargs)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to create TenderFile. Status: {response.status_code}, Response: {response.text}")

            # Parse response manually to extract just the ID
            response_json = response.json()
            file_id = UUID(response_json.get('Id'))

            # Create a minimal TenderFile object with just the ID for return
            created_file = TenderFile(
                id=file_id,
                submission_id=submission,
                original_path=file_path,
                original_filename=filename,
                status=TenderProcessStatus.QUEUED
            )

            print(
                f"Created TenderFile: ID={created_file.id}, Filename={filename}")
            return created_file

        except Exception as e:
            raise Exception(
                f"Failed to create TenderFile for {file_path}: {str(e)}")

    def _delete_tender_files(self, file_ids: List[UUID]) -> None:
        """
        Delete TenderFile records (rollback on queue submission failure)

        Args:
            file_ids: List of TenderFile IDs to delete

        Note:
            Errors are logged but not raised (this is cleanup/rollback)
        """
        if not file_ids:
            return

        # Ensure token is valid before proceeding
        try:
            self._ensure_valid_token()
        except Exception as e:
            print(
                f"Token refresh failed during rollback (non-fatal): {str(e)}")
            return

        try:
            print(f"Rolling back: Deleting {len(file_ids)} TenderFile records")

            response = batch_delete_tender_file.sync_detailed(
                client=self.entity_client,
                body=file_ids,
                fail_on_first=False
            )

            if response.status_code == 200:
                print(
                    f"Successfully deleted {len(file_ids)} TenderFile records")
            else:
                print(
                    f"TenderFile deletion returned status {response.status_code}")

            print(f"Successfully deleted {len(file_ids)} TenderFile records")

        except Exception as e:
            # Log but don't raise - this is cleanup, don't mask original error
            print(f"Error during TenderFile rollback (non-fatal): {str(e)}")

    def _build_queue_item(self,
                          file_path: str,
                          tender_id: str,
                          submitted_by: str,
                          reference: str,
                          document_count: int,
                          discipline: str,
                          title_block_coords: Optional[Dict] = None,
                          sharepoint_folder_path: Optional[str] = None,
                          output_folder_path: Optional[str] = None) -> Dict:
        """
        Build a UiPath queue item object

        Args:
            file_path: Blob storage path
            tender_id: Tender/project identifier
            submitted_by: User email
            reference: CUID linking to TenderSubmission
            document_count: Total files in this submission
            discipline: Drawing discipline (e.g., 'Architectural', 'Structural')
            title_block_coords: Optional title block coordinates {x, y, width, height} in pixels
            sharepoint_folder_path: SharePoint folder path for input documents
            output_folder_path: SharePoint folder path for output location

        Returns:
            Queue item dictionary for bulk add API
        """
        # Convert title block coords to comma-separated string
        # Format: "x,y,width,height"
        if title_block_coords:
            coords_str = f"{title_block_coords.get('x', 0)},{title_block_coords.get('y', 0)},{title_block_coords.get('width', 0)},{title_block_coords.get('height', 0)}"
        else:
            coords_str = "0,0,0,0"  # Default values if not provided

        queue_item = {
            "Name": self.queue_name,
            "Priority": "High",
            "Reference": reference,
            "SpecificContent": {
                "ProjectName": tender_id,
                "ValidationUser": submitted_by,
                "FilePath": file_path,
                "Reference": reference,
                "DocumentCount": document_count,
                "RequestDate": datetime.now().strftime("%Y-%m-%d"),
                "IsAddendum": False,
                "Discipline": discipline,
                "TitleBlockCoords": coords_str,  # String instead of object
                "SharePointFolderPath": sharepoint_folder_path or "",
                "OutputFolderPath": output_folder_path or ""
            }
        }

        print(
            f"Built queue item: File={file_path}, Discipline={discipline}, Ref={reference}, Coords={coords_str}")
        return queue_item

    def _bulk_add_queue_items(self, queue_items: List[Dict]) -> Dict:
        """
        Submit queue items to UiPath using bulk add endpoint

        Args:
            queue_items: List of queue item dictionaries

        Returns:
            UiPath API response

        Raises:
            Exception: If submission fails
        """
        try:
            # Authenticate
            access_token = self._authenticate_uipath("OR.Queues")

            # Build request URL
            url = (f"https://cloud.uipath.com/kapitolgroup/{self.tenant_name}/"
                   f"orchestrator_/odata/Queues/UiPathODataSvc.BulkAddQueueItems")

            # Build headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-UIPATH-OrganizationUnitId": self.folder_id
            }

            # Build payload
            payload = {
                "queueName": self.queue_name,
                "commitType": "AllOrNothing",
                "queueItems": queue_items
            }

            print(
                f"Submitting {len(queue_items)} queue items to UiPath (queue: {self.queue_name})")

            # Submit request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            # Check status code first
            if response.status_code != 200:
                raise Exception(
                    f"UiPath API returned status {response.status_code}: {response.text}")

            # Check if response has content before trying to parse JSON
            if not response.content or response.text.strip() == "":
                print(
                    f"UiPath queue submission successful (empty response, status {response.status_code})")
                return {"success": True, "count": len(queue_items)}

            # Try to parse JSON, but handle empty/non-JSON responses
            try:
                result = response.json()
                print(
                    f"Successfully submitted {len(queue_items)} items to UiPath queue")
                return result
            except requests.exceptions.JSONDecodeError:
                # Response was successful but not JSON (treat as success)
                print(
                    f"UiPath queue submission successful (non-JSON response, status {response.status_code})")
                return {"success": True, "count": len(queue_items)}

        except requests.exceptions.JSONDecodeError as e:
            # JSON decode error - but request was successful
            print(f"UiPath queue submission successful (couldn't parse response)")
            return {"success": True, "count": len(queue_items)}

        except requests.exceptions.RequestException as e:
            raise Exception(
                f"Failed to submit queue items to UiPath: {str(e)}")

    def submit_extraction_job(self,
                              tender_id: str,
                              file_paths: List[str],
                              discipline: str,
                              title_block_coords: Dict,
                              submitted_by: str = 'Unknown',
                              batch_id: Optional[str] = None,
                              sharepoint_folder_path: Optional[str] = None,
                              output_folder_path: Optional[str] = None,
                              folder_list: Optional[List[str]] = None) -> Dict:
        """
        Submit a drawing metadata extraction job via Entity Store and UiPath queue

        Args:
            tender_id: Tender identifier
            file_paths: List of blob storage file paths to process
            discipline: Drawing discipline (for logging, not used in queue items)
            title_block_coords: Title block coordinates (for logging, not used in queue items)
            submitted_by: User email who submitted the job
            batch_id: Optional batch identifier for backward compatibility
            sharepoint_folder_path: SharePoint folder path for input documents
            output_folder_path: SharePoint folder path for output location
            folder_list: List of available destination folder names (stored as semicolon-delimited string)

        Returns:
            Job information dictionary with submission details

        Raises:
            ValueError: If user not registered in TitleBlockValidationUsers
            Exception: If any step fails
        """
        # Mock mode - return mock response without Entity Store or UiPath
        if self.mock_mode or not self.entity_client:
            mock_reference = f"mock-{Cuid().generate()}"
            return {
                'reference': mock_reference,
                'submission_id': 'mock-submission-id',
                'project_id': 'mock-project-id',
                'status': 'Queued',
                'tender_id': tender_id,
                'file_count': len(file_paths),
                'submitted_at': datetime.utcnow().isoformat(),
                'submitted_by': submitted_by,
                'batch_id': batch_id,
                'message': 'Mock submission created (UiPath/Entity Store not configured)'
            }

        created_files = []  # Track created files for rollback

        try:
            # Step 1: Get or create TenderProject
            project = self._get_or_create_tender_project(tender_id)

            # Step 2: Validate user exists (fail-fast)
            user = self._get_validation_user(submitted_by)

            # Step 3: Generate CUID reference
            reference = self._generate_cuid()
            print(f"Generated CUID reference: {reference}")

            # Step 4: Create TenderSubmission
            submission = self._create_tender_submission(
                project, reference, user, sharepoint_folder_path, output_folder_path, folder_list)

            # Step 5: Create TenderFile records and build queue items
            queue_items = []
            document_count = len(file_paths)

            for file_path in file_paths:
                # Create TenderFile record
                tender_file = self._create_tender_file(submission, file_path)
                created_files.append(tender_file)

                # Build queue item
                queue_item = self._build_queue_item(
                    file_path=file_path,
                    tender_id=tender_id,
                    submitted_by=submitted_by,
                    reference=reference,
                    document_count=document_count,
                    discipline=discipline,
                    title_block_coords=title_block_coords,
                    sharepoint_folder_path=sharepoint_folder_path,
                    output_folder_path=output_folder_path
                )
                queue_items.append(queue_item)

            # Step 6: Submit to UiPath queue (with rollback on failure)
            try:
                uipath_response = self._bulk_add_queue_items(queue_items)

                # Success - return submission details
                return {
                    'reference': reference,
                    'submission_id': str(submission.id),
                    'project_id': str(project.id),
                    'status': 'Queued',
                    'tender_id': tender_id,
                    'file_count': len(file_paths),
                    'submitted_at': datetime.utcnow().isoformat(),
                    'submitted_by': submitted_by,
                    'batch_id': batch_id,
                    'uipath_response': uipath_response
                }

            except Exception as queue_error:
                # Rollback: Delete created TenderFile records
                file_ids = [f.id for f in created_files]
                self._delete_tender_files(file_ids)

                # Re-raise original error
                raise queue_error

        except ValueError as e:
            # User not found - re-raise as-is for 400 response
            raise
        except Exception as e:
            # Other errors - wrap with context
            raise Exception(f"Failed to submit extraction job: {str(e)}")
