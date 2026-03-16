import os
import json
import jwt
import httpx
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.algorithms import RSAAlgorithm
from dotenv import load_dotenv

load_dotenv()

# We need the publishable key or secret key to get the JWKS URL
CLERK_PUBLISHABLE_KEY = os.getenv("VITE_CLERK_PUBLISHABLE_KEY")

security = HTTPBearer()
jwks_cache = None

def get_jwks():
    global jwks_cache
    if jwks_cache:
        return jwks_cache
        
    if not CLERK_PUBLISHABLE_KEY:
        raise ValueError("VITE_CLERK_PUBLISHABLE_KEY is not set in backend .env")
        
    # Extract the frontend API domain from the Base64-encoded publishable key
    try:
        # pk_test_Y2xlcmsuYXBwLmNvbSQ= -> "clerk.app.com"
        import base64
        # Remove the prefix "pk_test_" or "pk_live_"
        b64_str = CLERK_PUBLISHABLE_KEY.split("_")[2]
        decoded = base64.b64decode(b64_str + "==").decode("utf-8")
        frontend_api = decoded.replace("$", "")
        
        jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        
        response = httpx.get(jwks_url)
        response.raise_for_status()
        jwks_cache = response.json()
        return jwks_cache
    except Exception as e:
        print(f"Failed to fetch JWKS: {e}")
        return None

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verifies Clerk JWT and returns the User ID (Subject)"""
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization header")
        
    # We can skip verification for development if no key is provided, but we shouldn't.
    jwks = get_jwks()
    if not jwks:
        raise HTTPException(status_code=500, detail="Could not fetch JWKS data")

    try:
        # Get the unverified header to find the Key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing kid")

        # Find the matching key in our JWKS
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = RSAAlgorithm.from_jwk(json.dumps(key))
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid Key ID in token")

        # Verify the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False} # The aud depends on the issuer, we can ignore for now
        )
        
        user_id = payload.get("sub")
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
