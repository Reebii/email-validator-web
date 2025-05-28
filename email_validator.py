import smtplib
import dns.resolver
import re
import time
import datetime
import logging
from validate_email_address import validate_email

# Configure Logging
logging.basicConfig(
    filename='email_validation_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_valid_syntax(email):
    # Basic regex for syntax validation
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def get_mx_records(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = [record.exchange.to_text() for record in records]
        return mx_hosts
    except Exception as e:
        logging.warning(f"MX record fetch failed: {e}")
        return []

def smtp_check(email, mx_hosts):
    from_address = "test@example.com"
    for mx in mx_hosts:
        try:
            server = smtplib.SMTP(timeout=10)
            start = time.time()
            server.connect(mx)
            server.helo("example.com")
            server.mail(from_address)
            code, message = server.rcpt(email)
            end = time.time()
            server.quit()

            response_time = end - start
            if code == 250:
                return True, response_time, message.decode()
            else:
                return False, response_time, message.decode()

        except Exception as e:
            logging.error(f"SMTP error: {e}")
            continue
    return False, None, "All SMTP attempts failed"

def check_email(email):
    logging.info(f"Validating email: {email}")
    
    if not is_valid_syntax(email):
        logging.warning("Invalid syntax")
        return False, "Invalid email format"

    domain = email.split('@')[-1]
    mx_hosts = get_mx_records(domain)
    
    if not mx_hosts:
        logging.warning("No MX records found")
        return False, "No MX records found"

    success, response_time, server_response = smtp_check(email, mx_hosts)
    
    if success:
        logging.info(f"Email {email} is valid. Response time: {response_time:.2f}s")
        return True, f"Valid. Response time: {response_time:.2f}s. Server: {server_response}"
    else:
        logging.warning(f"Email {email} is invalid. Server: {server_response}")
        return False, f"Invalid. Server: {server_response}"

if __name__ == "__main__":
    email_to_check = input("Enter email to validate: ").strip()
    valid, info = check_email(email_to_check)
    print(f"Result: {info}")
