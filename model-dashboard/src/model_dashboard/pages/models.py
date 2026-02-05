import streamlit as st

import json
import logging
import pandas as pd
from uuid import uuid4
from model_dashboard.models import InferenceModel
from model_dashboard.utils import get_pixel_height

logger = logging.getLogger('model_dashboard.pages.models')

if 'dfk' not in st.session_state: st.session_state.dfk = str(uuid4())

st.header('Current Models')
st.markdown(f'*Select a model to edit it by clicking the checkbox next to it in the leftmost column*')
st.divider()

if 'db' not in st.session_state:
    st.switch_page('app.py')
else:
    db = st.session_state.db._instance
    username = st.session_state.user.username
    
    models = []
    for k,v in db.models.items():
        desc = str(v.description or '')
        create_date=v.create_date
        last_modified_date=v.last_modified_date
        inf_info = v.inference_information
        version = inf_info["version"]
        while len(desc) > 75:
            desc = ' '.join(desc.split(' ')[:-1]) + '...'
        models.append({
            'Name': k,
            'Network Type': v.network_type,
            'Description': desc,
            'Version': version,
            'create_date':create_date,
            'last_modified_date':last_modified_date
        })
    models = sorted(models,key=lambda x: (x['Network Type'],x['Name']))

    df = pd.DataFrame(models)

    event = st.dataframe(
        df,
        key=st.session_state.dfk,
        hide_index=True,
        use_container_width=True,
        on_select='rerun',
        selection_mode='single-row'
    )

    if event.selection.rows:
        st.divider()

        row_id = event.selection.rows[0]
        name = df.iloc[row_id]['Name']

        m = db.models[name].model_dump()

        st.subheader(name)

        def format_val(key,val):
            if key not in m: 
                return val
            elif isinstance(m[key],(list,dict)): 
                return json.loads(val)
            return m[key].__class__(val)

        def update(key:str):
            logger.info(f'{username} changed {name}.{key}: {st.session_state[key]}')

        fields = {}
        for k,v in m.items():
            if isinstance(v,bool):
                fields[k] = st.checkbox(k,value=v,key=k,on_change=update,args=(k,))
            elif isinstance(v,(list,dict)):
                _v = json.dumps(v,indent=4)
                height = get_pixel_height(_v.count('\n'),max_lines=15)
                fields[k] = st.text_area(k,value=_v,key=k,height=height,on_change=update,args=(k,))
            else:
                fields[k] = st.text_input(k,value=v,key=k,on_change=update,args=(k,))
        
        def save():
            updated_model = {}
            for k in fields:
                new_val = format_val(k,st.session_state[k])
                if m[k] != new_val:
                    updated_model[k] = new_val

            if updated_model:
                _updates = json.dumps(updated_model,indent=2,default=lambda x: str(x))
                logger.info(f'{username} updated model {name}:\n{_updates}')

                updated_model.update({k:v for k,v in m.items() if k not in updated_model})
                model = InferenceModel(**updated_model)
                m_type = model.network_type
                res = db.add_model(model=model,overwrite=True)
                if res:
                    logger.info(f'Model {m_type}/{name} successfully updated')
                    st.toast(f'Model {m_type}/{name} successfully updated', icon="✅")
                    st.balloons()
                    m.update(model.model_dump())
                else:
                    logger.error('Model update failed. Check logs for more information.')
                    st.toast('ERROR: Model update failed. Check logs for more information.', icon="🚨")
            else:
                st.toast('No model parameters were changed. Skipping model update.')

        def cancel():
            st.session_state.dfk = str(uuid4())

        c1,c2,c3 = st.columns([0.8,0.1,0.1])
        with c1:
            pass
        with c2:
            st.button('Cancel',on_click=cancel,use_container_width=True)
        with c3:
            st.button('Save',on_click=save,type='primary',use_container_width=True)