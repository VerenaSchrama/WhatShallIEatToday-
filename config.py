import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # Client-side key
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Admin key

# Debug logging
print("=== Supabase Configuration Debug ===")
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_ANON_KEY exists: {bool(SUPABASE_ANON_KEY)}")
print(f"SUPABASE_ANON_KEY length: {len(SUPABASE_ANON_KEY) if SUPABASE_ANON_KEY else 0}")
print(f"SUPABASE_ANON_KEY first 10 chars: {SUPABASE_ANON_KEY[:10] if SUPABASE_ANON_KEY else 'None'}")
print(f"SUPABASE_ANON_KEY last 10 chars: {SUPABASE_ANON_KEY[-10:] if SUPABASE_ANON_KEY else 'None'}")
print(f"SUPABASE_SERVICE_ROLE_KEY exists: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
print(f"SUPABASE_SERVICE_ROLE_KEY length: {len(SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else 0}")
print(f"SUPABASE_SERVICE_ROLE_KEY first 10 chars: {SUPABASE_SERVICE_ROLE_KEY[:10] if SUPABASE_SERVICE_ROLE_KEY else 'None'}")
print(f"SUPABASE_SERVICE_ROLE_KEY last 10 chars: {SUPABASE_SERVICE_ROLE_KEY[-10:] if SUPABASE_SERVICE_ROLE_KEY else 'None'}")
print("==================================")

# Use service role key for admin and JWT operations
JWT_SECRET = SUPABASE_SERVICE_ROLE_KEY

# Verify key format
if JWT_SECRET:
    if not JWT_SECRET.startswith('eyJ'):
        print("WARNING: JWT_SECRET does not start with 'eyJ' - this might indicate an invalid JWT format")
    if len(JWT_SECRET) < 100:
        print("WARNING: JWT_SECRET seems too short for a valid JWT token")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Application Settings
SESSION_TIMEOUT = 3600  # 1 hour in seconds
MAX_LOGIN_ATTEMPTS = 3
PASSWORD_MIN_LENGTH = 8
VERIFICATION_TOKEN_EXPIRY = 24 * 3600  # 24 hours in seconds
RESET_TOKEN_EXPIRY = 1 * 3600  # 1 hour in seconds

# UI Constants
SUPPORT_OPTIONS = [
    "Nothing specific",
    "Hormonal balance and regular cycle",
    "Getting back my period",
    "More energy",
    "Acne",
    "Eat more nutritious in general",
    "Digestive health/ Metabolism boost"
]

DIETARY_OPTIONS = [
    "Vegan",
    "Vegetarian",
    "Nut allergy",
    "Gluten free",
    "Lactose intolerance"
]

CYCLE_PHASES = [
    "Menstrual",
    "Follicular",
    "Ovulatory",
    "Luteal"
]

# Error Messages
ERROR_MESSAGES = {
    "invalid_email": "Please enter a valid email address",
    "password_too_short": f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
    "password_mismatch": "Passwords do not match",
    "user_exists": "An account with this email already exists",
    "invalid_credentials": "Invalid email or password",
    "session_expired": "Your session has expired. Please log in again",
    "api_error": "An error occurred. Please try again later"
}

# Success Messages
SUCCESS_MESSAGES = {
    "registration": "Registration successful! Please check your email to verify your account",
    "login": "Login successful!",
    "settings_saved": "Your preferences have been saved successfully",
    "password_reset": "Password reset instructions have been sent to your email"
} 