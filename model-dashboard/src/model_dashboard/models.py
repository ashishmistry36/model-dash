import json
from enum import Enum
from pydantic import (
    Field,
    BaseModel,
    ConfigDict,
    model_validator
)
from typing import (
    Any,
    Dict,
    Union,
    Optional
)

class MinioModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    @classmethod
    def load(cls,obj:Any) -> Any:
        if isinstance(obj,cls): 
            return obj
        elif isinstance(obj,bytes):
            return cls.model_validate(json.loads(obj.decode('utf-8')))
        elif isinstance(obj,dict): 
            return cls.model_validate(obj)
        elif hasattr(obj,'model_dump'):
            return cls.model_validate(obj.model_dump())
        raise ValueError(f'Unable to convert object of type "{type(obj)}" to "{type(cls)}"')

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode('utf-8')

class NetworkType(str,Enum):
    nnUNet = 'nnUNet'
    nnUNet_v2 = 'nnUNet_v2'
    tensorflow = 'tensorflow'
    totalsegmentator = 'totalsegmentator'
    TotalSegmentatorV2 = 'TotalSegmentatorV2'
    MIST = 'MIST'
    vista3d = 'vista3d'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return self.value

class InferenceModel(MinioModel):
    name: str
    network_type: NetworkType
    enabled: Optional[bool] = Field(default=False)
    alias: Optional[str] = Field(default='')
    description: Optional[str] = Field(default='')
    contour_names: Optional[Dict[Union[int,str],Any]] = Field(default={})
    inference_information: Optional[Dict[str,Any]] = Field(default={})
    inference_args: Optional[str] = Field(default='')
    create_date: Optional[str] = Field(default='')
    last_modified_date: Optional[str] = Field(default='')
    version: Optional[str] = Field(default='')


    @model_validator(mode='after')
    def validate_fields(self) -> 'InferenceModel':
        if not self.alias: self.alias = f'{self.name}'
        if not self.inference_args:
            if 'inference_args' in self.inference_information:
                args = []
                for key,v in self.inference_information['inference_args'].items():
                    k = f'{key}' if key.startswith('-') else f'--{key}'
                    if isinstance(v, bool) and v:
                        args.append(k)
                    else:
                        args.append(f'{k} {v}')
                self.inference_args = ' ' + ' '.join(args)
        return self