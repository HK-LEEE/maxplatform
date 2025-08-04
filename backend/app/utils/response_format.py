"""
Standardized API Response Format - Wave 3 Implementation
Provides consistent response structure across all API endpoints
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from fastapi.responses import JSONResponse

class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PROCESSING = "processing"

class StandardResponse(BaseModel):
    """Standard API response structure"""
    status: ResponseStatus
    message: str
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: str
    
    class Config:
        use_enum_values = True

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ListResponse(BaseModel):
    """Standard list response with pagination"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = "Data retrieved successfully"
    data: List[Any]
    meta: PaginationMeta
    timestamp: str
    
    class Config:
        use_enum_values = True

class ResponseBuilder:
    """Builder for creating standardized API responses"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation completed successfully",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create success response"""
        return StandardResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            meta=meta,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    
    @staticmethod
    def error(
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create error response"""
        error_data = {
            "message": message
        }
        
        if code:
            error_data["code"] = code
        
        if details:
            error_data["details"] = details
        
        return StandardResponse(
            status=ResponseStatus.ERROR,
            message=message,
            data=error_data,
            meta=meta,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    
    @staticmethod
    def list_response(
        items: List[Any],
        page: int = 1,
        per_page: int = 10,
        total_items: int = 0,
        message: str = "Data retrieved successfully"
    ) -> Dict[str, Any]:
        """Create paginated list response"""
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
        
        pagination_meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        return ListResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=items,
            meta=pagination_meta,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    
    @staticmethod
    def created(
        data: Any,
        message: str = "Resource created successfully",
        location: Optional[str] = None
    ) -> JSONResponse:
        """Create 201 Created response"""
        response_data = ResponseBuilder.success(data=data, message=message)
        headers = {}
        
        if location:
            headers["Location"] = location
        
        return JSONResponse(
            status_code=201,
            content=response_data,
            headers=headers
        )
    
    @staticmethod
    def updated(
        data: Any,
        message: str = "Resource updated successfully"
    ) -> Dict[str, Any]:
        """Create update response"""
        return ResponseBuilder.success(data=data, message=message)
    
    @staticmethod
    def deleted(
        message: str = "Resource deleted successfully",
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create delete response"""
        return ResponseBuilder.success(data=data, message=message)
    
    @staticmethod
    def no_content() -> JSONResponse:
        """Create 204 No Content response"""
        return JSONResponse(status_code=204)
    
    @staticmethod
    def partial_success(
        data: Any,
        message: str = "Operation partially completed",
        warnings: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create partial success response"""
        meta = {}
        if warnings:
            meta["warnings"] = warnings
        
        return StandardResponse(
            status=ResponseStatus.PARTIAL,
            message=message,
            data=data,
            meta=meta if meta else None,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    
    @staticmethod
    def processing(
        message: str = "Request is being processed",
        tracking_id: Optional[str] = None,
        estimated_completion: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create processing response for async operations"""
        meta = {}
        if tracking_id:
            meta["tracking_id"] = tracking_id
        if estimated_completion:
            meta["estimated_completion"] = estimated_completion
        
        return StandardResponse(
            status=ResponseStatus.PROCESSING,
            message=message,
            data=None,
            meta=meta if meta else None,
            timestamp=datetime.utcnow().isoformat()
        ).dict()

# Response type aliases for common patterns
SuccessResponse = Dict[str, Any]
ErrorResponse = Dict[str, Any]
ListResponseType = Dict[str, Any]

# Common response messages
class ResponseMessages:
    """Standard response messages"""
    
    # Success messages
    OPERATION_SUCCESS = "Operation completed successfully"
    DATA_RETRIEVED = "Data retrieved successfully"
    RESOURCE_CREATED = "Resource created successfully"
    RESOURCE_UPDATED = "Resource updated successfully"
    RESOURCE_DELETED = "Resource deleted successfully"
    
    # LLM Model specific messages
    MODEL_CREATED = "LLM 모델이 성공적으로 생성되었습니다"
    MODEL_UPDATED = "LLM 모델이 성공적으로 업데이트되었습니다"
    MODEL_DELETED = "LLM 모델이 성공적으로 삭제되었습니다"
    MODELS_RETRIEVED = "LLM 모델 목록을 성공적으로 조회했습니다"
    
    PERMISSION_GRANTED = "모델 권한이 성공적으로 부여되었습니다"
    PERMISSION_REVOKED = "모델 권한이 성공적으로 해제되었습니다"
    PERMISSIONS_RETRIEVED = "모델 권한 목록을 성공적으로 조회했습니다"
    
    # Error messages
    INVALID_INPUT = "입력 데이터가 올바르지 않습니다"
    RESOURCE_NOT_FOUND = "요청한 리소스를 찾을 수 없습니다"
    UNAUTHORIZED = "인증이 필요합니다"
    FORBIDDEN = "접근 권한이 없습니다"
    INTERNAL_ERROR = "내부 서버 오류가 발생했습니다"
    SERVICE_UNAVAILABLE = "서비스가 일시적으로 사용할 수 없습니다"
    
    # Processing messages  
    PROCESSING_REQUEST = "요청을 처리 중입니다"
    ASYNC_OPERATION_STARTED = "비동기 작업이 시작되었습니다"

def format_response(
    success: bool = True,
    data: Any = None,
    message: Optional[str] = None,
    code: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Legacy support function for backward compatibility
    """
    if success:
        return ResponseBuilder.success(
            data=data,
            message=message or ResponseMessages.OPERATION_SUCCESS,
            meta=meta
        )
    else:
        return ResponseBuilder.error(
            message=message or ResponseMessages.INTERNAL_ERROR,
            code=code,
            meta=meta
        )

# Decorator for automatic response formatting
def standardize_response(message: Optional[str] = None):
    """Decorator to automatically format endpoint responses"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # If already formatted, return as-is
                if isinstance(result, dict) and 'status' in result:
                    return result
                
                # If it's a JSONResponse, return as-is
                if isinstance(result, JSONResponse):
                    return result
                
                # Format the result
                return ResponseBuilder.success(
                    data=result,
                    message=message or ResponseMessages.OPERATION_SUCCESS
                )
            
            except Exception as e:
                # Let error handler handle the exception
                raise e
        
        return wrapper
    return decorator