"""
API Versioning Support - Wave 3 Implementation
Provides backward-compatible API versioning for smooth migrations
"""

from typing import Optional, Dict, Any, Callable
from enum import Enum
from fastapi import Request, Header
from fastapi.routing import APIRoute
import re

class APIVersion(str, Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"  # Future version for enhanced features

class VersionedResponse:
    """Response adapter for different API versions"""
    
    @staticmethod
    def adapt_response(data: Any, version: APIVersion) -> Any:
        """Adapt response format based on API version"""
        
        if version == APIVersion.V1:
            # V1 format - legacy response structure
            return VersionedResponse._to_v1_format(data)
        elif version == APIVersion.V2:
            # V2 format - standardized response structure (from response_format.py)
            return data  # Already in correct format
        else:
            # Default to latest version
            return data
    
    @staticmethod
    def _to_v1_format(data: Any) -> Any:
        """Convert standardized response to V1 legacy format"""
        
        # If it's already a legacy format, return as-is
        if not isinstance(data, dict) or 'status' not in data:
            return data
        
        # Convert standardized format to V1 format
        if data.get('status') == 'success':
            # V1 success format
            return {
                'success': True,
                'data': data.get('data'),
                'message': data.get('message', 'Success')
            }
        elif data.get('status') == 'error':
            # V1 error format
            error_data = data.get('data', {})
            return {
                'success': False,
                'error': error_data.get('message', data.get('message')),
                'code': error_data.get('code'),
                'details': error_data.get('details')
            }
        else:
            # Other statuses - keep as-is for now
            return data

class VersionExtractor:
    """Extract API version from request"""
    
    @staticmethod
    def from_header(accept_version: Optional[str] = Header(None)) -> APIVersion:
        """Extract version from Accept-Version header"""
        if accept_version:
            # Support formats: "v1", "v2", "application/vnd.api.v1", etc.
            version_match = re.search(r'v(\d+)', accept_version.lower())
            if version_match:
                version_num = version_match.group(1)
                try:
                    return APIVersion(f"v{version_num}")
                except ValueError:
                    pass
        
        # Default to V1 for backward compatibility
        return APIVersion.V1
    
    @staticmethod
    def from_path(request: Request) -> APIVersion:
        """Extract version from URL path (e.g., /api/v1/models)"""
        path = request.url.path
        version_match = re.search(r'/v(\d+)/', path)
        if version_match:
            version_num = version_match.group(1)
            try:
                return APIVersion(f"v{version_num}")
            except ValueError:
                pass
        
        # Default to V1 for backward compatibility
        return APIVersion.V1
    
    @staticmethod
    def from_query(request: Request) -> APIVersion:
        """Extract version from query parameter (e.g., ?version=v1)"""
        version_param = request.query_params.get('version')
        if version_param:
            try:
                return APIVersion(version_param.lower())
            except ValueError:
                pass
        
        # Default to V1 for backward compatibility
        return APIVersion.V1
    
    @staticmethod
    def extract_version(
        request: Request,
        accept_version: Optional[str] = Header(None)
    ) -> APIVersion:
        """
        Extract API version using multiple strategies:
        1. Accept-Version header (preferred)
        2. URL path version
        3. Query parameter
        4. Default to V1
        """
        
        # Priority 1: Header
        if accept_version:
            version = VersionExtractor.from_header(accept_version)
            if version != APIVersion.V1:  # Only if explicitly specified
                return version
        
        # Priority 2: Path
        path_version = VersionExtractor.from_path(request)
        if path_version != APIVersion.V1:  # Only if explicitly specified
            return path_version
        
        # Priority 3: Query parameter
        query_version = VersionExtractor.from_query(request)
        if query_version != APIVersion.V1:  # Only if explicitly specified
            return query_version
        
        # Default: V1 for backward compatibility
        return APIVersion.V1

def versioned_endpoint(supported_versions: list = None):
    """
    Decorator to mark endpoints as version-aware
    
    Args:
        supported_versions: List of supported API versions for this endpoint
    """
    if supported_versions is None:
        supported_versions = [APIVersion.V1, APIVersion.V2]
    
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Extract request and version info
            request = None
            accept_version = None
            
            # Find request and version parameters
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            for key, value in kwargs.items():
                if key == 'accept_version':
                    accept_version = value
                    break
            
            # Extract version
            if request:
                version = VersionExtractor.extract_version(
                    request, 
                    accept_version
                )
            else:
                version = APIVersion.V1
            
            # Check if version is supported
            if version not in supported_versions:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"API version {version.value} is not supported for this endpoint. "
                           f"Supported versions: {[v.value for v in supported_versions]}"
                )
            
            # Add version to kwargs for endpoint to use
            kwargs['api_version'] = version
            
            # Execute original function
            result = await func(*args, **kwargs)
            
            # Adapt response format based on version
            adapted_result = VersionedResponse.adapt_response(result, version)
            
            return adapted_result
        
        return wrapper
    return decorator

class VersionedRoute(APIRoute):
    """Custom route class that adds version information to OpenAPI spec"""
    
    def __init__(self, *args, **kwargs):
        # Extract version info from kwargs if provided
        self.supported_versions = kwargs.pop('supported_versions', [APIVersion.V1])
        super().__init__(*args, **kwargs)

def create_versioned_router(version: APIVersion, prefix: str = ""):
    """Create a router for a specific API version"""
    from fastapi import APIRouter
    
    version_prefix = f"/api/{version.value}" if not prefix else f"{prefix}/{version.value}"
    
    return APIRouter(
        prefix=version_prefix,
        tags=[f"API {version.value.upper()}"],
        responses={
            400: {"description": "Bad Request - Invalid API version"},
            406: {"description": "Not Acceptable - Unsupported API version"}
        }
    )

# Migration utilities
class APIVersionMigration:
    """Utilities for migrating between API versions"""
    
    @staticmethod
    def migrate_request_v1_to_v2(request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate V1 request format to V2"""
        # Add any request format migrations here
        return request_data
    
    @staticmethod
    def migrate_response_v2_to_v1(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate V2 response format to V1"""
        return VersionedResponse._to_v1_format(response_data)

# Version deprecation warnings
def add_deprecation_warning(version: APIVersion, response_headers: Dict[str, str]):
    """Add deprecation warnings to response headers"""
    if version == APIVersion.V1:
        response_headers["X-API-Deprecation-Warning"] = (
            "API v1 is deprecated. Please migrate to v2. "
            "See documentation for migration guide."
        )
        response_headers["X-API-Sunset-Date"] = "2024-12-31"  # Example sunset date

# Usage examples:
"""
# Example 1: Version-aware endpoint
@versioned_endpoint(supported_versions=[APIVersion.V1, APIVersion.V2])
async def get_models(
    request: Request,
    accept_version: Optional[str] = Header(None),
    api_version: APIVersion = APIVersion.V1  # Injected by decorator
):
    # Your endpoint logic here
    models = await get_models_from_db()
    
    # Response will be automatically adapted based on api_version
    return ResponseBuilder.success(data=models)

# Example 2: Version-specific router
v1_router = create_versioned_router(APIVersion.V1)
v2_router = create_versioned_router(APIVersion.V2)

@v1_router.get("/models")
async def get_models_v1():
    # V1 specific implementation
    pass

@v2_router.get("/models")  
async def get_models_v2():
    # V2 specific implementation
    pass
"""