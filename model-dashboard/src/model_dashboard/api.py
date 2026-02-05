"""
REST API module for Model Dashboard.
Provides a simple API endpoint to list all models.
"""

import os
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model_dashboard.auth import validate_api_token, User

logger = logging.getLogger('model_dashboard.api')

# FastAPI app
app = FastAPI(
    title="Model Dashboard API",
    description="REST API for accessing model data",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Response models
class ModelInfo(BaseModel):
    """Model information."""
    name: str
    network_type: str
    description: str
    version: str
    enabled: bool
    alias: str
    create_date: str
    last_modified_date: str


class ModelsResponse(BaseModel):
    """Response containing list of models."""
    total: int
    models: List[ModelInfo]


# Database connection
def get_db():
    """Get database connection."""
    from model_dashboard.connection import ModelDB
    
    opts = {
        'username': os.getenv('MINIO_USERNAME', 'minioadmin'),
        'password': os.getenv('MINIO_PASSWORD', 'minioadmin'),
        'bucket': os.getenv('MINIO_BUCKET', 'argo-models'),
        'namespace': os.getenv('MINIO_NAMESPACE', 'model-dashboard'),
    }
    
    if os.getenv('MINIO_HOST'):
        opts['host'] = os.getenv('MINIO_HOST')
    if os.getenv('MINIO_PORT'):
        opts['port'] = int(os.getenv('MINIO_PORT'))
    
    return ModelDB(**opts)


# Authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Validate the API token and return the authenticated user."""
    token = credentials.credentials
    success, user, error = validate_api_token(token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Health check (no auth required)
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


# Models endpoint
@app.get("/api/v1/models", response_model=ModelsResponse, tags=["Models"])
async def list_models(
    current_user: User = Depends(get_current_user)
):
    """
    List all available models.
    
    Returns a list of all models with their details.
    Requires Bearer token authentication.
    """
    try:
        db = get_db()
        db.update_models()
        
        models = []
        for model in db.model_list:
            # Get version from inference_information
            version = ''
            if model.inference_information:
                version = model.inference_information.get('version', '')
            
            # Truncate description for display
            desc = str(model.description or '')
            if len(desc) > 200:
                desc = desc[:197] + '...'
            
            models.append(ModelInfo(
                name=model.name,
                network_type=str(model.network_type),
                description=desc,
                version=version,
                enabled=model.enabled or False,
                alias=model.alias or '',
                create_date=model.create_date or '',
                last_modified_date=model.last_modified_date or ''
            ))
        
        return ModelsResponse(
            total=len(models),
            models=models
        )
        
    except Exception as e:
        logger.error(f"Error retrieving models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving models: {str(e)}"
        )


def run_api():
    """Run the API server."""
    import uvicorn
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))
    reload = os.getenv('API_RELOAD', 'false').lower() == 'true'
    
    uvicorn.run(
        "model_dashboard.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_api()
