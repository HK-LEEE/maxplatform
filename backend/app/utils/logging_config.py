"""
Central Logging Configuration for MAX Platform
Standardized timestamp format and security data filtering
"""

import logging
import logging.config
import logging.handlers
import sys
import re
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class SecurityDataFilter:
    """Filter sensitive data in log messages for security compliance"""
    
    @staticmethod
    def filter_key(key: str, show_length: int = 10) -> str:
        """
        Filter security keys showing only first N characters
        Format: head[10] as requested by user
        """
        if not key or len(key) <= show_length:
            return key
        
        return f"{key[:show_length]}..."
    
    @staticmethod
    def filter_token(token: str) -> str:
        """Filter JWT tokens showing only first 10 characters"""
        return SecurityDataFilter.filter_key(token, 10)
    
    @staticmethod
    def filter_hash(hash_value: str) -> str:
        """Filter hash values showing only first 10 characters"""
        return SecurityDataFilter.filter_key(hash_value, 10)
    
    @staticmethod
    def filter_sensitive_data(message: str) -> str:
        """
        Auto-filter common sensitive patterns in log messages
        """
        # Pattern for JWT tokens (3 base64 parts separated by dots)
        jwt_pattern = r'\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'
        message = re.sub(jwt_pattern, lambda m: SecurityDataFilter.filter_token(m.group()), message)
        
        # Pattern for hash values (long hex strings)
        hash_pattern = r'\b[a-fA-F0-9]{32,}\b'
        message = re.sub(hash_pattern, lambda m: SecurityDataFilter.filter_hash(m.group()), message)
        
        # Pattern for API keys and secrets
        secret_pattern = r'(secret[_-]?[a-zA-Z0-9]*["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{16,})'
        message = re.sub(secret_pattern, lambda m: f"{m.group(1)}{SecurityDataFilter.filter_key(m.group(2))}", message, flags=re.IGNORECASE)
        
        return message


