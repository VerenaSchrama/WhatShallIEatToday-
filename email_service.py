import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
import logging
load_dotenv(override=True)


from config import (
    SUPABASE_SERVICE_ROLE_KEY,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)

print("EMAIL SERVICE SUPABASE_SERVICE_ROLE_KEY:", SUPABASE_SERVICE_ROLE_KEY)

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
        token = jwt.encode(payload, SUPABASE_SERVICE_ROLE_KEY, algorithm='HS256')
        logging.warning(f"GENERATING TOKEN FOR USER ID: {user_id}")
        logging.warning(f"GENERATED TOKEN: {token}")
        return token

    def _create_reset_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'reset'
        }
        return jwt.encode(payload, SUPABASE_SERVICE_ROLE_KEY, algorithm='HS256')

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def send_verification_email(self, user_id: str, email: str) -> bool:
        token = self._create_verification_token(user_id)
        verification_url = f"{os.getenv('APP_URL', 'http://localhost:8501')}/verify?token={token}"
        
        html_content = f"""
        <html>
          <body>
            <h2>Welcome to Cycle Nutrition Assistant, {email}!</h2>
            <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
            <p><a href=\"{verification_url}\">Verify Email Address</a></p>
            <p>If you did not create an account, you can safely ignore this email.</p>
            <br>
            <p>Best regards,<br>The Cycle Nutrition Assistant Team</p>
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
            <p>Hello,</p>
            <p>We received a request to reset your password for your Cycle Nutrition Assistant account.</p>
            <p>If you made this request, please click the link below to reset your password:</p>
            <p><a href=\"{reset_url}\">Reset Password</a></p>
            <p>If you did not request a password reset, you can safely ignore this email.</p>
            <br>
            <p>Best regards,<br>The Cycle Nutrition Assistant Team</p>
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
            payload = jwt.decode(token, SUPABASE_SERVICE_ROLE_KEY, algorithms=['HS256'])
            return True, payload['user_id'], payload['type']
        except jwt.ExpiredSignatureError:
            return False, "", "Token has expired"
        except jwt.InvalidTokenError:
            return False, "", "Invalid token" 

    def send_password_reset_email(self, to_email, reset_link):
        subject = "Password Reset Request"
        body = f"Click the following link to reset your password: {reset_link}\n\nIf you did not request this, ignore this email."
        return self._send_email(to_email, subject, body) 