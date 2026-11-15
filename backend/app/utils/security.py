import hashlib
import hmac
import os
import json
import base64
import time

SECRET_KEY = os.environ.get("ANEMIAWATCH_SECRET_KEY", "anemiawatch-production-medical-key-2026")
SALT = b"anemiawatch-salt-secure-hash"

def hash_password(password: str) -> str:
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), SALT, 100000)
    return key.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def create_access_token(data: dict, expires_in_seconds: int = 86400 * 7) -> str:
    payload = data.copy()
    payload['exp'] = int(time.time()) + expires_in_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    
    encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode('utf-8')).decode('utf-8').rstrip("=")
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip("=")
    
    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
    
    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"

def decode_access_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        
        # Pad base64
        rem = len(sig_b64) % 4
        padded_sig = sig_b64 + ("=" * (4 - rem) if rem else "")
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode('utf-8'))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        rem = len(payload_b64) % 4
        padded_payload = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode('utf-8')).decode('utf-8'))
        
        if payload.get('exp', 0) < int(time.time()):
            return None # Expired
            
        return payload
    except Exception:
        return None
