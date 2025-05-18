import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
load_dotenv(override=True)


from config import (
    SUPABASE_KEY,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.transip.email")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self._validate_config()

    def _validate_config(self):
        if not all([self.smtp_username, self.smtp_password, self.sender_email]):
            raise ValueError("Email configuration is missing")

    def _create_verification_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'type': 'verification'
        }
        return jwt.encode(payload, SUPABASE_KEY, algorithm='HS256')

    def _create_reset_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'reset'
        }
        return jwt.encode(payload, SUPABASE_KEY, algorithm='HS256')

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def send_verification_email(self, user_id: str, email: str) -> bool:
        token = self._create_verification_token(user_id)
        verification_url = f"{os.getenv('APP_URL', 'http://localhost:8501')}/verify?token={token}"
        
        html_content = f"""
        <html>
            <body>
                <h2>Welcome to Cycle Nutrition Assistant!</h2>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify Email Address</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't create an account, you can safely ignore this email.</p>
            </body>
        </html>
        """
        
        return self._send_email(
            email,
            "Verify your email address - Cycle Nutrition Assistant",
            html_content
        )

    def send_password_reset_email(self, user_id: str, email: str) -> bool:
        token = self._create_reset_token(user_id)
        reset_url = f"{os.getenv('APP_URL', 'http://localhost:8501')}/reset-password?token={token}"
        
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>You requested to reset your password. Click the link below to set a new password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
            </body>
        </html>
        """
        
        return self._send_email(
            email,
            "Reset your password - Cycle Nutrition Assistant",
            html_content
        )

    def verify_token(self, token: str) -> tuple[bool, str, str]:
        try:
            payload = jwt.decode(token, SUPABASE_KEY, algorithms=['HS256'])
            return True, payload['user_id'], payload['type']
        except jwt.ExpiredSignatureError:
            return False, "", "Token has expired"
        except jwt.InvalidTokenError:
            return False, "", "Invalid token" 

    def send_password_reset_email(self, to_email, reset_link):
        subject = "Password Reset Request"
        body = f"Click the following link to reset your password: {reset_link}\n\nIf you did not request this, ignore this email."
        return self._send_email(to_email, subject, body) 