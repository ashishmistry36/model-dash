"""
Database connection module for Model Dashboard.
Provides MinIO-based model storage and retrieval functionality.
"""

import streamlit as st

import json
import logging
from io import BytesIO
from minio import Minio
from streamlit.connections import BaseConnection
from typing import (
    Any,
    Dict,
    List,
    Union
)
from model_dashboard.models import (
    NetworkType,
    InferenceModel
)

logging.getLogger('httpx').setLevel(logging.WARNING)


class ModelDB:
    """
    Model database interface for MinIO storage.
    
    Provides CRUD operations for inference models stored in MinIO buckets.
    """
    
    def __init__(
        self,
        username: str,
        password: str,
        bucket: str = 'argo-models',
        namespace: str = 'inference',
        port: int = 9000,
        host: str = None
    ):
        """
        Initialize the model database connection.
        
        Args:
            username: MinIO access key
            password: MinIO secret key
            bucket: Bucket name for model storage
            namespace: Kubernetes namespace (used for default host)
            port: MinIO server port
            host: MinIO server hostname (optional, defaults to k8s service)
        """
        self._bucket = bucket
        self._models = {}
        self.log = logging.getLogger('ModelDB')
        
        if not host:
            host = f'argo-artifacts.{namespace}.svc.cluster.local'
        
        self.client = Minio(
            f'{host}:{port}',
            access_key=username,
            secret_key=password,
            secure=False,
            cert_check=False
        )

    @property
    def models(self) -> Dict[str, InferenceModel]:
        """Get dictionary of all models, loading if necessary."""
        if not self._models:
            self.update_models()
        return self._models
    
    @property
    def model_list(self) -> List[InferenceModel]:
        """Get sorted list of all models."""
        return sorted(self.models.values(), key=lambda x: (x.network_type, x.name))
    
    @property
    def names(self) -> List[str]:
        """Get list of all model names."""
        return [m.name for m in self.model_list]

    def get_objects(
        self,
        prefix: str = None,
        recursive: bool = True,
        include_dirs: bool = False,
        **kwargs
    ) -> List[Any]:
        """
        List objects in the bucket.
        
        Args:
            prefix: Filter by object prefix
            recursive: Include objects in subdirectories
            include_dirs: Include directory entries
            
        Returns:
            List of MinIO objects
        """
        objects = []
        for o in self.client.list_objects(
            self._bucket,
            prefix=prefix,
            recursive=recursive,
            **kwargs
        ):
            if not include_dirs and o.is_dir:
                continue
            objects.append(o)
        return objects
    
    def update_models(self) -> None:
        """Refresh the models cache from MinIO."""
        self._models = {}
        for o in self.get_objects():
            try:
                network_type, name = o.object_name.split('/')
                self._models[name] = self.get_model(name, network_type)
            except Exception:
                pass

    def object_exists(self, name: str) -> bool:
        """Check if an object exists in the bucket."""
        try:
            obj = self.client.stat_object(self._bucket, name)
            assert obj.size
            return True
        except Exception:
            return False

    def get_model(self, name: str, network_type: NetworkType) -> InferenceModel:
        """
        Retrieve a model from MinIO.
        
        Args:
            name: Model name
            network_type: Network architecture type
            
        Returns:
            InferenceModel instance or None if not found
        """
        model = None
        res = None
        path = f'{network_type}/{name}'
        
        try:
            assert self.object_exists(path), f'No model found named "{name}" (network_type: {network_type})'
            res = self.client.get_object(self._bucket, path)
            data = res.read()
            model = InferenceModel.load(data)
        except Exception as ex:
            self.log.error(f'Unable to get model "{name}": {ex}')
        finally:
            if res:
                res.close()
                res.release_conn()
        
        return model
    
    def add_model(
        self,
        model: Union[dict, InferenceModel],
        overwrite: bool = False
    ) -> bool:
        """
        Add a model to MinIO storage.
        
        Args:
            model: Model data (dict or InferenceModel)
            overwrite: Allow overwriting existing models
            
        Returns:
            True if successful
        """
        if isinstance(model, dict):
            m = InferenceModel(**model)
        else:
            m = model

        path = f'{m.network_type}/{m.name}'
        
        if not overwrite and self.object_exists(path):
            self.log.warning(f'Skipping upload: model already exists')
            return True
        
        self.log.info(f'Uploading model {m.name}...')
        data = m.to_bytes()

        res = self.client.put_object(
            self._bucket,
            path,
            BytesIO(data),
            len(data),
            metadata={
                'name': m.name,
                'network_type': str(m.network_type),
                'enabled': str(m.enabled).lower()
            }
        )
        
        txt = 'Successfully added model:'
        txt += f'\n  - Name: {res.object_name}'
        txt += f'\n  - Tag: {res.etag}'
        txt += f'\n  - Version: {res.version_id}'
        self.log.info(txt)
        
        self._models[m.name] = m
        return True
    
    def delete_model(self, name: str, network_type: NetworkType) -> bool:
        """
        Delete a model from MinIO storage.
        
        Args:
            name: Model name
            network_type: Network architecture type
            
        Returns:
            True if successful
        """
        path = f'{network_type}/{name}'
        
        try:
            self.client.remove_object(self._bucket, path)
            self.log.info(f'Deleted model: {path}')
            
            if name in self._models:
                del self._models[name]
            
            return True
        except Exception as ex:
            self.log.error(f'Unable to delete model "{name}": {ex}')
            return False


class MinioConnection(BaseConnection[ModelDB]):
    """
    Streamlit connection wrapper for ModelDB.
    
    Allows using st.connection() to manage the database connection.
    """
    
    def _connect(self, **kwargs) -> ModelDB:
        """Create the database connection."""
        import os
        
        # Start with defaults
        opts = {
            'username': 'argo',
            'password': '@rgo.password',
            'bucket': 'argo-models',
            'namespace': 'inference'
        }
        
        # Try to get config from secrets.toml (lowest priority)
        try:
            secrets_opts = {k: v for k, v in st.secrets.model_db.items()}
            opts.update(secrets_opts)
        except Exception:
            pass
        
        # Environment variables override secrets.toml (highest priority)
        if os.getenv('MINIO_USERNAME'):
            opts['username'] = os.getenv('MINIO_USERNAME')
        if os.getenv('MINIO_PASSWORD'):
            opts['password'] = os.getenv('MINIO_PASSWORD')
        if os.getenv('MINIO_BUCKET'):
            opts['bucket'] = os.getenv('MINIO_BUCKET')
        if os.getenv('MINIO_NAMESPACE'):
            opts['namespace'] = os.getenv('MINIO_NAMESPACE')
        if os.getenv('MINIO_HOST'):
            opts['host'] = os.getenv('MINIO_HOST')
        if os.getenv('MINIO_PORT'):
            opts['port'] = int(os.getenv('MINIO_PORT'))
        
        opts.update(kwargs)
        return ModelDB(**opts)