import base64
import json
import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from services.blob_storage import BlobStorageService
from services.uipath_client import UiPathClient
from utils.auth import extract_user_info

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
        tenders = blob_service.list_tenders()
        return jsonify({
            'success': True,
            'data': tenders
        })
    except Exception as e:
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
        sharepoint_path = data.get('sharepoint_path')
        output_location = data.get('output_location')

        if not tender_name:
            return jsonify({
                'success': False,
                'error': 'Tender name is required'
            }), 400

        user_info = extract_user_info(request.headers)

        tender = blob_service.create_tender(
            tender_name=tender_name,
            created_by=user_info.get('name', 'Unknown'),
            metadata={
                'sharepoint_path': sharepoint_path,
                'output_location': output_location,
                'created_at': datetime.utcnow().isoformat()
            }
        )

        return jsonify({
            'success': True,
            'data': tender
        }), 201
    except Exception as e:
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
        blob_service.delete_tender(tender_id)
        return jsonify({
            'success': True,
            'message': 'Tender deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Files API


@app.get('/api/tenders/<tender_id>/files')
def list_files(tender_id: str):
    """List files in a tender"""
    try:
        files = blob_service.list_files(tender_id)
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

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        user_info = extract_user_info(request.headers)

        file_info = blob_service.upload_file(
            tender_id=tender_id,
            file=file,
            category=category,
            uploaded_by=user_info.get('name', 'Unknown')
        )

        return jsonify({
            'success': True,
            'data': file_info
        }), 201
    except Exception as e:
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
        blob_service.delete_file(tender_id, file_path)
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# UiPath API


@app.post('/api/uipath/extract')
def queue_extraction():
    """Queue drawing metadata extraction via UiPath"""
    try:
        data = request.json
        tender_id = data.get('tender_id')
        file_paths = data.get('file_paths', [])
        discipline = data.get('discipline')
        # {x, y, width, height} in pixels
        title_block_coords = data.get('title_block_coords')

        if not all([tender_id, file_paths, discipline, title_block_coords]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        user_info = extract_user_info(request.headers)

        # Submit job to UiPath
        job = uipath_client.submit_extraction_job(
            tender_id=tender_id,
            file_paths=file_paths,
            discipline=discipline,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get('name', 'Unknown')
        )

        return jsonify({
            'success': True,
            'data': job
        }), 202
    except Exception as e:
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
