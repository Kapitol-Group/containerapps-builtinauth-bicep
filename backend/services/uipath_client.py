"""
UiPath REST API client for drawing metadata extraction
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime


class UiPathClient:
    """Client for interacting with UiPath REST API"""

    def __init__(self, base_url: Optional[str], api_key: Optional[str]):
        """
        Initialize the UiPath client

        Args:
            base_url: UiPath API base URL
            api_key: UiPath API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key

        if not base_url or not api_key:
            print(
                "Warning: UIPATH_API_URL or UIPATH_API_KEY not set. UiPath integration will not work.")

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def submit_extraction_job(self, tender_id: str, file_paths: List[str],
                              discipline: str, title_block_coords: Dict,
                              submitted_by: str = 'Unknown') -> Dict:
        """
        Submit a drawing metadata extraction job to UiPath

        Args:
            tender_id: Tender identifier
            file_paths: List of file paths to process
            discipline: Drawing discipline (e.g., 'Architectural', 'Structural')
            title_block_coords: Title block coordinates {x, y, width, height} in pixels
            submitted_by: User who submitted the job

        Returns:
            Job information dictionary
        """
        if not self.base_url or not self.api_key:
            # Mock response for development
            return {
                'job_id': f'mock-job-{datetime.utcnow().timestamp()}',
                'status': 'Pending',
                'tender_id': tender_id,
                'file_count': len(file_paths),
                'submitted_at': datetime.utcnow().isoformat(),
                'submitted_by': submitted_by,
                'message': 'Mock job created (UiPath not configured)'
            }

        payload = {
            'tender_id': tender_id,
            'files': file_paths,
            'discipline': discipline,
            'title_block_region': title_block_coords,
            'submitted_by': submitted_by,
            'submitted_at': datetime.utcnow().isoformat()
        }

        try:
            response = requests.post(
                f'{self.base_url}/jobs',
                json=payload,
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to submit UiPath job: {str(e)}")

    def get_job_status(self, job_id: str) -> Dict:
        """
        Get the status of a UiPath job

        Args:
            job_id: Job identifier

        Returns:
            Job status information
        """
        if not self.base_url or not self.api_key:
            # Mock response for development
            return {
                'job_id': job_id,
                'status': 'Running',
                'progress': 0.5,
                'message': 'Mock job status (UiPath not configured)'
            }

        try:
            response = requests.get(
                f'{self.base_url}/jobs/{job_id}',
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get UiPath job status: {str(e)}")

    def cancel_job(self, job_id: str) -> Dict:
        """
        Cancel a running UiPath job

        Args:
            job_id: Job identifier

        Returns:
            Cancellation confirmation
        """
        if not self.base_url or not self.api_key:
            return {
                'job_id': job_id,
                'status': 'Cancelled',
                'message': 'Mock job cancelled (UiPath not configured)'
            }

        try:
            response = requests.post(
                f'{self.base_url}/jobs/{job_id}/cancel',
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to cancel UiPath job: {str(e)}")
