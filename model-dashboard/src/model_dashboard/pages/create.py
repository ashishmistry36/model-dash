import streamlit as st

import json
import logging
from uuid import uuid4
from model_dashboard.utils import (
    format_error,
    get_pixel_height
)
from model_dashboard.models import (
    NetworkType,
    InferenceModel
)

logger = logging.getLogger('model_dashboard.pages.models')

if 'status_pct' not in st.session_state: st.session_state.status_pct = 0
if 'submitted' not in st.session_state: st.session_state.submitted = False

if 'db' not in st.session_state:
    st.switch_page('app.py')

db = st.session_state.db._instance
username = st.session_state.user.username

st.header('Create New Model Definition')
st.divider()

status_bar = st.progress(st.session_state.status_pct, text='Enter Model Name')

def update_status(pct:int,txt:str) -> None:
    st.session_state.status_pct = pct
    status_bar.progress(st.session_state.status_pct, text=txt)

def clear_input(key):
    st.session_state[key] = ''

name = st.text_input('Name',placeholder='i.e. Task0001_SampleModelName',autocomplete='on',key='create_name')
derived_from = st.selectbox('Derived From',
                            key='create_derived',
                            options=db.model_list,
                            index=None,
                            format_func=lambda x: f'{x.network_type} - {x.name}', 
                            help='If you making a customized version of an existing model, select the model here')

if name: 
    if derived_from:
        network_type = st.text_input('Network Type',value=derived_from.network_type,disabled=True,key='create_network')
    else:
        opts = NetworkType.list()
        if name.startswith('Task'):
            opts = ['nnUNet','totalsegmentator','MIST']
        elif name.startswith('Dataset'):
            opts = ['nnUNet_v2','TotalSegmentatorV2','MIST']
        network_type = st.selectbox('Network Type',opts,index=None)

    if network_type:
        update_status(75,f'Update Model Information') 

        fields = {
            'alias': name,
            'description': None,
            'contour_names': {'1':name},
            'inference_information': {},
            'inference_args': None
        }
        if derived_from: 
            df = derived_from.model_dump()
            fields.update({k:v for k,v in df.items() if k in fields})

        fields['contour_names'] = json.dumps(fields['contour_names'],indent=4)
        fields['inference_information'] = json.dumps(fields['inference_information'],indent=4)

        def get_height(value:str|None = None) -> int:
            v = value or ''
            n = max(v.count('\n'),10)
            return get_pixel_height(n,max_lines=15)

        alias = st.text_input('Alias',value=fields['alias'])
        description = st.text_area('Description',value=fields['description'],placeholder='Model description (optional)')
        contour_names = st.text_area('Contour Names',value=fields['contour_names'],height=get_height(fields['contour_names']),placeholder='Dictionary of contour name mappings (optional)')
        inference_information = st.text_area('Inference Information',value=fields['inference_information'],height=get_height(fields['inference_information']),placeholder='Dictionary with extra model information (optional)')
        inference_args = st.text_area('Inference Args',value=fields['inference_args'],placeholder='Arguments to pass to the inference job (optional)')
        overwrite = st.checkbox('Overwrite',value=False)

        def save():
            fields.update({
                'name': name,
                'network_type': network_type,
                'alias': alias or name,
                'description': description or f'{name} ({network_type})',
                'contour_names': json.loads(contour_names),
                'inference_information': json.loads(inference_information),
                'inference_args': inference_args or ''
            })

            logger.info(f'User {username} is adding a model to the database:\n{json.dumps(fields,indent=2)}')

            try:
                m = InferenceModel(**fields)
                db_path = f'{m.network_type}/{m.name}'
                if overwrite: assert not db.object_exists(db_path), f'Model already exists and overwrite is not set'
                assert db.add_model(m), 'Database error'
                res = True
                msg = 'Successfully added model to the database'
            except Exception as ex:
                res = False
                msg = format_error(f'Unable to add model to the database: {ex}')

            if res:
                logger.info(msg)
                st.success(msg, icon="✅")
                st.balloons()
            else:
                logger.error(msg)
                st.error(msg, icon="🚨")

            update_status(100,'Model Created')
            st.session_state.submitted = True

        def cancel():
            st.session_state.submitted = False
            st.session_state.status_pct = 0
            for x in ['create_name','create_network']:
                clear_input(x)
            st.session_state.create_derived = None

        c1,c2,c3 = st.columns([0.8,0.1,0.1])
        with c1:
            pass
        with c2:
            st.button('Reset',on_click=cancel,use_container_width=True)
        with c3:
            st.button('Submit',on_click=save,type='primary',use_container_width=True)
    else:
        update_status(50,'Choose Network Type')
else:
    update_status(25,'Enter Model Name')

