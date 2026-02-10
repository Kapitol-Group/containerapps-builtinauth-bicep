import base64
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.datastructures import FileStorage
import requests

from services.blob_storage import BlobStorageService
from services.uipath_client import UiPathClient
from utils.auth import extract_user_info, require_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose Azure SDK logging
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)


# Create a flask app
# Serve React build from frontend_build directory, fallback to templates/static for legacy routes
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='frontend_build',
    static_url_path=''
)

# CORS not needed since frontend and backend are on same origin
# CORS(app, origins=[os.getenv('FRONTEND_URL', '*')])

# Initialize services
blob_service = BlobStorageService(
    account_name=os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
    container_name=os.getenv(
        'AZURE_STORAGE_CONTAINER_NAME', 'tender-documents')
)

uipath_client = UiPathClient(
    tenant_name=os.getenv('UIPATH_TENANT_NAME'),
    app_id=os.getenv('UIPATH_APP_ID'),
    api_key=os.getenv('UIPATH_API_KEY'),
    folder_id=os.getenv('UIPATH_FOLDER_ID'),
    queue_name=os.getenv('UIPATH_QUEUE_NAME'),
    data_fabric_url=os.getenv('DATA_FABRIC_API_URL'),
    data_fabric_key=os.getenv('DATA_FABRIC_API_KEY')
)

# SharePoint import job tracking (in-memory)
sharepoint_import_jobs = {}
import_jobs_lock = threading.Lock()

# Auto-cleanup completed jobs after 1 hour
JOB_CLEANUP_SECONDS = 3600

# Log startup info
logger.info("=" * 60)
logger.info("Construction Tender Automation Backend Starting")
logger.info(
    f"Storage Account: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'NOT SET')}")
logger.info(
    f"Container Name: {os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'tender-documents')}")
logger.info(f"UiPath Mock Mode: {os.getenv('UIPATH_MOCK_MODE', 'true')}")
logger.info("=" * 60)

# ========== Web Routes (existing functionality) ==========


@app.get('/')
def index():
    # Serve React app index.html
    return app.send_static_file('index.html')

# Extract the username for display from the base64 encoded header
# X-MS-CLIENT-PRINCIPAL from the 'name' claim.
#
# Fallback to `default_username` if the header is not present.


def extract_username(headers, default_username="You"):
    if "X-MS-CLIENT-PRINCIPAL" not in headers:
        return default_username

    token = json.loads(base64.b64decode(headers.get("X-MS-CLIENT-PRINCIPAL")))
    claims = {claim["typ"]: claim["val"] for claim in token["claims"]}
    return claims.get("name", default_username)


@app.get('/hello')
def hello():
    return render_template('hello.html', name=extract_username(request.headers))

# ========== API Routes ==========

# Tenders API


