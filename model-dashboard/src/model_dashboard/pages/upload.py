import streamlit as st

import os
import json
import logging
from io import BytesIO
from tempfile import mkdtemp
from zipfile import ZipFile, ZIP_DEFLATED
from model_dashboard.models import NetworkType
from model_dashboard.utils import (
    get_pixel_height,
    validate_model_files
)
from datetime import datetime

todays_date = datetime.now().strftime("%-m/%-d/%y")

_NETWORK_TYPE_HELP = 'This is to validate the the files imported are in the proper format and that they are saved to the proper paths'

logger = logging.getLogger('model_dashboard.pages.upload')

if 'db' not in st.session_state or 'user' not in st.session_state or not st.session_state.user:
    st.switch_page('app.py')

if 'status_pct' not in st.session_state: st.session_state.status_pct = 0
for _x in ['tmp_dir','from_path','to_path','final_info']:
    if _x not in st.session_state: st.session_state[_x] = ''

st.header('Argo Model Upload')
st.markdown('*Follow the prompts to add a model to the database*')
st.divider()

status_bar = st.progress(0, text='Enter Model Name')

def update_status(pct:int,txt:str) -> None:
    st.session_state.status_pct = pct or 5
    status_bar.progress(st.session_state.status_pct, text=txt)

name = st.text_input('Name',placeholder='i.e. Task0001_SampleModelName',autocomplete='on')
network_type,nnunet_config,version,upload = ('','','',None)
if name: 
    opts = NetworkType.list()
    if name.startswith('Task'):
        opts = ['nnUNet','totalsegmentator','MIST']
    elif name.startswith('Dataset'):
        opts = ['nnUNet_v2','TotalSegmentatorV2','MIST']

    network_type = st.selectbox('Network Type',[None,*opts],help=_NETWORK_TYPE_HELP)
    update_status(20,'Choose Network Type')
    
if name and network_type:
    if network_type == 'nnUNet_v2':
        version = st.selectbox('Version',['2.0','2.4','2.5','2.6'])
        update_status(35,'Choose Version')
        
        if version:
            upload = st.file_uploader('Choose Files',accept_multiple_files=False,type='zip')
            update_status(50,'Upload a Zip File')
    elif network_type in ['nnUNet','totalsegmentator']: 
        nnunet_config = st.selectbox('nnUNet Configuration',['3d_fullres','3d_lowres','3d_cascade_fullres','2d'])
        update_status(35,'Choose an nnUNet Configuration')

        if nnunet_config:
            upload = st.file_uploader('Choose Files',accept_multiple_files=False,type='zip')
            update_status(50,'Upload a Zip File')
    else:
        upload = st.file_uploader('Choose Files',accept_multiple_files=False,type='zip')
        update_status(50,'Upload a Zip File')
elif name:
    update_status(20,'Choose Network Type')
else:
    update_status(0,'Enter Model Name')

if upload is not None:
    username = st.session_state.user.username
    logger.info(f'User {username} is attempting to upload a new model: {name} ({network_type})')

    # if not st.session_state.tmp_dir: 
    #     st.session_state.tmp_dir = f'/tmp/{network_type}/{name}'

    update_status(70,'Checking Files')

    tmp = f'/tmp/{network_type}/{name}'
    os.makedirs(tmp,exist_ok=True)

    if len(os.listdir(tmp)) == 0:
        with st.spinner('Extracting files...', show_time=True):
            z = ZipFile(BytesIO(upload.getvalue()),'r',ZIP_DEFLATED)
            z.extractall(tmp)
            
    if not st.session_state.final_info:
        with st.spinner('Validating files...', show_time=True):
            info, from_path, to_path, missing = validate_model_files(tmp,name=name,network_type=network_type,nnunet_config=nnunet_config)

            st.session_state.from_path = from_path
            st.session_state.to_path = to_path

        for f in missing:
            st.markdown(f':orange-badge[⚠️ Missing file] {f}')

        if info:
            update_status(90,'Validate Model Information')

            _info = json.dumps(info,indent=4)
            height = get_pixel_height(_info.count('\n'),max_lines=20)
            final_info = st.text_area('Validate Model Information',
                                        value=_info,
                                        height=height,
                                        key='final_info',
                                        help='Last chance to change/add anything before the model is stored in the database')
    else:
        update_status(95,'Validate Model Information')

        _info = st.session_state.final_info
        height = get_pixel_height(_info.count('\n'),max_lines=20)
        final_info = st.text_area('Validate Model Information',
                                    value=_info,
                                    height=height,
                                    key='final_info',
                                    help='Last chance to change/add anything before the model is stored in the database')
        
        if st.button('Submit'):
            to_path = st.session_state.to_path
            from_path = st.session_state.from_path

            info = json.loads(st.session_state.final_info)

            _info = {k:v for k,v in info.items()}
            _info['from_path'] = from_path
            _info['to_path'] = to_path
            _info = json.dumps(_info,indent=2)
            info["create_date"]=todays_date
            info["last_modified_date"]=todays_date
            info["inference_information"]["version"]=version

            logger.info(f'User {username} is adding a model to the database:\n{_info}')

            with st.spinner('Saving...', show_time=True):
                os.makedirs(os.path.dirname(to_path),exist_ok=True)
                os.system(f'mv {repr(from_path)} {repr(to_path)}')
                # if tmp: os.system(f'rm -rf {tmp}/*')

                try:
                    res = st.session_state.db._instance.add_model(info)
                    msg = f'Model {network_type}/{name} successfully uploaded'
                except Exception as ex:
                    res = False
                    msg = f'Unable to upload model {network_type}/{name}: {ex}'

            if res:
                logger.info(msg)
                st.success(msg, icon="✅")
                st.balloons()
            else:
                logger.error(msg)
                st.error(msg, icon="🚨")

            update_status(100,'Upload Complete')