class CustomFormatter(logging.Formatter):
    """
    Custom formatter with standardized timestamp and security filtering
    Format: yyyy-mm-dd HH:MM:SS.fff as requested
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.security_filter = SecurityDataFilter()
    
    def formatTime(self, record, datefmt=None):
        """
        Format timestamp as yyyy-mm-dd HH:MM:SS.fff
        """
        ct = self.converter(record.created)
        if datefmt:
            s = datetime(*ct[:6]).strftime(datefmt)
        else:
            # Custom format: yyyy-mm-dd HH:MM:SS.fff
            dt = datetime(*ct[:6])
            s = dt.strftime('%Y-%m-%d %H:%M:%S')
            # Add milliseconds
            s += f".{int(record.msecs):03d}"
        return s
    
    def format(self, record):
        """Format log record with security filtering"""
        # Apply security filtering to the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.security_filter.filter_sensitive_data(record.msg)
        
        # Format the record normally
        formatted = super().format(record)
        
        # Apply additional security filtering to the entire formatted message
        return self.security_filter.filter_sensitive_data(formatted)


def setup_logging(
    log_level: str = None,
    log_file: Optional[str] = None,
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10,
    use_daily_rotation: bool = True
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  If None, will be determined by environment
        log_file: Optional log file path
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        use_daily_rotation: Use daily rotation instead of size-based
    """
    
    # Determine log level based on environment if not specified
    if log_level is None:
        env = os.getenv('MAX_ENV', 'development').lower()
        if env in ['production', 'prod']:
            log_level = 'INFO'
        elif env in ['staging', 'test']:
            log_level = 'INFO'
        else:  # development
            log_level = 'DEBUG'
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Console handler configuration
    console_handler = {
        'class': 'logging.StreamHandler',
        'level': 'DEBUG' if log_level == 'DEBUG' else 'INFO',
        'formatter': 'detailed',
        'stream': 'ext://sys.stdout'
    }
    
    # File handler configuration (if log_file provided)
    handlers = {
        'console': console_handler
    }
    
    if log_file:
        if use_daily_rotation:
            # Use TimedRotatingFileHandler for daily rotation
            handlers['file'] = {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': log_file + '.log',  # Base filename
                'when': 'midnight',
                'interval': 1,
                'backupCount': backup_count,
                'encoding': 'utf8'
            }
        else:
            # Use size-based rotation
            handlers['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': log_file,
                'maxBytes': max_bytes,
                'backupCount': backup_count,
                'encoding': 'utf8'
            }
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                '()': CustomFormatter,
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
            },
            'simple': {
                '()': CustomFormatter,
                'format': '%(asctime)s [%(levelname)s] - %(message)s'
            }
        },
        'handlers': handlers,
        'root': {
            'level': log_level,
            'handlers': list(handlers.keys())
        },
        'loggers': {
            # OAuth and authentication specific loggers
            'app.api.oauth_simple': {
                'level': 'DEBUG',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'app.utils.auth': {
                'level': 'DEBUG',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'app.security': {
                'level': 'DEBUG',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            # Database loggers
            'sqlalchemy.engine': {
                'level': 'WARNING',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            # FastAPI loggers
            'uvicorn': {
                'level': 'INFO',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': list(handlers.keys()),
                'propagate': False
            }
        }
    }
    
    # Apply the configuration
    logging.config.dictConfig(config)


def get_auth_logger() -> logging.Logger:
    """Get logger specifically for authentication events"""
    return logging.getLogger('app.utils.auth')


def get_oauth_logger() -> logging.Logger:
    """Get logger specifically for OAuth events"""
    return logging.getLogger('app.api.oauth_simple')


def get_security_logger() -> logging.Logger:
    """Get logger specifically for security events"""
    return logging.getLogger('app.security')


def log_auth_event(
    event_type: str,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
    token_hash: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log authentication event with security filtering
    
    Args:
        event_type: Type of auth event (login, token_refresh, token_revoke, etc.)
        user_id: User ID involved
        client_id: OAuth client ID
        token_hash: Token hash (will be filtered for security)
        success: Whether the event was successful
        error: Error message if unsuccessful
        additional_data: Additional event data
    """
    logger = get_auth_logger()
    
    # Prepare log data with security filtering
    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'client_id': client_id,
        'success': success
    }
    
    # Filter sensitive token data
    if token_hash:
        log_data['token_hash'] = SecurityDataFilter.filter_hash(token_hash)
    
    if error:
        log_data['error'] = error
    
    if additional_data:
        log_data['additional_data'] = additional_data
    
    # Log with appropriate level
    if success:
        logger.info(f"Auth event: {event_type} | Data: {log_data}")
    else:
        logger.warning(f"Auth event failed: {event_type} | Data: {log_data}")


def log_oauth_event(
    event_type: str,
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    scope: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """
    Log OAuth-specific event with detailed tracking
    
    Args:
        event_type: OAuth event type (authorize, token_grant, token_refresh, etc.)
        client_id: OAuth client ID
        user_id: User ID involved
        scope: OAuth scope requested/granted
        success: Whether the event was successful
        error: Error message if unsuccessful
        ip_address: Client IP address
        user_agent: Client user agent
    """
    logger = get_oauth_logger()
    
    log_data = {
        'event_type': event_type,
        'client_id': client_id,
        'user_id': user_id,
        'scope': scope,
        'success': success,
        'ip_address': ip_address,
        'user_agent': SecurityDataFilter.filter_key(user_agent or '', 50) if user_agent else None
    }
    
    if error:
        log_data['error'] = error
    
    # Log with appropriate level
    if success:
        logger.info(f"OAuth event: {event_type} | Data: {log_data}")
    else:
        logger.error(f"OAuth event failed: {event_type} | Data: {log_data}")


# Example usage and testing
if __name__ == "__main__":
    # Test the logging configuration
    setup_logging("DEBUG", "/tmp/maxplatform_test.log")
    
    # Test security filtering
    test_logger = logging.getLogger("test")
    
    # Test sensitive data filtering
    test_logger.info("Testing JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
    test_logger.info("Testing hash: a1b2c3d4e5f6789012345678901234567890abcdef1234567890")
    test_logger.info("Testing secret: client_secret = secret_lab_2025_dev_very_long_secret")
    
    # Test auth event logging
    log_auth_event(
        event_type="token_refresh",
        user_id="user123",
        client_id="maxlab",
        token_hash="a1b2c3d4e5f6789012345678901234567890abcdef",
        success=True
    )
    
    # Test OAuth event logging
    log_oauth_event(
        event_type="authorization_grant",
        client_id="maxlab",
        user_id="user123",
        scope="read:profile manage:experiments",
        success=True,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    print("Logging configuration test completed. Check /tmp/maxplatform_test.log for output.")