@app.get('/api/tenders')
@require_auth
def list_tenders():
    """List all tenders"""
    try:
        logger.debug("Listing all tenders")
        tenders = blob_service.list_tenders()
        logger.debug(f"Found {len(tenders)} tenders")
        return jsonify({
            'success': True,
            'data': tenders
        })
    except Exception as e:
        logger.error(f"Failed to list tenders: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders')
@require_auth
def create_tender():
    """Create a new tender"""
    try:
        data = request.json
        tender_name = data.get('name')

        # Legacy fields (kept for backward compatibility)
        sharepoint_path = data.get('sharepoint_path')
        output_location = data.get('output_location')

        # New SharePoint identifier fields
        sharepoint_site_id = data.get('sharepoint_site_id')
        sharepoint_library_id = data.get('sharepoint_library_id')
        sharepoint_folder_path = data.get('sharepoint_folder_path')

        # Output location identifier fields
        output_site_id = data.get('output_site_id')
        output_library_id = data.get('output_library_id')
        output_folder_path = data.get('output_folder_path')

        if not tender_name:
            return jsonify({
                'success': False,
                'error': 'Tender name is required'
            }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Creating tender: {tender_name} by {user_info.get('name', 'Unknown')}")

        # Build metadata with all SharePoint identifiers
        metadata = {
            'created_at': datetime.utcnow().isoformat()
        }

        # Add legacy fields if provided
        if sharepoint_path:
            metadata['sharepoint_path'] = sharepoint_path
        if output_location:
            metadata['output_location'] = output_location

        # Add new SharePoint identifier fields if provided
        if sharepoint_site_id:
            metadata['sharepoint_site_id'] = sharepoint_site_id
        if sharepoint_library_id:
            metadata['sharepoint_library_id'] = sharepoint_library_id
        if sharepoint_folder_path:
            metadata['sharepoint_folder_path'] = sharepoint_folder_path

        # Add output location identifier fields if provided
        if output_site_id:
            metadata['output_site_id'] = output_site_id
        if output_library_id:
            metadata['output_library_id'] = output_library_id
        if output_folder_path:
            metadata['output_folder_path'] = output_folder_path

        tender = blob_service.create_tender(
            tender_name=tender_name,
            created_by=user_info.get('name', 'Unknown'),
            metadata=metadata
        )

        logger.info(f"Successfully created tender: {tender['id']}")
        return jsonify({
            'success': True,
            'data': tender
        }), 201
    except Exception as e:
        logger.error(f"Failed to create tender: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# UiPath API


def _process_uipath_submission_async(
    tender_id: str,
    tender_name: str,
    batch_id: str,
    file_paths: list,
    category: str,
    title_block_coords: dict,
    user_email: str,
    sharepoint_folder_path: str,
    output_folder_path: str,
    folder_list: list = None
):
    """
    Background worker to submit extraction job to UiPath.
    Runs in separate thread to avoid blocking the HTTP response.
    Updates batch metadata with success/failure details.
    """
    try:
        logger.info(
            f"[Background] Starting UiPath submission for batch {batch_id}")

        # Get current batch to track attempts
        batch = blob_service.get_batch(tender_id, batch_id)
        attempts = batch.get('submission_attempts', []) if batch else []

        # Record attempt start
        attempts.append({
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'in_progress'
        })

        blob_service.update_batch(tender_id, batch_id, {
            'submission_attempts': attempts
        })

        job = uipath_client.submit_extraction_job(
            tender_id=tender_name,
            file_paths=file_paths,
            discipline=category,
            title_block_coords=title_block_coords,
            submitted_by=user_email,
            batch_id=batch_id,
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list
        )

        logger.info(
            f"[Background] Successfully submitted batch {batch_id} to UiPath with reference {job.get('reference')}"
        )

        # Update batch with success details
        attempts[-1]['status'] = 'success'
        attempts[-1]['reference'] = job.get('reference')

        blob_service.update_batch(tender_id, batch_id, {
            'status': 'running',
            'uipath_reference': job.get('reference', ''),
            'uipath_submission_id': job.get('submission_id', ''),
            'uipath_project_id': job.get('project_id', ''),
            'submission_attempts': attempts,
            'last_error': ''
        })

    except ValueError as user_error:
        # User validation failed - update batch with error
        logger.error(
            f"[Background] User validation failed for batch {batch_id}: {str(user_error)}")

        try:
            batch = blob_service.get_batch(tender_id, batch_id)
            attempts = batch.get('submission_attempts', []) if batch else []
            if attempts:
                attempts[-1]['status'] = 'failed'
                attempts[-1]['error'] = str(user_error)

            blob_service.update_batch(tender_id, batch_id, {
                'status': 'failed',
                'submission_attempts': attempts,
                'last_error': f'User validation failed: {str(user_error)}'
            })
        except Exception as update_error:
            logger.error(
                f"[Background] Failed to update batch status: {update_error}")

    except Exception as e:
        # UiPath submission failed - update batch with error
        logger.error(
            f"[Background] UiPath submission failed for batch {batch_id}: {str(e)}", exc_info=True)

        try:
            batch = blob_service.get_batch(tender_id, batch_id)
            attempts = batch.get('submission_attempts', []) if batch else []
            if attempts:
                attempts[-1]['status'] = 'failed'
                attempts[-1]['error'] = str(e)

            blob_service.update_batch(tender_id, batch_id, {
                'status': 'failed',
                'submission_attempts': attempts,
                'last_error': str(e)
            })
        except Exception as update_error:
            logger.error(
                f"[Background] Failed to update batch status: {update_error}")


def retry_stuck_batches():
    """
    Background worker that periodically retries batches stuck in 'pending' status.
    Runs every 5 minutes to find and retry batches that failed to submit to UiPath.
    """
    logger.info("[Retry Worker] Starting stuck batch retry worker")

    while True:
        try:
            # Sleep first to allow app startup to complete
            time.sleep(300)  # 5 minutes

            logger.info("[Retry Worker] Checking for stuck batches...")

            # Find all tenders
            tenders = blob_service.list_tenders()
            stuck_count = 0
            retry_count = 0

            for tender in tenders:
                tender_id = tender['id']

                try:
                    batches = blob_service.list_batches(tender_id)

                    for batch in batches:
                        # Find batches stuck in pending for > 5 minutes
                        if batch.get('status') == 'pending':
                            try:
                                submitted_at = datetime.fromisoformat(
                                    batch['submitted_at'])
                                age = datetime.utcnow() - submitted_at

                                if age > timedelta(minutes=5):
                                    stuck_count += 1
                                    logger.warning(
                                        f"[Retry Worker] Found stuck batch {batch['batch_id']} in tender {tender_id} "
                                        f"(age: {int(age.total_seconds()//60)} min)"
                                    )

                                    # Check retry attempts to prevent infinite retries
                                    submission_attempts = batch.get(
                                        'submission_attempts', [])
                                    failed_attempts = [
                                        a for a in submission_attempts if a.get('status') == 'failed']

                                    # Old batches (>24 hours) without submission tracking should be marked as failed
                                    if age > timedelta(hours=24) and len(submission_attempts) == 0:
                                        logger.warning(
                                            f"[Retry Worker] Batch {batch['batch_id']} is very old ({int(age.total_seconds()//3600)} hours) "
                                            f"with no tracked attempts. Marking as failed (legacy batch)."
                                        )
                                        try:
                                            blob_service.update_batch(tender_id, batch['batch_id'], {
                                                'status': 'failed',
                                                'last_error': f'Legacy batch older than 24 hours with no submission tracking. Original submission failed.'
                                            })
                                        except Exception as update_error:
                                            logger.error(
                                                f"[Retry Worker] Failed to update batch status: {update_error}")
                                        continue

                                    # Check TOTAL attempts (not just failed) to catch infinite loops
                                    # If we have >5 total attempts, something is wrong (normal is 1 success or <=3 failures)
                                    if len(submission_attempts) > 5:
                                        logger.error(
                                            f"[Retry Worker] Batch {batch['batch_id']} has {len(submission_attempts)} attempts. "
                                            f"This indicates an infinite retry loop. Marking as failed."
                                        )
                                        try:
                                            # Use simple update to avoid metadata size issues
                                            blob_service.update_batch(tender_id, batch['batch_id'], {
                                                'status': 'failed',
                                                'last_error': f'Too many submission attempts ({len(submission_attempts)}). Likely infinite retry loop or metadata size limit exceeded.'
                                            })
                                        except Exception as update_error:
                                            logger.error(
                                                f"[Retry Worker] Failed to mark looping batch as failed: {update_error}")
                                            # If we can't even update the status, try to delete the batch to stop the loop
                                            try:
                                                logger.warning(
                                                    f"[Retry Worker] Attempting to delete stuck batch {batch['batch_id']}")
                                                blob_service.delete_batch(
                                                    tender_id, batch['batch_id'])
                                            except Exception as delete_error:
                                                logger.critical(
                                                    f"[Retry Worker] CRITICAL: Cannot update or delete looping batch {batch['batch_id']}. "
                                                    f"Manual intervention required. Error: {delete_error}"
                                                )
                                        continue

                                    if len(failed_attempts) >= 3:
                                        logger.warning(
                                            f"[Retry Worker] Batch {batch['batch_id']} has reached max retry limit (3 failed attempts). "
                                            f"Marking as permanently failed."
                                        )
                                        try:
                                            blob_service.update_batch(tender_id, batch['batch_id'], {
                                                'status': 'failed',
                                                'last_error': f'Maximum retry limit reached after {len(failed_attempts)} failed attempts'
                                            })
                                        except Exception as update_error:
                                            logger.error(
                                                f"[Retry Worker] Failed to update batch status: {update_error}")
                                        continue

                                    # Retry UiPath submission
                                    try:
                                        # Extract necessary fields from batch metadata
                                        category = batch.get('discipline') or batch.get(
                                            'destination', 'Unknown')
                                        # submitted_by should be email address (stored during batch creation)
                                        submitted_by = batch.get(
                                            'submitted_by', 'System')

                                        job = uipath_client.submit_extraction_job(
                                            tender_id=tender_id,
                                            file_paths=batch['file_paths'],
                                            discipline=category,
                                            title_block_coords=batch['title_block_coords'],
                                            submitted_by=submitted_by,
                                            batch_id=batch['batch_id'],
                                            sharepoint_folder_path=None,  # Not stored in batch metadata
                                            output_folder_path=None
                                        )

                                        # Update status to running on success
                                        try:
                                            blob_service.update_batch_status(
                                                tender_id, batch['batch_id'], 'running')
                                            retry_count += 1

                                            logger.info(
                                                f"[Retry Worker] Successfully retried batch {batch['batch_id']} "
                                                f"with reference {job.get('reference')}"
                                            )
                                        except Exception as status_error:
                                            # CRITICAL: Submission succeeded but status update failed
                                            # This causes infinite retry loops - mark as failed to stop the loop
                                            error_msg = str(status_error)
                                            logger.error(
                                                f"[Retry Worker] UiPath submission succeeded for batch {batch['batch_id']} "
                                                f"but status update failed: {error_msg}. Marking as failed to prevent loop."
                                            )
                                            try:
                                                # Try simple status update without adding to submission_attempts
                                                blob_service.update_batch(tender_id, batch['batch_id'], {
                                                    'status': 'failed',
                                                    'last_error': f'Submitted to UiPath but metadata update failed (likely size limit): {error_msg}. Check UiPath for results.'
                                                })
                                            except Exception as final_error:
                                                logger.critical(
                                                    f"[Retry Worker] CRITICAL: Batch {batch['batch_id']} submitted to UiPath "
                                                    f"but cannot update status. Manual cleanup required. Error: {final_error}"
                                                )

                                    except Exception as retry_error:
                                        logger.error(
                                            f"[Retry Worker] Retry failed for batch {batch['batch_id']}: {str(retry_error)}"
                                        )
                                        # Leave in pending, will retry again in next cycle (up to max limit)

                            except (ValueError, KeyError) as parse_error:
                                logger.error(
                                    f"[Retry Worker] Error parsing batch {batch.get('batch_id')}: {parse_error}"
                                )

                except Exception as tender_error:
                    logger.error(
                        f"[Retry Worker] Error processing tender {tender_id}: {tender_error}"
                    )

            if stuck_count > 0:
                logger.info(
                    f"[Retry Worker] Retry cycle complete: Found {stuck_count} stuck batches, "
                    f"successfully retried {retry_count}"
                )
            else:
                logger.debug("[Retry Worker] No stuck batches found")

        except Exception as e:
            logger.error(
                f"[Retry Worker] Error in retry loop: {str(e)}", exc_info=True)


# Start retry worker thread
retry_thread = threading.Thread(target=retry_stuck_batches, daemon=True)
retry_thread.start()
logger.info("Started retry worker thread")


@app.get('/api/tenders/<tender_id>')
@require_auth
def get_tender(tender_id: str):
    """Get tender details"""
    try:
        tender = blob_service.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        return jsonify({
            'success': True,
            'data': tender
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>')
@require_auth
def delete_tender(tender_id: str):
    """Delete a tender"""
    try:
        logger.info(f"Attempting to delete tender: {tender_id}")
        blob_service.delete_tender(tender_id)
        logger.info(f"Successfully deleted tender: {tender_id}")
        return jsonify({
            'success': True,
            'message': 'Tender deleted successfully'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Files API


@app.get('/api/tenders/<tender_id>/files')
@require_auth
def list_files(tender_id: str):
    """List files in a tender"""
    try:
        # Get exclude_batched query parameter (default: False)
        exclude_batched = request.args.get(
            'exclude_batched', 'false').lower() == 'true'

        files = blob_service.list_files(
            tender_id, exclude_batched=exclude_batched)
        return jsonify({
            'success': True,
            'data': files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders/<tender_id>/files')
@require_auth
def upload_file(tender_id: str):
    """Upload a file to a tender"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        category = request.form.get('category', 'uncategorized')
        source = request.form.get('source', 'local')  # 'local' or 'sharepoint'

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Uploading file {file.filename} to tender {tender_id}, category: {category}, source: {source}")

        file_info = blob_service.upload_file(
            tender_id=tender_id,
            file=file,
            category=category,
            uploaded_by=user_info.get('name', 'Unknown'),
            source=source
        )

        logger.info(
            f"Successfully uploaded file {file.filename} to tender {tender_id}")
        return jsonify({
            'success': True,
            'data': file_info
        }), 201
    except Exception as e:
        logger.error(
            f"Failed to upload file to tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/files/<path:file_path>')
@require_auth
def download_file(tender_id: str, file_path: str):
    """Download a file from a tender"""
    try:
        file_data = blob_service.download_file(tender_id, file_path)

        return app.response_class(
            file_data['content'],
            mimetype=file_data['content_type'],
            headers={
                'Content-Disposition': f'attachment; filename="{file_data["filename"]}"'
            }
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.put('/api/tenders/<tender_id>/files/<path:file_path>/category')
@require_auth
def update_file_category(tender_id: str, file_path: str):
    """Update file category"""
    try:
        data = request.json
        category = data.get('category')

        if not category:
            return jsonify({
                'success': False,
                'error': 'Category is required'
            }), 400

        blob_service.update_file_metadata(
            tender_id=tender_id,
            file_path=file_path,
            metadata={'category': category}
        )

        return jsonify({
            'success': True,
            'message': 'File category updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>/files/<path:file_path>')
@require_auth
def delete_file(tender_id: str, file_path: str):
    """Delete a file from a tender"""
    try:
        logger.info(f"Deleting file {file_path} from tender {tender_id}")
        blob_service.delete_file(tender_id, file_path)
        logger.info(
            f"Successfully deleted file {file_path} from tender {tender_id}")
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete file {file_path} from tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Batches API


@app.post('/api/tenders/<tender_id>/batches')
@require_auth
def create_batch(tender_id: str):
    """Create a new extraction batch"""
    try:
        data = request.json
        batch_name = data.get('batch_name')
        discipline = data.get('discipline')
        file_paths = data.get('file_paths', [])
        title_block_coords = data.get('title_block_coords')

        if not all([batch_name, discipline, file_paths, title_block_coords]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: batch_name, discipline, file_paths, title_block_coords'
            }), 400

        # Validate files exist
        all_files = blob_service.list_files(tender_id)
        existing_paths = {f['path'] for f in all_files}
        for file_path in file_paths:
            if file_path not in existing_paths:
                return jsonify({
                    'success': False,
                    'error': f'File not found: {file_path}'
                }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Creating batch '{batch_name}' for tender {tender_id} with {len(file_paths)} files")

        # Create batch (use email for UiPath user lookup, fallback to name if no email)
        batch = blob_service.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=discipline,
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get(
                'email') or user_info.get('name', 'Unknown'),
            job_id=None  # Will be set when UiPath job is submitted
        )

        # Update file categories and batch references
        updated_count = blob_service.update_files_category(
            tender_id=tender_id,
            file_paths=file_paths,
            category=discipline,
            batch_id=batch['batch_id']
        )

        logger.info(
            f"Created batch {batch['batch_id']}, updated {updated_count} files")

        return jsonify({
            'success': True,
            'data': batch
        }), 201
    except Exception as e:
        logger.error(
            f"Failed to create batch for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches')
@require_auth
def list_batches(tender_id: str):
    """List all batches for a tender"""
    try:
        batches = blob_service.list_batches(tender_id)
        return jsonify({
            'success': True,
            'data': batches
        })
    except Exception as e:
        logger.error(
            f"Failed to list batches for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def get_batch(tender_id: str, batch_id: str):
    """Get batch details and files"""
    try:
        batch = blob_service.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        # Get files in batch
        files = blob_service.get_batch_files(tender_id, batch_id)

        return jsonify({
            'success': True,
            'data': {
                'batch': batch,
                'files': files
            }
        })
    except Exception as e:
        logger.error(
            f"Failed to get batch {batch_id} for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.patch('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def update_batch_status(tender_id: str, batch_id: str):
    """Update batch status"""
    try:
        data = request.json
        status = data.get('status')

        if not status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400

        batch = blob_service.update_batch_status(tender_id, batch_id, status)

        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        return jsonify({
            'success': True,
            'data': batch
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(
            f"Failed to update batch {batch_id} status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders/<tender_id>/batches/<batch_id>/retry')
@require_auth
def retry_batch(tender_id: str, batch_id: str):
    """Manually retry a failed or stuck batch submission"""
    try:
        # Verify batch exists
        batch = blob_service.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        # Check if batch is in a retriable state
        status = batch.get('status', '')
        if status not in ['pending', 'failed']:
            return jsonify({
                'success': False,
                'error': f'Batch cannot be retried. Current status: {status}. Only pending or failed batches can be retried.'
            }), 400

        # Get tender info for submission
        tender = blob_service.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        tender_name = tender.get('name', tender_id)

        # Get batch details
        file_paths = batch.get('file_paths', [])
        category = batch.get('category', '')
        title_block_coords = batch.get('title_block_coords', {})
        sharepoint_folder_path = batch.get('sharepoint_folder_path', '')
        output_folder_path = batch.get('output_folder_path', '')
        folder_list = batch.get('folder_list', [])

        # Get email from current user making the retry request (not from old batch metadata)
        # This ensures we use a valid email even for legacy batches with display names
        user_info = extract_user_info(request.headers)
        user_email = user_info.get('email') or user_info.get('name', 'system')

        if not file_paths:
            return jsonify({
                'success': False,
                'error': 'Batch has no files to process'
            }), 400

        # Spawn background thread to retry submission
        logger.info(
            f"Manual retry initiated for batch {batch_id} in tender {tender_id} by {user_email}")

        retry_thread = threading.Thread(
            target=_process_uipath_submission_async,
            args=(
                tender_id,
                tender_name,
                batch_id,
                file_paths,
                category,
                title_block_coords,
                user_email,
                sharepoint_folder_path,
                output_folder_path,
                folder_list
            ),
            daemon=True
        )
        retry_thread.start()

        return jsonify({
            'success': True,
            'message': 'Batch retry initiated. Processing in background.'
        }), 202

    except Exception as e:
        logger.error(
            f"Failed to retry batch {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def delete_batch(tender_id: str, batch_id: str):
    """Delete a batch (admin only - files remain categorized)"""
    try:
        success = blob_service.delete_batch(tender_id, batch_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Batch not found or could not be deleted'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Batch deleted successfully. Files have been uncategorized.'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete batch {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches/<batch_id>/progress')
@require_auth
def get_batch_progress(tender_id: str, batch_id: str):
    """
    Get file-level progress for a batch by querying Entity Store

    Returns aggregated status counts and per-file details including:
    - Total file count
    - Status breakdown (queued, extracted, failed, exported)
    - Per-file metadata (status, drawing_number, etc.)
    """
    try:
        # Get batch to retrieve CUID reference
        batch = blob_service.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        reference = batch.get('uipath_reference')

        # If batch not yet submitted to UiPath, return default progress
        if not reference:
            file_count = int(batch.get('file_count', 0))
            logger.info(
                f"Batch {batch_id} not yet submitted to UiPath. Returning default progress.")
            return jsonify({
                'success': True,
                'data': {
                    'batch_id': batch_id,
                    'total_files': file_count,
                    'status_counts': {
                        'queued': file_count,
                        'extracted': 0,
                        'failed': 0,
                        'exported': 0
                    },
                    'files': []
                }
            })

        # Query Entity Store for file-level progress
        logger.info(
            f"Querying Entity Store progress for batch {batch_id} with reference {reference}")
        progress = uipath_client.get_batch_progress(reference)

        # Add batch_id to response
        progress['batch_id'] = batch_id

        return jsonify({
            'success': True,
            'data': progress
        })

    except Exception as e:
        logger.error(
            f"Failed to get batch progress for {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/webhooks/uipath/batch-complete')
def uipath_batch_complete_webhook():
    """
    Webhook endpoint for UiPath to notify when a batch is complete

    Expected payload:
    {
        "reference": "cuid-reference-string",
        "status": "completed" | "failed",
        "completed_at": "ISO-8601 datetime"
    }

    Note: This endpoint does NOT require authentication since it's called by UiPath.
    Security is handled via UiPath's webhook signing (TODO: implement signature validation).
    """
    try:
        data = request.json

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        reference = data.get('reference')
        webhook_status = data.get('status')
        completed_at = data.get('completed_at')

        if not reference:
            return jsonify({
                'success': False,
                'error': 'reference is required'
            }), 400

        if not webhook_status or webhook_status not in ['completed', 'failed']:
            return jsonify({
                'success': False,
                'error': 'status must be "completed" or "failed"'
            }), 400

        logger.info(
            f"Webhook received: Batch {reference} status={webhook_status}")

        # Find batch by uipath_reference across all tenders
        # Note: This is not the most efficient approach, but blob storage metadata
        # doesn't support cross-tender queries. Consider caching or indexing if performance becomes an issue.
        tenders = blob_service.list_tenders()
        batch_found = False

        for tender in tenders:
            tender_id = tender['name']
            batches = blob_service.list_batches(tender_id)

            for batch in batches:
                if batch.get('uipath_reference') == reference:
                    batch_id = batch.get('batch_id')
                    logger.info(
                        f"Found batch {batch_id} in tender {tender_id} for reference {reference}")

                    # Update batch status
                    blob_service.update_batch_status(
                        tender_id, batch_id, webhook_status)

                    logger.info(
                        f"Updated batch {batch_id} status to {webhook_status}")
                    batch_found = True
                    break

            if batch_found:
                break

        if not batch_found:
            logger.warning(
                f"Webhook received for unknown reference: {reference}")
            return jsonify({
                'success': False,
                'error': 'Batch not found for reference'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Batch status updated'
        }), 200

    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/admin/purge-old-batches')
@require_auth
def purge_old_batches():
    """
    Admin endpoint to mark old stuck batches as failed.
    Useful for cleaning up legacy batches that don't have submission tracking.
    """
    try:
        # Optional query parameter for age threshold (default 24 hours)
        age_hours = request.args.get('age_hours', 24, type=int)

        logger.info(
            f"[Admin] Starting manual purge of batches older than {age_hours} hours")

        tenders = blob_service.list_tenders()
        purged_count = 0
        checked_count = 0
        errors = []

        for tender in tenders:
            tender_id = tender['id']

            try:
                batches = blob_service.list_batches(tender_id)

                for batch in batches:
                    # Only process pending batches
                    if batch.get('status') == 'pending':
                        checked_count += 1

                        try:
                            submitted_at = datetime.fromisoformat(
                                batch['submitted_at'])
                            age = datetime.utcnow() - submitted_at
                            submission_attempts = batch.get(
                                'submission_attempts', [])

                            # Mark as failed if old and no tracking
                            if age > timedelta(hours=age_hours) and len(submission_attempts) == 0:
                                batch_id = batch['batch_id']
                                logger.info(
                                    f"[Admin] Purging batch {batch_id} in tender {tender_id} "
                                    f"(age: {int(age.total_seconds()//3600)} hours)"
                                )

                                blob_service.update_batch(tender_id, batch_id, {
                                    'status': 'failed',
                                    'last_error': f'Manually purged: Legacy batch older than {age_hours} hours with no submission tracking'
                                })

                                purged_count += 1

                        except (ValueError, KeyError) as parse_error:
                            error_msg = f"Error parsing batch {batch.get('batch_id')} in tender {tender_id}: {parse_error}"
                            logger.error(f"[Admin] {error_msg}")
                            errors.append(error_msg)

            except Exception as tender_error:
                error_msg = f"Error processing tender {tender_id}: {tender_error}"
                logger.error(f"[Admin] {error_msg}")
                errors.append(error_msg)

        logger.info(
            f"[Admin] Purge complete: Checked {checked_count} pending batches, purged {purged_count}")

        return jsonify({
            'success': True,
            'message': f'Purge complete',
            'data': {
                'checked': checked_count,
                'purged': purged_count,
                'age_threshold_hours': age_hours,
                'errors': errors if errors else None
            }
        })

    except Exception as e:
        logger.error(
            f"[Admin] Purge operation failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# UiPath API


@app.post('/api/uipath/extract')
@require_auth
def queue_extraction():
    """Queue drawing metadata extraction via UiPath - creates batch and submits job"""
    try:
        data = request.json
        tender_id = data.get('tender_id')
        tender_name = data.get('tender_name')
        file_paths = data.get('file_paths', [])

        # Support both 'discipline' (legacy) and 'destination' (new)
        destination = data.get('destination')
        # Fallback for backward compatibility
        discipline = data.get('discipline')

        # Use destination if provided, otherwise fall back to discipline
        category = destination or discipline

        # {x, y, width, height} in pixels
        title_block_coords = data.get('title_block_coords')
        batch_name = data.get(
            'batch_name', f"{category} Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

        # Get SharePoint paths from request
        sharepoint_folder_path = data.get('sharepoint_folder_path')
        output_folder_path = data.get('output_folder_path')

        # Get folder list from request (list of folder names)
        folder_list = data.get('folder_list', [])

        if not all([tender_id, file_paths, category, title_block_coords]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: tender_id, file_paths, destination (or discipline), title_block_coords'
            }), 400

        user_info = extract_user_info(request.headers)

        logger.info(
            f"Creating batch and queuing extraction for tender {tender_id}")

        # Create batch first (with both discipline and destination for compatibility)
        # Use email for UiPath user lookup, fallback to name if no email
        batch = blob_service.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=category,  # Store in discipline field for backward compatibility
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get(
                'email') or user_info.get('name', 'Unknown'),
            job_id=None,  # Will be updated after UiPath submission
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list
        )

        # Update file categories and batch references
        blob_service.update_files_category(
            tender_id=tender_id,
            file_paths=file_paths,
            category=category,
            batch_id=batch['batch_id']
        )

        # Start UiPath submission in background thread to avoid timeout
        # The batch is already created and files are categorized, so we can return immediately
        submission_thread = threading.Thread(
            target=_process_uipath_submission_async,
            args=(
                tender_id,
                tender_name,
                batch['batch_id'],
                file_paths,
                category,
                title_block_coords,
                user_info.get('email', 'Unknown'),
                sharepoint_folder_path,
                output_folder_path,
                folder_list
            ),
            daemon=True  # Daemon thread will not block app shutdown
        )
        submission_thread.start()

        logger.info(
            f"Successfully created batch {batch['batch_id']} and queued for UiPath submission (processing in background)")

        # Return immediately with batch details
        # The UiPath submission will complete in the background
        return jsonify({
            'success': True,
            'data': {
                'batch_id': batch['batch_id'],
                'status': 'pending',  # Initial status
                'message': f'Batch created successfully. Processing {len(file_paths)} files in background.',
                'batch': batch
            }
        }), 202

    except Exception as e:
        logger.error(f"Failed to queue extraction: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/uipath/jobs/<job_id>')
@require_auth
def get_job_status(job_id: str):
    """Get UiPath job status"""
    try:
        status = uipath_client.get_job_status(job_id)
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# SharePoint API (placeholder for future integration)


@app.post('/api/sharepoint/validate')
@require_auth
def validate_sharepoint_path():
    """Validate SharePoint folder path"""
    try:
        data = request.json
        path = data.get('path')

        # TODO: Implement SharePoint validation
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'SharePoint validation not yet implemented'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/sharepoint/list-folders')
@require_auth
def list_sharepoint_folders():
    """List subfolders in a SharePoint folder using Graph API"""
    try:
        data = request.json
        access_token = data.get('access_token')
        drive_id = data.get('drive_id')  # output_library_id
        folder_path = data.get('folder_path')  # output_folder_path

        if not access_token or not drive_id or not folder_path:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: access_token, drive_id, folder_path'
            }), 400

        # Handle two possible path formats:
        # 1. Full Graph API format: "/drives/{drive-id}/root:/path"
        # 2. Simple path format: "/path"

        if folder_path.startswith('/drives/'):
            # Extract the actual path from the full Graph API format
            # Format: /drives/{drive-id}/root:/actual/path
            logger.info(
                f"Folder path is in full Graph API format: {folder_path}")

            # Find the "/root:" part and extract what comes after it
            root_index = folder_path.find('/root:')
            if root_index != -1:
                actual_path = folder_path[root_index + 6:]  # Skip "/root:"
                logger.info(f"Extracted actual path: {actual_path}")

                # Construct Graph API URL using the extracted path
                graph_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{actual_path}:/children"
            else:
                # Fallback: use the full path as-is (shouldn't happen but handle it)
                logger.warning(f"Could not find '/root:' in path, using as-is")
                graph_url = f"https://graph.microsoft.com/v1.0{folder_path}:/children"
        else:
            # Simple path format - construct the full URL
            logger.info(f"Folder path is in simple format: {folder_path}")
            graph_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{folder_path}:/children"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        logger.info(f"Fetching folders from: {graph_url}")

        response = requests.get(graph_url, headers=headers)

        if not response.ok:
            error_text = response.text
            logger.error(f"Graph API error: {error_text}")
            return jsonify({
                'success': False,
                'error': f'Graph API request failed: {response.status_code} - {error_text}'
            }), response.status_code

        result = response.json()

        # Filter to only include folders (items with 'folder' property)
        folders = []
        for item in result.get('value', []):
            if 'folder' in item:
                folders.append({
                    'name': item.get('name'),
                    'id': item.get('id'),
                    # Just return the folder name, not full path
                    'path': item.get('name')
                })

        logger.info(f"Found {len(folders)} folders")

        return jsonify({
            'success': True,
            'data': folders
        })

    except Exception as e:
        logger.error(
            f"Failed to list SharePoint folders: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/sharepoint/import-files')
@require_auth
def import_sharepoint_files():
    """Import files from SharePoint to blob storage (backend-driven)"""
    try:
        data = request.json
        tender_id = data.get('tender_id')
        access_token = data.get('access_token')
        items = data.get('items', [])
        category = data.get('category', 'sharepoint-import')

        if not tender_id or not access_token or not items:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: tender_id, access_token, items'
            }), 400

        # Verify tender exists
        tender = blob_service.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Initialize job tracking
        with import_jobs_lock:
            sharepoint_import_jobs[job_id] = {
                'job_id': job_id,
                'tender_id': tender_id,
                'status': 'running',
                'progress': 0,
                'total': len(items),
                'current_file': '',
                'success_count': 0,
                'error_count': 0,
                'errors': [],
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

        # Start background import thread
        import_thread = threading.Thread(
            target=_process_sharepoint_import,
            args=(job_id, tender_id, access_token, items, category)
        )
        import_thread.daemon = True
        import_thread.start()

        logger.info(
            f"Started SharePoint import job {job_id} for tender {tender_id} with {len(items)} items")

        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'running',
                'total': len(items)
            }
        })

    except Exception as e:
        logger.error(
            f"Failed to start SharePoint import: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/sharepoint/import-jobs/<job_id>')
@require_auth
def get_sharepoint_import_job_status(job_id: str):
    """Get status of a SharePoint import job"""
    try:
        with import_jobs_lock:
            job = sharepoint_import_jobs.get(job_id)

        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        return jsonify({
            'success': True,
            'data': job
        })

    except Exception as e:
        logger.error(
            f"Failed to get import job status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _process_sharepoint_import(job_id: str, tender_id: str, access_token: str, items: list, category: str):
    """Background thread function to process SharePoint file imports"""
    try:
        for i, item in enumerate(items):
            # Update current file
            file_name = item.get('name', 'unknown')
            relative_path = item.get('relativePath', '')

            with import_jobs_lock:
                if job_id in sharepoint_import_jobs:
                    sharepoint_import_jobs[job_id]['current_file'] = file_name
                    sharepoint_import_jobs[job_id]['progress'] = i
                    sharepoint_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                    ).isoformat()

            try:
                # Check if it's a folder (folders don't have downloadUrl)
                download_url = item.get('downloadUrl')
                if not download_url:
                    logger.info(
                        f"Skipping folder or item without download URL: {file_name}")
                    continue

                # Download file from SharePoint
                logger.info(
                    f"Downloading {file_name} from SharePoint (job {job_id})...")
                response = requests.get(
                    download_url,
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=300  # 5 minute timeout for large files
                )

                if not response.ok:
                    raise Exception(
                        f"Failed to download: {response.status_code} {response.reason}")

                # Determine category (preserve folder structure if relativePath provided)
                upload_category = category
                if relative_path:
                    # Use the first folder in relative path as category
                    upload_category = relative_path.strip('/').split('/')[0]

                # Upload to blob storage
                logger.info(
                    f"Uploading {file_name} to blob storage...")

                # Create a FileStorage-like object from the downloaded content
                file_stream = BytesIO(response.content)
                file_storage = FileStorage(
                    stream=file_stream,
                    filename=file_name,
                    content_type=item.get(
                        'mimeType', 'application/octet-stream')
                )

                file_metadata = blob_service.upload_file(
                    tender_id=tender_id,
                    file=file_storage,
                    category=upload_category,
                    uploaded_by='SharePoint Import',
                    source='sharepoint'
                )

                # Increment success count
                with import_jobs_lock:
                    if job_id in sharepoint_import_jobs:
                        sharepoint_import_jobs[job_id]['success_count'] += 1

                logger.info(
                    f"Successfully imported {file_name} (job {job_id})")

            except Exception as item_error:
                error_msg = f"{file_name}: {str(item_error)}"
                logger.error(
                    f"Failed to import {file_name} in job {job_id}: {str(item_error)}")

                with import_jobs_lock:
                    if job_id in sharepoint_import_jobs:
                        sharepoint_import_jobs[job_id]['error_count'] += 1
                        sharepoint_import_jobs[job_id]['errors'].append(
                            error_msg)

        # Mark job as complete
        with import_jobs_lock:
            if job_id in sharepoint_import_jobs:
                job = sharepoint_import_jobs[job_id]
                job['status'] = 'completed' if job['error_count'] == 0 else 'completed_with_errors'
                job['progress'] = len(items)
                job['current_file'] = ''
                job['updated_at'] = datetime.utcnow().isoformat()
                job['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"SharePoint import job {job_id} completed: {sharepoint_import_jobs[job_id]['success_count']} succeeded, {sharepoint_import_jobs[job_id]['error_count']} failed")

        # Schedule cleanup
        cleanup_thread = threading.Thread(
            target=_cleanup_import_job,
            args=(job_id,)
        )
        cleanup_thread.daemon = True
        cleanup_thread.start()

    except Exception as e:
        logger.error(
            f"Fatal error in SharePoint import job {job_id}: {str(e)}", exc_info=True)

        with import_jobs_lock:
            if job_id in sharepoint_import_jobs:
                sharepoint_import_jobs[job_id]['status'] = 'failed'
                sharepoint_import_jobs[job_id]['errors'].append(
                    f"Fatal error: {str(e)}")
                sharepoint_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                ).isoformat()


def _cleanup_import_job(job_id: str):
    """Remove completed job from memory after cleanup period"""
    time.sleep(JOB_CLEANUP_SECONDS)
    with import_jobs_lock:
        if job_id in sharepoint_import_jobs:
            del sharepoint_import_jobs[job_id]
            logger.info(f"Cleaned up import job {job_id}")


# Health check


@app.get('/api/health')
def health_check():
    """Health check endpoint (unauthenticated for monitoring)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.get('/api/config')
@require_auth
def get_config():
    """Get frontend configuration from environment variables"""
    return jsonify({
        'success': True,
        'data': {
            'entraClientId': os.getenv('ENTRA_CLIENT_ID', ''),
            'entraTenantId': os.getenv('ENTRA_TENANT_ID', ''),
            'sharepointBaseUrl': os.getenv('SHAREPOINT_BASE_URL', '')
        }
    })


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    # For non-API routes, serve React app (client-side routing)
    return app.send_static_file('index.html')


@app.errorhandler(500)
def handle_500(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', debug=True, port=8080)
