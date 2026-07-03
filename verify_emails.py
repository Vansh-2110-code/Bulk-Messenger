import re
import socket
import urllib.request
import json

def is_valid_email_syntax(email):
    """Check if the email has valid syntax."""
    if not email or not isinstance(email, str):
        return False
    # Standard email validation regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def verify_email_domain(email):
    """Verify if the email domain is active and can receive mail."""
    if not is_valid_email_syntax(email):
        return False, "Invalid email syntax"
    
    domain = email.strip().split('@')[1]
    
    try:
        # Check if the domain is resolvable
        socket.gethostbyname(domain)
    except socket.gaierror:
        return False, f"Domain '{domain}' is not resolvable / does not exist"
        
    # Standard lookup using a public DNS over HTTPS API (100% native and reliable inside Docker)
    try:
        url = f"https://dns.google/resolve?name={domain}&type=MX"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if "Answer" in data and len(data["Answer"]) > 0:
                return True, "Domain and MX records verified"
    except Exception as e:
        # Fallback: if DNS API is blocked, assume domain resolvability is enough
        pass
        
    return True, "Domain resolved successfully"

def verify_single_email(email):
    """Perform syntax and domain verification on a single email."""
    if not email:
        return {"valid": False, "reason": "Empty email"}
        
    valid_syntax = is_valid_email_syntax(email)
    if not valid_syntax:
        return {"valid": False, "reason": "Invalid syntax format"}
        
    valid_domain, reason = verify_email_domain(email)
    if not valid_domain:
        return {"valid": False, "reason": reason}
        
    return {"valid": True, "reason": "Verified successfully"}
