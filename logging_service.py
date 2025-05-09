import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import json

class LoggingService:
    def __init__(self):
        self.log_dir = "logs"
        self._setup_logging()

    def _setup_logging(self):
        # Create logs directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                RotatingFileHandler(
                    os.path.join(self.log_dir, 'app.log'),
                    maxBytes=10485760,  # 10MB
                    backupCount=5
                ),
                logging.StreamHandler()
            ]
        )

        # Create loggers for different components
        self.auth_logger = logging.getLogger('auth')
        self.app_logger = logging.getLogger('app')
        self.email_logger = logging.getLogger('email')
        self.db_logger = logging.getLogger('db')

    def log_auth_event(self, event_type: str, user_id: str = None, success: bool = True, details: dict = None):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'success': success,
            'details': details or {}
        }
        if success:
            self.auth_logger.info(json.dumps(log_data))
        else:
            self.auth_logger.error(json.dumps(log_data))

    def log_app_event(self, event_type: str, details: dict = None, level: str = 'INFO'):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details or {}
        }
        if level.upper() == 'ERROR':
            self.app_logger.error(json.dumps(log_data))
        else:
            self.app_logger.info(json.dumps(log_data))

    def log_email_event(self, event_type: str, recipient: str, success: bool = True, details: dict = None):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'recipient': recipient,
            'success': success,
            'details': details or {}
        }
        if success:
            self.email_logger.info(json.dumps(log_data))
        else:
            self.email_logger.error(json.dumps(log_data))

    def log_db_event(self, event_type: str, table: str, success: bool = True, details: dict = None):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'table': table,
            'success': success,
            'details': details or {}
        }
        if success:
            self.db_logger.info(json.dumps(log_data))
        else:
            self.db_logger.error(json.dumps(log_data))

    def get_recent_logs(self, component: str = None, level: str = None, limit: int = 100) -> list:
        log_file = os.path.join(self.log_dir, 'app.log')
        logs = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f.readlines()[-limit:]:
                    try:
                        log_entry = json.loads(line.split(' - ')[-1])
                        if component and log_entry.get('event_type', '').startswith(component):
                            continue
                        if level and log_entry.get('level', '').upper() != level.upper():
                            continue
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return logs 