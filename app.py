from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
import re
from datetime import datetime

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Use stdout for Railway logging
    ]
)

app = Flask(__name__)

# Enhanced CORS configuration
CORS(app, 
     origins=[
         'https://reebii.github.io',
         'http://localhost:3000',  # For local development
         'http://127.0.0.1:3000'   # Alternative localhost
     ],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# Request counter for basic stats (in-memory)
request_stats = {
    'total_requests': 0,
    'successful_validations': 0,
    'failed_validations': 0,
    'start_time': datetime.now()
}

def advanced_email_validation(email):
    """
    Advanced email validation with multiple checks
    """
    try:
        # Basic format check
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, email):
            return False, "Invalid email format"
        
        # Split email into local and domain parts
        local, domain = email.rsplit('@', 1)
        
        # Check local part length (max 64 characters)
        if len(local) > 64:
            return False, "Local part too long (max 64 characters)"
        
        # Check domain part length (max 253 characters)
        if len(domain) > 253:
            return False, "Domain part too long (max 253 characters)"
        
        # Check for consecutive dots
        if '..' in email:
            return False, "Consecutive dots not allowed"
        
        # Check for dots at start or end of local part
        if local.startswith('.') or local.endswith('.'):
            return False, "Local part cannot start or end with a dot"
        
        # Check domain has at least one dot
        if '.' not in domain:
            return False, "Domain must contain at least one dot"
        
        # Check domain doesn't start or end with hyphen
        if domain.startswith('-') or domain.endswith('-'):
            return False, "Domain cannot start or end with hyphen"
        
        # Basic disposable email check (you can expand this list)
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        ]
        
        if domain.lower() in disposable_domains:
            return False, "Disposable email addresses are not allowed"
        
        return True, "Email format is valid"
        
    except Exception as e:
        logging.error(f"Email validation error: {e}")
        return False, "Validation error occurred"

# Try to import custom email validator, fallback to built-in
try:
    from email_validator import check_email as custom_check_email
    logging.info("Successfully imported custom email_validator module")
    
    def check_email(email):
        return custom_check_email(email)
        
except ImportError as e:
    logging.warning(f"Custom email_validator not found: {e}")
    logging.info("Using built-in advanced email validation")
    
    def check_email(email):
        return advanced_email_validation(email)

@app.route('/validate', methods=['POST', 'OPTIONS'])
def validate_email():
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        # Update stats
        request_stats['total_requests'] += 1
        
        # Log the request
        logging.info(f"Validation request received from {request.remote_addr}")
        
        # Get the email from the request
        data = request.get_json()
        
        if not data or 'email' not in data:
            logging.warning("Request missing email field")
            request_stats['failed_validations'] += 1
            return jsonify({
                'valid': False,
                'message': 'No email provided in request'
            }), 400
        
        email = data['email'].strip()
        
        if not email:
            logging.warning("Empty email provided")
            request_stats['failed_validations'] += 1
            return jsonify({
                'valid': False,
                'message': 'Empty email address'
            }), 400
        
        # Basic length check
        if len(email) > 254:  # RFC 5321 limit
            logging.warning(f"Email too long: {len(email)} characters")
            request_stats['failed_validations'] += 1
            return jsonify({
                'valid': False,
                'message': 'Email address too long (max 254 characters)'
            }), 400
        
        # Log the validation attempt
        logging.info(f"Validating email: {email}")
        
        # Use email validation function
        start_time = datetime.now()
        valid, info = check_email(email)
        end_time = datetime.now()
        
        # Calculate response time
        response_time = (end_time - start_time).total_seconds()
        
        # Update stats
        if valid:
            request_stats['successful_validations'] += 1
        else:
            request_stats['failed_validations'] += 1
        
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
        request_stats['failed_validations'] += 1
        
        return jsonify({
            'valid': False,
            'message': 'Server error occurred during validation',
            'error_type': type(e).__name__
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'message': 'Email validator API is running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'uptime_seconds': (datetime.now() - request_stats['start_time']).total_seconds()
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """API usage statistics"""
    try:
        uptime = datetime.now() - request_stats['start_time']
        
        return jsonify({
            'total_requests': request_stats['total_requests'],
            'successful_validations': request_stats['successful_validations'],
            'failed_validations': request_stats['failed_validations'],
            'success_rate': f"{(request_stats['successful_validations'] / max(request_stats['total_requests'], 1) * 100):.1f}%",
            'uptime_seconds': uptime.total_seconds(),
            'uptime_human': str(uptime).split('.')[0],  # Remove microseconds
            'start_time': request_stats['start_time'].isoformat(),
            'last_request': datetime.now().isoformat()
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
        'description': 'Professional email validation with advanced format checking',
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
                    'response_time': '0.12s',
                    'timestamp': '2024-01-01T12:00:00'
                }
            }
        },
        'features': [
            'Advanced email format validation',
            'RFC 5321 compliance checking',
            'Disposable email detection',
            'Real-time validation',
            'CORS enabled for web apps'
        ],
        'github': 'https://github.com/Reebii/email-validator-web',
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
    # Get port from environment variable (required for Railway, Heroku, etc.)
    port = int(os.environ.get('PORT', 5000))
    
    logging.info(f"Starting Email Validator API server on port {port}")
    logging.info("API endpoints:")
    logging.info("  POST /validate - Validate an email address")
    logging.info("  GET /health - Health check")
    logging.info("  GET /stats - API statistics")
    logging.info("  GET / - API information")
    
    # Run the Flask app
    app.run(debug=False, host='0.0.0.0', port=port)