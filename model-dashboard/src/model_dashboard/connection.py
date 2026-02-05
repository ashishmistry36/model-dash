import streamlit as st

import json
import logging
from io import BytesIO
from minio import Minio
from httpx import Client
from streamlit.connections import BaseConnection
from model_dashboard.utils import make_svg_avatar
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
    def __init__(self,username:str,password:str,bucket:str='argo-models',namespace:str='inference',port:int=9000,host:str=None):
        self._bucket = bucket
        self._models = {}
        self.log = logging.getLogger('ModelDB')
        if not host: host = f'argo-artifacts.{namespace}.svc.cluster.local'
        self.client = Minio(f'{host}:{port}',
            access_key=username,
            secret_key=password,
            secure=False,
            cert_check=False
        )

    @property
    def models(self) -> Dict[str,InferenceModel]:
        if not self._models: self.update_models()
        return self._models
    
    @property
    def model_list(self) -> List[InferenceModel]:
        return sorted(self.models.values(),key=lambda x: (x.network_type,x.name))
    
    @property
    def names(self) -> List[str]:
        return [m.name for m in self.model_list]

    def get_objects(self,prefix=None,recursive=True,include_dirs=False,**kwargs) -> List[Any]:
        objects = []
        for o in self.client.list_objects(self._bucket,prefix=prefix,recursive=recursive,**kwargs):
            if not include_dirs and o.is_dir: continue
            objects.append(o)
        return objects
    
    def update_models(self) -> None:
        self._models = {}
        for o in self.get_objects():
            try:
                network_type,name = o.object_name.split('/')
                self._models[name] = self.get_model(name,network_type)
            except: pass

    def object_exists(self,name:str) -> bool:
        try:
            obj = self.client.stat_object(self._bucket,name)
            assert obj.size
            return True
        except:
            return False

    def get_model(self,name:str,network_type:NetworkType) -> InferenceModel:
        model = None
        path = f'{network_type}/{name}'
        try:
            assert self.object_exists(path), f'No model found named "{name}" (network_type: {network_type})'
            res = self.client.get_object(self._bucket,path)
            data = res.read()
            model = InferenceModel.load(data)
        except Exception as ex:
            self.log.error(f'Unable to get model "{name}": {ex}')
        finally:
            if res:
                res.close()
                res.release_conn()
        return model
    
    def add_model(self,model:Union[dict,InferenceModel],overwrite:bool = False) -> bool:
        if isinstance(model,dict):
            m = InferenceModel(**model)
        else:
            m = model

        path = f'{m.network_type}/{m.name}'
        if not overwrite and self.object_exists(path):
            self.log.warning(f'Skipping upload: model already exists')
            return True
        
        self.log.info(f'Uploading model {m.name}...')
        data = m.to_bytes()

        res = self.client.put_object(self._bucket,path,BytesIO(data),len(data),
            metadata={
                'name':m.name,
                'network_type':str(m.network_type),
                'enabled':str(m.enabled).lower()
            }
        )
        txt = 'Successfully added model:'
        txt += f'\n  - Name: {res.object_name}'
        txt += f'\n  - Tag: {res.etag}'
        txt += f'\n  - Version: {res.version_id}'
        self.log.info(txt)
        self._models[m.name] = m
        return True

class MinioConnection(BaseConnection[ModelDB]):
    def _connect(self,**kwargs) -> ModelDB:
        opts = {k:v for k,v in st.secrets.model_db.items()}
        opts.update(kwargs)
        return ModelDB(**opts)

class GithubUser:
    def __init__(self,access_token,token_type='bearer',scope=''):
        self._token = access_token
        self._token_type = token_type.title()
        self._scope = scope
        self._info = {}
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'{self._token_type} {self._token}'
        }
        self.client = Client(headers=self.headers,base_url='https://github.mdanderson.org')
        self.connect()

    def __str__(self):
        return json.dumps(self._info,indent=2,default=lambda x:str(x))

    def __getattr__(self,key):
        return self._info.get(key,None)
    
    @property
    def username(self) -> str:
        return self._info.get('login','')
    
    def items(self):
        return self._info.items()

    def connect(self):
        res = self.client.get('/api/v3/user')
        res.raise_for_status()
        self._info = res.json()

        names = self._info['name'].split(',')
        fname = names.pop(-1)
        name = ' '.join([fname,*names])
        self._info['name'] = name
        self._info['avatar'] = make_svg_avatar(name,radius=32)