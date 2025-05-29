import re
import bcrypt
import uuid
from datetime import datetime, timedelta
import jwt
from supabase import create_client
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SESSION_TIMEOUT,
    PASSWORD_MIN_LENGTH,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    VERIFICATION_TOKEN_EXPIRY,
    RESET_TOKEN_EXPIRY
)
from email_service import EmailService
from logging_service import LoggingService
import secrets

class AuthService:
    def __init__(self):
        print("=== AuthService Initialization ===")
        print(f"SUPABASE_URL: {SUPABASE_URL}")
        print(f"SUPABASE_SERVICE_ROLE_KEY exists: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
        print(f"SUPABASE_SERVICE_ROLE_KEY length: {len(SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else 0}")
        print(f"SUPABASE_SERVICE_ROLE_KEY first 10 chars: {SUPABASE_SERVICE_ROLE_KEY[:10] if SUPABASE_SERVICE_ROLE_KEY else 'None'}")
        try:
            print("Attempting to create Supabase client...")
            self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            print("Supabase client created successfully")
            
            # Test the connection with a simpler query
            print("Testing Supabase connection...")
            try:
                # Just try to get the auth configuration
                auth_config = self.supabase.auth.get_session()
                print("Connection test successful - Auth configuration retrieved")
            except Exception as auth_error:
                print(f"Auth test failed: {str(auth_error)}")
                # Try a simple table query as fallback
                try:
                    test_response = self.supabase.table("users").select("id").limit(1).execute()
                    print("Connection test successful - Table query worked")
                except Exception as table_error:
                    print(f"Table test failed: {str(table_error)}")
                    raise
        except Exception as e:
            print(f"Error creating Supabase client: {str(e)}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                print(f"Response body: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
            raise
        self.email_service = EmailService()
        self.logger = LoggingService()
        self._validate_config()
        print("=== AuthService Initialization Complete ===")

    def _validate_config(self):
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("Supabase configuration is missing")

    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_password(self, password: str) -> tuple[bool, str]:
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, ERROR_MESSAGES["password_too_short"]
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, ""

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def _generate_session_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=SESSION_TIMEOUT)
        }
        return jwt.encode(payload, SUPABASE_SERVICE_ROLE_KEY, algorithm='HS256')

    def register_user(self, email: str, password: str) -> tuple[bool, str]:
        try:
            # Validate email
            if not self._validate_email(email):
                self.logger.log_auth_event('register', success=False, details={'error': 'invalid_email'})
                return False, ERROR_MESSAGES["invalid_email"]

            # Validate password
            is_valid, message = self._validate_password(password)
            if not is_valid:
                self.logger.log_auth_event('register', success=False, details={'error': 'invalid_password'})
                return False, message

            # Check if user exists
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if response.data:
                self.logger.log_auth_event('register', success=False, details={'error': 'user_exists'})
                return False, ERROR_MESSAGES["user_exists"]

            # Create user
            user_id = str(uuid.uuid4())
            hashed_pw = self._hash_password(password)
            
            self.supabase.table("users").insert({
                "id": user_id,
                "email": email,
                "password": hashed_pw,
                "email_verified": False,
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None
            }).execute()

            # Send verification email
            email_sent = self.email_service.send_verification_email(user_id, email)
            if not email_sent:
                self.logger.log_email_event('verification', email, success=False)
                return False, ERROR_MESSAGES["email_send_failed"]

            self.logger.log_auth_event('register', user_id, success=True)
            self.logger.log_email_event('verification', email, success=True)
            return True, SUCCESS_MESSAGES["registration"]

        except Exception as e:
            self.logger.log_auth_event('register', success=False, details={'error': str(e)})
            return False, f"Registration error: {str(e)}"

    def login_user(self, email: str, password: str) -> tuple[bool, dict, str]:
        try:
            # Validate email
            if not self._validate_email(email):
                self.logger.log_auth_event('login', success=False, details={'error': 'invalid_email'})
                return False, None, ERROR_MESSAGES["invalid_email"]

            # Get user
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if not response.data:
                self.logger.log_auth_event('login', success=False, details={'error': 'user_not_found'})
                return False, None, ERROR_MESSAGES["invalid_credentials"]

            user = response.data[0]
            
            # Check email verification
            if not user.get("email_verified", False):
                self.logger.log_auth_event('login', user["id"], success=False, details={'error': 'email_not_verified'})
                return False, None, ERROR_MESSAGES["email_verification_required"]
            
            # Verify password
            if not self._verify_password(password, user["password"]):
                self.logger.log_auth_event('login', user["id"], success=False, details={'error': 'invalid_password'})
                return False, None, ERROR_MESSAGES["invalid_credentials"]

            # Generate session token
            session_token = self._generate_session_token(user["id"])

            # Update last login
            self.supabase.table("users").update({
                "last_login": datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()

            self.logger.log_auth_event('login', user["id"], success=True)
            return True, {
                "id": user["id"],
                "email": user["email"],
                "session_token": session_token
            }, SUCCESS_MESSAGES["login"]

        except Exception as e:
            self.logger.log_auth_event('login', success=False, details={'error': str(e)})
            return False, None, f"Login error: {str(e)}"

    def reset_password(self, email: str) -> tuple[bool, str]:
        try:
            if not self._validate_email(email):
                self.logger.log_auth_event('password_reset', success=False, details={'error': 'invalid_email'})
                return False, ERROR_MESSAGES["invalid_email"]

            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if not response.data:
                self.logger.log_auth_event('password_reset', success=False, details={'error': 'user_not_found'})
                return False, ERROR_MESSAGES["invalid_credentials"]

            user = response.data[0]
            email_sent = self.email_service.send_password_reset_email(user["id"], email)
            
            if not email_sent:
                self.logger.log_email_event('password_reset', email, success=False)
                return False, ERROR_MESSAGES["email_send_failed"]

            self.logger.log_auth_event('password_reset', user["id"], success=True)
            self.logger.log_email_event('password_reset', email, success=True)
            return True, SUCCESS_MESSAGES["password_reset"]

        except Exception as e:
            self.logger.log_auth_event('password_reset', success=False, details={'error': str(e)})
            return False, f"Password reset error: {str(e)}"

    def verify_session(self, session_token: str) -> tuple[bool, str]:
        try:
            payload = jwt.decode(session_token, SUPABASE_SERVICE_ROLE_KEY, algorithms=['HS256'])
            self.logger.log_auth_event('session_verify', payload['user_id'], success=True)
            return True, payload['user_id']
        except jwt.ExpiredSignatureError:
            self.logger.log_auth_event('session_verify', success=False, details={'error': 'session_expired'})
            return False, ERROR_MESSAGES["session_expired"]
        except jwt.InvalidTokenError:
            self.logger.log_auth_event('session_verify', success=False, details={'error': 'invalid_token'})
            return False, "Invalid session token"

    def verify_email(self, token: str) -> tuple[bool, str]:
        try:
            success, user_id, token_type = self.email_service.verify_token(token)
            if not success or token_type != 'verification':
                self.logger.log_auth_event('email_verify', success=False, details={'error': 'invalid_token'})
                return False, ERROR_MESSAGES["invalid_token"]

            self.supabase.table("users").update({
                "email_verified": True
            }).eq("id", user_id).execute()

            self.logger.log_auth_event('email_verify', user_id, success=True)
            return True, SUCCESS_MESSAGES["email_verified"]

        except Exception as e:
            self.logger.log_auth_event('email_verify', success=False, details={'error': str(e)})
            return False, f"Email verification error: {str(e)}"

    def change_password(self, token: str, new_password: str) -> tuple[bool, str]:
        try:
            success, user_id, token_type = self.email_service.verify_token(token)
            if not success or token_type != 'reset':
                self.logger.log_auth_event('password_change', success=False, details={'error': 'invalid_token'})
                return False, ERROR_MESSAGES["invalid_token"]

            # Validate new password
            is_valid, message = self._validate_password(new_password)
            if not is_valid:
                self.logger.log_auth_event('password_change', success=False, details={'error': 'invalid_password'})
                return False, message

            # Update password
            hashed_pw = self._hash_password(new_password)
            self.supabase.table("users").update({
                "password": hashed_pw
            }).eq("id", user_id).execute()

            self.logger.log_auth_event('password_change', user_id, success=True)
            return True, SUCCESS_MESSAGES["password_changed"]

        except Exception as e:
            self.logger.log_auth_event('password_change', success=False, details={'error': str(e)})
            return False, f"Password change error: {str(e)}"

    def send_password_reset(self, email):
        try:
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            
            # Save token to database
            if not self.save_reset_token(email, token, expiry):
                return False, "Failed to save reset token"
            
            reset_link = f"http://localhost:8501/?token={token}"
            success = self.email_service.send_password_reset_email(email, reset_link)
            
            if success:
                return True, "Reset link sent."
            else:
                return False, "Failed to send reset email."
        except Exception as e:
            self.logger.log_auth_event('send_password_reset', success=False, details={'error': str(e)})
            return False, f"Error: {str(e)}"

    def verify_reset_token(self, token):
        # TODO: Retrieve token record from DB
        record = self.get_reset_token_record(token)
        if record and record['expiry'] > datetime.utcnow():
            return True, record['email']
        return False, None

    def reset_password(self, token, new_password):
        valid, email = self.verify_reset_token(token)
        if not valid:
            return False, "Invalid or expired token."
        # TODO: Update user's password in DB
        self.update_user_password(email, new_password)
        # TODO: Delete token after use
        self.delete_reset_token(token)
        return True, "Password reset successful." 
    
    def save_reset_token(self, email, token, expiry):
        try:
            print(f"Attempting to save reset token for email: {email}")
            print(f"Using Supabase URL: {SUPABASE_URL}")
            print(f"Using Supabase key length: {len(SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else 0}")
            
            response = self.supabase.table("password_resets").insert({
                "email": email,
                "token": token,
                "expiry": expiry.isoformat()
            }).execute()
            
            print(f"Reset token saved successfully: {response}")
            return True
        except Exception as e:
            print(f"Error saving reset token: {str(e)}")
            self.logger.log_auth_event('save_reset_token', success=False, details={'error': str(e)})
            raise