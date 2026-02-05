"""
Model Dashboard - Inference Model Management System

A Streamlit-based dashboard for managing ML inference models
with LDAP/local authentication and REST API access.
"""

import os
import subprocess

__version__ = '2.0.0'


def main() -> None:
    """Start the Streamlit dashboard."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(
        'streamlit run app.py',
        shell=True,
        text=True,
        check=True,
        cwd=app_dir
    )


def run_api() -> None:
    """Start the REST API server."""
    import uvicorn
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))
    reload = os.getenv('API_RELOAD', 'false').lower() == 'true'
    
    uvicorn.run(
        'model_dashboard.api:app',
        host=host,
        port=port,
        reload=reload
    )


def run_both() -> None:
    """Start both the dashboard and API server in parallel."""
    import multiprocessing
    
    dashboard = multiprocessing.Process(target=main)
    api = multiprocessing.Process(target=run_api)
    
    dashboard.start()
    api.start()
    
    dashboard.join()
    api.join()
