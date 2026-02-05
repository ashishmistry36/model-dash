import os
import sys
import logging
import streamlit as st
from streamlit_oauth import OAuth2Component
from streamlit_cookies_controller import CookieController
from model_dashboard.connection import (
    GithubUser,
    MinioConnection
)

LOG_DIR = os.getenv('LOG_DIR','/data/models/.logs')
LOG_FILE = os.path.join(LOG_DIR,'model_dashboard.log')
os.makedirs(LOG_DIR,exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stderr),
                        logging.handlers.TimedRotatingFileHandler(LOG_FILE,when='midnight',delay=True)
                    ])

logger = logging.getLogger('model_dashboard.app')

st.set_page_config(page_title='Model Dashboard',layout='wide')

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'token' not in st.session_state: st.session_state.token = ''
if 'user' not in st.session_state: st.session_state.user = None
if 'db' not in st.session_state: st.session_state.db = st.connection('models',type=MinioConnection)

oauth2 = OAuth2Component(**st.secrets['github'])

controller = CookieController()
oauth_cookie_key = os.getenv('OAUTH_COOKIE_KEY','model-dashboard-oath-token')

user_auth = controller.get(oauth_cookie_key)
if user_auth:
    try:
        user = GithubUser(user_auth)
        st.session_state.user = user
        st.session_state.token = {'access_token':user_auth,'token_type':'bearer','scope':''}
        st.session_state.logged_in = True
    except: pass

def login():
    c1,c2,c3 = st.columns(3)

    with c1:
        pass 

    with c2:
        st.header('Log in')

        st.markdown('''         
This app uses GitHub SSO for authorization. Press the `authorize` button below if you agree to log in.

If you are looking for the Workflows Dashboard, you can find it [here](https://xnat.mdanderson.org/argo/workflows/inference).

---
''')

        callback_url = os.getenv('CALLBACK_URL','https://xnat.mdanderson.org/argo-models/component/streamlit_oauth.authorize_button')
        if not callback_url.endswith('/index.html'): callback_url = f'{callback_url}/index.html'
        result = oauth2.authorize_button('Authorize',callback_url,'')

    with c3:
        pass
    
    if result and 'token' in result:
        controller.set(oauth_cookie_key,result['token']['access_token'])
        st.session_state.user = GithubUser(**result['token'])
        st.session_state.token = result['token']
        st.session_state.logged_in = True

        logger.info(f'Successfully logging in user: {st.session_state.user.username}')
        st.rerun()

def logout():
    st.header('Log Out')

    if st.button('Confirm'):
        controller.remove(oauth_cookie_key)
        st.session_state.user = None
        st.session_state.token = ''
        st.session_state.logged_in = False
        st.rerun()

login_page = st.Page(login, title='Log in', icon=':material/login:')
logout_page = st.Page(logout, title='Log out', icon=':material/logout:')

models = st.Page('pages/models.py', title='Dashboard', icon=':material/dashboard:', default=True)
upload = st.Page('pages/upload.py', title='Upload', icon=':material/upload_file:')
create = st.Page('pages/create.py', title='Create', icon=':material/post_add:')
user = st.Page('pages/user.py', title='User', icon=':material/account_circle:')

if st.session_state.logged_in and st.session_state.token:
    st.logo(st.session_state.user.avatar,size='large')
    pg = st.navigation(
        {
            'Account': [user,logout_page],
            'Models': [models, upload, create]
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()