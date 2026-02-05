import streamlit as st

import pandas as pd
from model_dashboard.utils import get_pixel_height

if 'user' not in st.session_state:
    st.switch_page('app.py')

c1,c2,c3 = st.columns(3)
with c1:
    c11,c12 = st.columns([0.15,0.85],vertical_alignment='bottom')
    with c11:
        st.image(st.session_state.user.avatar,width=40)
    with c12:
        st.header('User Info')
with c2:
    pass
with c3:
    pass

st.divider()

data = []
for k,v in st.session_state.user.items():
    if isinstance(v,dict):
        for kk,vv in v.items():
            if vv is not None and str(vv):
                data.append({'Parameter':f'{k}.{kk}','Value':str(vv)})
    elif v is not None and str(v):
        data.append({'Parameter':k,'Value':str(v)})

height = get_pixel_height(len(data),max_lines=15)
st.dataframe(pd.DataFrame(data),hide_index=True,use_container_width=True,height=height)
