"""
Model Dashboard Application
Main entry point for the Streamlit-based model management dashboard.
Uses LDAP authentication with AD group validation and local database fallback.
"""

import os
import sys
import logging
import streamlit as st
from streamlit_cookies_controller import CookieController

from model_dashboard.connection import MinioConnection
from model_dashboard.auth import (
    authenticate,
    User,
    make_svg_avatar
)

LOG_DIR = os.getenv('LOG_DIR', '/data/models/.logs')
LOG_FILE = os.path.join(LOG_DIR, 'model_dashboard.log')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='midnight', delay=True)
    ]
)

logger = logging.getLogger('model_dashboard.app')

st.set_page_config(
    page_title='Model Dashboard',
    layout='wide',
    page_icon='🧠'
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'db' not in st.session_state:
    st.session_state.db = st.connection('models', type=MinioConnection)
if 'login_error' not in st.session_state:
    st.session_state.login_error = ''

controller = CookieController()
session_cookie_key = os.getenv('SESSION_COOKIE_KEY', 'model-dashboard-session')


# Check for existing session
try:
    session_data = controller.get(session_cookie_key)
    if session_data and not st.session_state.logged_in:
        try:
            import json
            user_data = json.loads(session_data) if isinstance(session_data, str) else session_data
            st.session_state.user = User(
                username=user_data.get('username', ''),
                display_name=user_data.get('display_name', ''),
                email=user_data.get('email', ''),
                auth_type=user_data.get('auth_type', 'session'),
                groups=user_data.get('groups', [])
            )
            st.session_state.logged_in = True
            logger.info(f"Session restored for user: {st.session_state.user.username}")
        except Exception as e:
            logger.warning(f"Failed to restore session: {e}")
            try:
                controller.remove(session_cookie_key)
            except:
                pass
except TypeError:
    # Cookie controller not yet initialized, will be available on next rerun
    pass
except Exception as e:
    logger.debug(f"Cookie check error (expected on first load): {e}")


def login():
    """Render the login page with LDAP and local authentication options."""
    
    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .login-header p {
        color: #a0a0a0;
        font-size: 1rem;
    }
    .auth-info {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-header">
            <h1>🧠 Model Dashboard</h1>
            <p>Inference Model Management System</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="auth-info">
            <strong>🔐 Authentication Required</strong><br>
            Sign in with your network credentials (LDAP) or local account.
        </div>
        """, unsafe_allow_html=True)
        
        # Display any login errors
        if st.session_state.login_error:
            st.error(st.session_state.login_error, icon="🚫")
            st.session_state.login_error = ''
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_username",
                autocomplete="username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
                autocomplete="current-password"
            )
            
            auth_type = st.radio(
                "Authentication Type",
                options=["ldap", "local"],
                format_func=lambda x: "Network (LDAP)" if x == "ldap" else "Local Account",
                horizontal=True,
                key="login_auth_type"
            )
            
            submitted = st.form_submit_button("🔑 Sign In", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.session_state.login_error = "Please enter both username and password"
                    st.rerun()
                else:
                    with st.spinner("Authenticating..."):
                        success, user, error = authenticate(username, password, auth_type)
                    
                    if success and user:
                        # Store session in cookie
                        import json
                        session_data = json.dumps({
                            'username': user.username,
                            'display_name': user.display_name,
                            'email': user.email,
                            'auth_type': user.auth_type,
                            'groups': user.groups
                        })
                        controller.set(session_cookie_key, session_data)
                        
                        st.session_state.user = user
                        st.session_state.logged_in = True
                        
                        logger.info(f'Successfully logged in user: {user.username} (auth_type: {auth_type})')
                        st.rerun()
                    else:
                        st.session_state.login_error = error or "Authentication failed"
                        logger.warning(f'Failed login attempt for user: {username} - {error}')
                        st.rerun()
        
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.85rem;">
            <p>Need access? Contact your system administrator.</p>
            <p>Looking for the <a href="https://xnat.mdanderson.org/argo/workflows/inference" target="_blank">Workflows Dashboard</a>?</p>
        </div>
        """, unsafe_allow_html=True)


def logout():
    """Render the logout confirmation page."""
    
    st.markdown("""
    <style>
    .logout-container {
        max-width: 450px;
        margin: 3rem auto;
        padding: 2rem;
        text-align: center;
    }
    .logout-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="logout-icon">👋</div>', unsafe_allow_html=True)
        st.header('Sign Out')
        
        if st.session_state.user:
            st.markdown(f"**{st.session_state.user.display_name}** ({st.session_state.user.username})")
        
        st.markdown("Are you sure you want to sign out?")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button('Cancel', use_container_width=True):
                st.switch_page('pages/models.py')
        
        with col_b:
            if st.button('Sign Out', type='primary', use_container_width=True):
                username = st.session_state.user.username if st.session_state.user else 'unknown'
                logger.info(f'User logged out: {username}')
                
                controller.remove(session_cookie_key)
                st.session_state.user = None
                st.session_state.logged_in = False
                st.rerun()


# Page definitions
login_page = st.Page(login, title='Sign In', icon=':material/login:')
logout_page = st.Page(logout, title='Sign Out', icon=':material/logout:')

models = st.Page('pages/models.py', title='Dashboard', icon=':material/dashboard:', default=True)
upload = st.Page('pages/upload.py', title='Upload', icon=':material/upload_file:')
create = st.Page('pages/create.py', title='Create', icon=':material/post_add:')
user = st.Page('pages/user.py', title='Profile', icon=':material/account_circle:')
tokens = st.Page('pages/tokens.py', title='API Tokens', icon=':material/key:')

# Navigation setup
if st.session_state.logged_in and st.session_state.user:
    st.logo(st.session_state.user.avatar, size='large')
    pg = st.navigation(
        {
            'Account': [user, tokens, logout_page],
            'Models': [models, upload, create]
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()