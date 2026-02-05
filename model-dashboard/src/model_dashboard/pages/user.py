"""
User profile page.
Displays information about the currently logged-in user.
"""

import streamlit as st
import pandas as pd
from model_dashboard.utils import get_pixel_height

if 'user' not in st.session_state or not st.session_state.user:
    st.switch_page('app.py')

user = st.session_state.user

# Page styling
st.markdown("""
<style>
.profile-header {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1.5rem;
    background: linear-gradient(145deg, #1e3a5f 0%, #0d1f33 100%);
    border-radius: 16px;
    margin-bottom: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.profile-info {
    flex: 1;
}
.profile-info h2 {
    margin: 0 0 0.5rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.profile-info p {
    margin: 0;
    color: #a0a0a0;
}
.auth-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
}
.auth-ldap {
    background: rgba(39, 174, 96, 0.2);
    color: #27ae60;
    border: 1px solid rgba(39, 174, 96, 0.4);
}
.auth-local {
    background: rgba(52, 152, 219, 0.2);
    color: #3498db;
    border: 1px solid rgba(52, 152, 219, 0.4);
}
</style>
""", unsafe_allow_html=True)

# Profile header
c1, c2, c3 = st.columns([0.15, 0.7, 0.15])
with c1:
    st.image(user.avatar, width=80)
with c2:
    st.header(user.display_name)
    auth_class = "auth-ldap" if user.auth_type == "ldap" else "auth-local"
    auth_label = "Network (LDAP)" if user.auth_type == "ldap" else "Local Account"
    st.markdown(f'<span class="auth-badge {auth_class}">{auth_label}</span>', unsafe_allow_html=True)
with c3:
    pass

st.divider()

# User details
st.subheader('Profile Information')

data = []
for k, v in user.items():
    if v is not None and str(v):
        # Format the key nicely
        label = k.replace('_', ' ').title()
        data.append({'Field': label, 'Value': str(v)})

if data:
    df = pd.DataFrame(data)
    height = get_pixel_height(len(data), max_lines=15)
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=height,
        column_config={
            'Field': st.column_config.TextColumn('Field', width='medium'),
            'Value': st.column_config.TextColumn('Value', width='large')
        }
    )

st.divider()

# Quick links
st.subheader('Quick Actions')

col1, col2, col3 = st.columns(3)

with col1:
    if st.button('🔑 Manage API Tokens', use_container_width=True):
        st.switch_page('pages/tokens.py')

with col2:
    if st.button('📊 View Models', use_container_width=True):
        st.switch_page('pages/models.py')

with col3:
    if st.button('📤 Upload Model', use_container_width=True):
        st.switch_page('pages/upload.py')

st.divider()

# Session info
with st.expander("🔐 Session Information", expanded=False):
    st.markdown(f"""
    - **Session Status:** Active
    - **Authentication Type:** {user.auth_type.upper()}
    - **Username:** {user.username}
    - **Groups:** {', '.join(user.groups) if user.groups else 'None'}
    """)
    
    if st.button('Sign Out', key='signout_expander'):
        from streamlit_cookies_controller import CookieController
        import os
        
        controller = CookieController()
        session_cookie_key = os.getenv('SESSION_COOKIE_KEY', 'model-dashboard-session')
        controller.remove(session_cookie_key)
        
        st.session_state.user = None
        st.session_state.logged_in = False
        st.rerun()
