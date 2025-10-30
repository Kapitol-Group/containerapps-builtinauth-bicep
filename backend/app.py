import base64
import json
import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from services.blob_storage import BlobStorageService
from services.uipath_client import UiPathClient
from utils.auth import extract_user_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    base_url=os.getenv('UIPATH_API_URL'),
    api_key=os.getenv('UIPATH_API_KEY')
)

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


@app.get('/api/tenders/<tender_id>')
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

        # Create batch
        batch = blob_service.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=discipline,
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get('name', 'Unknown'),
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


@app.delete('/api/tenders/<tender_id>/batches/<batch_id>')
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
            'message': 'Batch deleted successfully. Files remain categorized.'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete batch {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# UiPath API


@app.post('/api/uipath/extract')
def queue_extraction():
    """Queue drawing metadata extraction via UiPath - creates batch and submits job"""
    try:
        data = request.json
        tender_id = data.get('tender_id')
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

        if not all([tender_id, file_paths, category, title_block_coords]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: tender_id, file_paths, destination (or discipline), title_block_coords'
            }), 400

        user_info = extract_user_info(request.headers)

        logger.info(
            f"Creating batch and queuing extraction for tender {tender_id}")

        # Create batch first (with both discipline and destination for compatibility)
        batch = blob_service.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=category,  # Store in discipline field for backward compatibility
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get('name', 'Unknown'),
            job_id=None  # Will be updated after UiPath submission
        )

        # Update file categories and batch references
        blob_service.update_files_category(
            tender_id=tender_id,
            file_paths=file_paths,
            category=category,
            batch_id=batch['batch_id']
        )

        # Submit job to UiPath with batch_id reference
        try:
            job = uipath_client.submit_extraction_job(
                tender_id=tender_id,
                file_paths=file_paths,
                discipline=category,  # Pass as discipline for UiPath compatibility
                title_block_coords=title_block_coords,
                submitted_by=user_info.get('name', 'Unknown'),
                batch_id=batch['batch_id']  # Pass batch_id to UiPath
            )

            # Update batch with job_id
            batch['job_id'] = job.get('job_id')

            # Note: In real implementation, we'd update the batch metadata blob with job_id
            # For now, just return both in response

            logger.info(
                f"Successfully created batch {batch['batch_id']} and queued job {job.get('job_id')}")

            return jsonify({
                'success': True,
                'data': {
                    'batch_id': batch['batch_id'],
                    'job_id': job.get('job_id'),
                    'status': job.get('status'),
                    'batch': batch
                }
            }), 202

        except Exception as uipath_error:
            # Rollback: delete batch if UiPath submission fails
            logger.error(
                f"UiPath submission failed, rolling back batch: {str(uipath_error)}")
            blob_service.delete_batch(tender_id, batch['batch_id'])
            raise

    except Exception as e:
        logger.error(f"Failed to queue extraction: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/uipath/jobs/<job_id>')
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

        import requests

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

# Health check


@app.get('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.get('/api/config')
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
