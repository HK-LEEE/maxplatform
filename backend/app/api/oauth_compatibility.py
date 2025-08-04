"""
OAuth Compatibility Router
Provides compatibility endpoints for various logout URL patterns
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import quote
from sqlalchemy.orm import Session
from ..database import get_db

router = APIRouter()

# Root-level logout endpoints for compatibility
@router.get("/logout", response_class=RedirectResponse)
@router.post("/logout", response_class=RedirectResponse)
async def oauth_logout_root(
    request: Request,
    post_logout_redirect_uri: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    id_token_hint: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Root logout compatibility - redirects to standard OIDC logout"""
    params = []
    if post_logout_redirect_uri:
        params.append(f"post_logout_redirect_uri={quote(post_logout_redirect_uri)}")
    if client_id:
        params.append(f"client_id={client_id}")
    if id_token_hint:
        params.append(f"id_token_hint={id_token_hint}")
    if state:
        params.append(f"state={state}")
    
    query_string = "&".join(params)
    redirect_url = f"/api/oauth/logout"
    if query_string:
        redirect_url += f"?{query_string}"
    
    return RedirectResponse(url=redirect_url, status_code=302)

# API-level logout compatibility endpoints
@router.get("/api/logout", response_class=RedirectResponse)
@router.post("/api/logout", response_class=RedirectResponse)
async def oauth_logout_api(
    request: Request,
    post_logout_redirect_uri: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    id_token_hint: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """API logout compatibility - redirects to standard OIDC logout"""
    params = []
    if post_logout_redirect_uri:
        params.append(f"post_logout_redirect_uri={quote(post_logout_redirect_uri)}")
    if client_id:
        params.append(f"client_id={client_id}")
    if id_token_hint:
        params.append(f"id_token_hint={id_token_hint}")
    if state:
        params.append(f"state={state}")
    
    query_string = "&".join(params)
    redirect_url = f"/api/oauth/logout"
    if query_string:
        redirect_url += f"?{query_string}"
    
    return RedirectResponse(url=redirect_url, status_code=302)

# OAuth path-level compatibility endpoints  
@router.get("/oauth/logout", response_class=RedirectResponse)
@router.post("/oauth/logout", response_class=RedirectResponse)
async def oauth_logout_oauth_path(
    request: Request,
    post_logout_redirect_uri: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    id_token_hint: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """OAuth path logout compatibility - redirects to standard OIDC logout"""
    params = []
    if post_logout_redirect_uri:
        params.append(f"post_logout_redirect_uri={quote(post_logout_redirect_uri)}")
    if client_id:
        params.append(f"client_id={client_id}")
    if id_token_hint:
        params.append(f"id_token_hint={id_token_hint}")
    if state:
        params.append(f"state={state}")
    
    query_string = "&".join(params)
    redirect_url = f"/api/oauth/logout"
    if query_string:
        redirect_url += f"?{query_string}"
    
    return RedirectResponse(url=redirect_url, status_code=302)