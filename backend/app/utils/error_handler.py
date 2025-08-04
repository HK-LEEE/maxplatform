"""
Centralized Error Handling - Wave 2 Implementation
Provides consistent error responses and logging across all API endpoints
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime
from enum import Enum
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError
from pydantic import ValidationError

from .circuit_breaker import CircuitBreakerError

logger = logging.getLogger(__name__)

class ErrorCategory(str, Enum):
    """Error categories for consistent classification"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXTERNAL_SERVICE = "external_service"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class ErrorCode(str, Enum):
    """Standardized error codes"""
    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Authorization errors
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ACCESS_DENIED = "ACCESS_DENIED"
    
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    
    # Circuit breaker errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_DEGRADED = "SERVICE_DEGRADED"
    
    # Business logic errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_OPERATION = "INVALID_OPERATION"
    
    # System errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_MAINTENANCE = "SERVICE_MAINTENANCE"

class StandardizedError:
    """Standardized error response structure"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        retry_after: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.category = category
        self.details = details or {}
        self.user_message = user_message or message
        self.retry_after = retry_after
        self.correlation_id = correlation_id
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        response = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "category": self.category.value,
                "user_message": self.user_message,
                "timestamp": self.timestamp
            }
        }
        
        if self.details:
            response["error"]["details"] = self.details
        
        if self.retry_after:
            response["error"]["retry_after"] = self.retry_after
        
        if self.correlation_id:
            response["error"]["correlation_id"] = self.correlation_id
        
        return response

class ErrorHandler:
    """Centralized error handling and response generation"""
    
    @staticmethod
    def handle_database_error(
        error: Exception,
        operation: str = "database operation",
        correlation_id: Optional[str] = None
    ) -> StandardizedError:
        """Handle database-related errors"""
        
        if isinstance(error, TimeoutError):
            logger.error(f"Database timeout during {operation}: {error}")
            return StandardizedError(
                code=ErrorCode.DATABASE_TIMEOUT,
                message=f"Database timeout during {operation}",
                category=ErrorCategory.DATABASE,
                user_message="요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
                retry_after=30,
                correlation_id=correlation_id,
                details={"operation": operation}
            )
        
        elif isinstance(error, OperationalError):
            logger.error(f"Database connection error during {operation}: {error}")
            return StandardizedError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=f"Database connection error during {operation}",
                category=ErrorCategory.DATABASE,
                user_message="데이터베이스 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
                retry_after=60,
                correlation_id=correlation_id,
                details={"operation": operation}
            )
        
        elif isinstance(error, SQLAlchemyError):
            logger.error(f"Database error during {operation}: {error}")
            return StandardizedError(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Database error during {operation}",
                category=ErrorCategory.DATABASE,
                user_message="데이터베이스 작업 중 오류가 발생했습니다.",
                correlation_id=correlation_id,
                details={"operation": operation}
            )
        
        else:
            logger.error(f"Unknown database error during {operation}: {error}")
            return StandardizedError(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Unknown database error during {operation}",
                category=ErrorCategory.DATABASE,
                user_message="예상치 못한 데이터베이스 오류가 발생했습니다.",
                correlation_id=correlation_id,
                details={"operation": operation}
            )
    
    @staticmethod
    def handle_circuit_breaker_error(
        error: CircuitBreakerError,
        service_name: str = "service",
        correlation_id: Optional[str] = None
    ) -> StandardizedError:
        """Handle circuit breaker errors"""
        
        logger.warning(f"Circuit breaker open for {service_name}: {error}")
        
        return StandardizedError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=f"Service {service_name} is currently unavailable",
            category=ErrorCategory.CIRCUIT_BREAKER,
            user_message=f"{service_name} 서비스가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
            retry_after=60,
            correlation_id=correlation_id,
            details={"service": service_name}
        )
    
    @staticmethod
    def handle_validation_error(
        error: ValidationError,
        correlation_id: Optional[str] = None
    ) -> StandardizedError:
        """Handle Pydantic validation errors"""
        
        logger.warning(f"Validation error: {error}")
        
        # Extract validation details
        validation_details = []
        for err in error.errors():
            validation_details.append({
                "field": ".".join(str(x) for x in err["loc"]),
                "message": err["msg"],
                "type": err["type"]
            })
        
        return StandardizedError(
            code=ErrorCode.INVALID_INPUT,
            message="Input validation failed",
            category=ErrorCategory.VALIDATION,
            user_message="입력 데이터가 올바르지 않습니다.",
            correlation_id=correlation_id,
            details={"validation_errors": validation_details}
        )
    
    @staticmethod
    def handle_http_exception(
        error: HTTPException,
        correlation_id: Optional[str] = None
    ) -> StandardizedError:
        """Handle FastAPI HTTP exceptions"""
        
        # Map status codes to error categories and codes
        status_mapping = {
            401: (ErrorCategory.AUTHENTICATION, ErrorCode.INVALID_CREDENTIALS),
            403: (ErrorCategory.AUTHORIZATION, ErrorCode.ACCESS_DENIED),
            404: (ErrorCategory.DATABASE, ErrorCode.RESOURCE_NOT_FOUND),
            408: (ErrorCategory.DATABASE, ErrorCode.DATABASE_TIMEOUT),
            409: (ErrorCategory.DATABASE, ErrorCode.DUPLICATE_RESOURCE),
            422: (ErrorCategory.VALIDATION, ErrorCode.INVALID_INPUT),
            503: (ErrorCategory.CIRCUIT_BREAKER, ErrorCode.SERVICE_UNAVAILABLE),
        }
        
        category, code = status_mapping.get(
            error.status_code, 
            (ErrorCategory.SYSTEM, ErrorCode.INTERNAL_SERVER_ERROR)
        )
        
        return StandardizedError(
            code=code,
            message=error.detail,
            category=category,
            user_message=error.detail,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def handle_generic_error(
        error: Exception,
        context: str = "operation",
        correlation_id: Optional[str] = None
    ) -> StandardizedError:
        """Handle generic unexpected errors"""
        
        logger.error(f"Unexpected error during {context}: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return StandardizedError(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Internal server error during {context}",
            category=ErrorCategory.SYSTEM,
            user_message="예상치 못한 오류가 발생했습니다. 관리자에게 문의해주세요.",
            correlation_id=correlation_id,
            details={"context": context}
        )

def create_error_response(
    error: Union[Exception, StandardizedError],
    status_code: int = 500,
    correlation_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response"""
    
    if isinstance(error, StandardizedError):
        std_error = error
    else:
        # Convert exception to standardized error
        if isinstance(error, CircuitBreakerError):
            std_error = ErrorHandler.handle_circuit_breaker_error(error, correlation_id=correlation_id)
            status_code = 503
        elif isinstance(error, (OperationalError, TimeoutError)):
            std_error = ErrorHandler.handle_database_error(error, correlation_id=correlation_id)
            status_code = 408
        elif isinstance(error, SQLAlchemyError):
            std_error = ErrorHandler.handle_database_error(error, correlation_id=correlation_id)
            status_code = 500
        elif isinstance(error, ValidationError):
            std_error = ErrorHandler.handle_validation_error(error, correlation_id=correlation_id)
            status_code = 422
        elif isinstance(error, HTTPException):
            std_error = ErrorHandler.handle_http_exception(error, correlation_id=correlation_id)
            status_code = error.status_code
        else:
            std_error = ErrorHandler.handle_generic_error(error, correlation_id=correlation_id)
            status_code = 500
    
    # Set retry-after header if specified
    headers = {}
    if std_error.retry_after:
        headers["Retry-After"] = str(std_error.retry_after)
    
    return JSONResponse(
        status_code=status_code,
        content=std_error.to_dict(),
        headers=headers
    )

def get_correlation_id(request: Request) -> str:
    """Generate or extract correlation ID from request"""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        import uuid
        correlation_id = str(uuid.uuid4())
    return correlation_id

# Decorator for endpoint error handling
def handle_errors(correlation_id_header: str = "X-Correlation-ID"):
    """Decorator for consistent error handling in endpoints"""
    def decorator(func):
        async def wrapper(request: Request = None, *args, **kwargs):
            correlation_id = None
            if request:
                correlation_id = get_correlation_id(request)
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return create_error_response(e, correlation_id=correlation_id)
        
        return wrapper
    return decorator