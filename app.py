from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)

# Configure CORS for production
CORS(app, origins=["*"], methods=["GET", "POST"], allow_headers=["Content-Type"])

# Import your email validator script
try:
    from email_validator import check_email
    logging.info("Successfully imported email_validator module")
except ImportError as e:
    logging.error(f"Failed to import email_validator: {e}")
    # Fallback basic validation if your script isn't available
    def check_email(email):
        import re
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if re.match(pattern, email):
            return True, "Basic syntax validation passed (full validation unavailable)"
        return False, "Invalid email format"

@app.route('/validate', methods=['POST', 'OPTIONS'])
def validate_email():
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        # Log the request
        logging.info(f"Validation request received from {request.remote_addr}")
        
        # Get the email from the request
        data = request.get_json()
        
        if not data or 'email' not in data:
            logging.warning("Request missing email field")
            return jsonify({
                'valid': False,
                'message': 'No email provided in request'
            }), 400
        
        email = data['email'].strip()
        
        if not email:
            logging.warning("Empty email provided")
            return jsonify({
                'valid': False,
                'message': 'Empty email address'
            }), 400
        
        # Basic length check
        if len(email) > 254:  # RFC 5321 limit
            logging.warning(f"Email too long: {len(email)} characters")
            return jsonify({
                'valid': False,
                'message': 'Email address too long'
            }), 400
        
        # Log the validation attempt
        logging.info(f"Validating email: {email}")
        
        # Use your existing check_email function
        start_time = datetime.now()
        valid, info = check_email(email)
        end_time = datetime.now()
        
        # Calculate response time
        response_time = (end_time - start_time).total_seconds()
        
        # Log the result
        logging.info(f"Validation result for {email}: {valid} - {info} (took {response_time:.2f}s)")
        
        return jsonify({
            'valid': valid,
            'message': info,
            'email': email,
            'response_time': f"{response_time:.2f}s",
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        # Log the error for debugging
        error_msg = f"Error validating email: {str(e)}"
        logging.error(error_msg)
        
        return jsonify({
            'valid': False,
            'message': f'Server error occurred during validation',
            'error_type': type(e).__name__
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'message': 'Email validator API is running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """Basic API statistics"""
    try:
        # Read log file to get basic stats
        log_file = 'api_log.txt'
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            total_requests = len([l for l in lines if 'Validation request received' in l])
            successful_validations = len([l for l in lines if 'Validation result' in l and 'True' in l])
            
            return jsonify({
                'total_requests': total_requests,
                'successful_validations': successful_validations,
                'uptime': 'Available in logs',
                'last_request': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'total_requests': 0,
                'message': 'No statistics available yet'
            }), 200
            
    except Exception as e:
        logging.error(f"Error getting stats: {e}")
        return jsonify({
            'error': 'Unable to fetch statistics'
        }), 500

@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        'name': 'Email Validator API',
        'version': '1.0.0',
        'description': 'Professional email validation with SMTP verification',
        'endpoints': {
            'POST /validate': 'Validate an email address',
            'GET /health': 'Health check',
            'GET /stats': 'API usage statistics',
            'GET /': 'This information'
        },
        'usage': {
            'validate': {
                'method': 'POST',
                'url': '/validate',
                'body': {'email': 'test@example.com'},
                'response': {
                    'valid': True,
                    'message': 'Validation result details',
                    'email': 'test@example.com',
                    'response_time': '1.23s',
                    'timestamp': '2024-01-01T12:00:00'
                }
            }
        },
        'github': 'https://github.com/yourusername/email-validator',
        'docs': 'See GitHub repository for documentation'
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': ['/', '/validate', '/health', '/stats']
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'message': 'The requested method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    # Check if email_validator.py exists
    if not os.path.exists('email_validator.py'):
        logging.warning("email_validator.py not found! Using fallback validation.")
        print("Warning: email_validator.py not found in the current directory!")
        print("The API will use basic syntax validation only.")
    
    # Get port from environment variable (required for Railway, Heroku, etc.)
    port = int(os.environ.get('PORT', 5000))
    
    logging.info(f"Starting Email Validator API server on port {port}")
    logging.info("API endpoints:")
    logging.info("  POST /validate - Validate an email address")
    logging.info("  GET /health - Health check")
    logging.info("  GET /stats - API statistics")
    logging.info("  GET / - API information")
    
    # Run the Flask app
    # In production, use debug=False
    app.run(debug=False, host='0.0.0.0', port=port)