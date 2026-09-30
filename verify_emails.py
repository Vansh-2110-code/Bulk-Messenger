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
    
    # 1. Primary lookup using public DNS over HTTPS API (100% native and reliable inside Docker / VPS)
    try:
        url = f"https://dns.google/resolve?name={domain}&type=MX"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if "Answer" in data and len(data["Answer"]) > 0:
                return True, "Domain and MX records verified"
            # If no MX records, check if domain has an A record
            if data.get("Status") == 0:
                return True, "Domain resolved successfully"
    except Exception:
        pass

    # 2. Fallback to native socket lookup
    try:
        socket.gethostbyname(domain)
        return True, "Domain resolved successfully"
    except socket.gaierror:
        # 3. Secondary check with Google DNS A record in case local DNS is broken
        try:
            url = f"https://dns.google/resolve?name={domain}&type=A"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if "Answer" in data and len(data["Answer"]) > 0:
                    return True, "Domain resolved via DNS over HTTPS"
        except Exception:
            pass
        return False, f"Domain '{domain}' is not resolvable / does not exist"
    except Exception:
        return True, "Domain resolution assumed valid"

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
