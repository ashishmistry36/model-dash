"""
API Tokens management page.
Allows users to create, view, and revoke API tokens for REST API access.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from model_dashboard.auth import (
    create_api_token,
    list_user_tokens,
    revoke_api_token,
    create_local_user
)
from model_dashboard.utils import get_pixel_height

if 'user' not in st.session_state or not st.session_state.user:
    st.switch_page('app.py')

user = st.session_state.user

# Page header
st.markdown("""
<style>
.token-card {
    background: linear-gradient(145deg, #1e3a5f 0%, #0d1f33 100%);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.token-display {
    font-family: 'Fira Code', 'Consolas', monospace;
    background: rgba(0, 0, 0, 0.3);
    padding: 1rem;
    border-radius: 8px;
    word-break: break-all;
    margin: 1rem 0;
}
.warning-box {
    background: rgba(255, 193, 7, 0.15);
    border: 1px solid rgba(255, 193, 7, 0.4);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

c1, c2 = st.columns([0.1, 0.9])
with c1:
    st.markdown("🔑")
with c2:
    st.header('API Tokens')

st.markdown('*Manage your API tokens for REST API access*')
st.divider()

# Create new token section
st.subheader('Create New Token')

with st.form("create_token_form"):
    description = st.text_input(
        "Description",
        placeholder="e.g., CI/CD pipeline, data science scripts",
        help="A descriptive name to help you identify this token"
    )
    
    submitted = st.form_submit_button("Generate Token", type="primary")
    
    if submitted:
        if user.auth_type == 'ldap':
            # For LDAP users, create a local account entry first if it doesn't exist
            from model_dashboard.auth import init_database, hash_password
            import sqlite3
            import secrets
            
            try:
                init_database()
                from model_dashboard.auth import DB_PATH
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT username FROM users WHERE username = ?', (user.username,))
                if not cursor.fetchone():
                    # Create user entry with random password (LDAP users won't use it)
                    random_pass = secrets.token_urlsafe(32)
                    cursor.execute('''
                        INSERT INTO users (username, password_hash, display_name, email)
                        VALUES (?, ?, ?, ?)
                    ''', (user.username, hash_password(random_pass), user.display_name, user.email))
                    conn.commit()
                conn.close()
            except Exception as e:
                st.error(f"Error setting up user for API tokens: {e}")
        
        success, token, message = create_api_token(user.username, description or "No description")
        
        if success:
            st.success("Token created successfully!", icon="✅")
            
            st.markdown("""
            <div class="warning-box">
                <strong>⚠️ Important:</strong> Copy this token now! You won't be able to see it again.
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="token-display">
                {token}
            </div>
            """, unsafe_allow_html=True)
            
            st.code(token, language=None)
            
            st.markdown("""
            **Usage Example:**
            ```bash
            curl -H "Authorization: Bearer YOUR_TOKEN" \\
                 https://your-server/api/v1/models
            ```
            """)
        else:
            st.error(f"Failed to create token: {message}", icon="🚫")

st.divider()

# List existing tokens
st.subheader('Your API Tokens')

tokens = list_user_tokens(user.username)

if not tokens:
    st.info("You don't have any API tokens yet. Create one above to get started.", icon="ℹ️")
else:
    # Convert to dataframe for display
    df_data = []
    for t in tokens:
        created = t['created_at'][:10] if t['created_at'] else 'N/A'
        expires = t['expires_at'][:10] if t['expires_at'] else 'Never'
        last_used = t['last_used_at'][:10] if t['last_used_at'] else 'Never'
        
        # Check if expired
        status = "Active"
        if t['expires_at']:
            try:
                exp_date = datetime.fromisoformat(t['expires_at'])
                if datetime.utcnow() > exp_date:
                    status = "Expired"
            except:
                pass
        
        df_data.append({
            'ID': t['id'],
            'Description': t['description'],
            'Created': created,
            'Expires': expires,
            'Last Used': last_used,
            'Status': status
        })
    
    df = pd.DataFrame(df_data)
    
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            'ID': st.column_config.NumberColumn('ID', width='small'),
            'Description': st.column_config.TextColumn('Description', width='medium'),
            'Created': st.column_config.TextColumn('Created', width='small'),
            'Expires': st.column_config.TextColumn('Expires', width='small'),
            'Last Used': st.column_config.TextColumn('Last Used', width='small'),
            'Status': st.column_config.TextColumn('Status', width='small')
        }
    )
    
    st.markdown("---")
    
    # Token revocation section
    st.subheader('Revoke Token')
    st.markdown("*To revoke a token, you'll need to provide the token value itself.*")
    
    with st.form("revoke_token_form"):
        token_to_revoke = st.text_input(
            "Token to Revoke",
            type="password",
            placeholder="Paste the token you want to revoke"
        )
        
        revoke_submitted = st.form_submit_button("Revoke Token", type="secondary")
        
        if revoke_submitted:
            if not token_to_revoke:
                st.warning("Please enter a token to revoke")
            else:
                success, message = revoke_api_token(token_to_revoke)
                if success:
                    st.success(message, icon="✅")
                    st.rerun()
                else:
                    st.error(message, icon="🚫")

st.divider()

# API Documentation
st.subheader('API Documentation')

with st.expander("📖 REST API Reference", expanded=False):
    st.markdown("""
    ### Available Endpoints
    
    All endpoints require authentication via Bearer token in the Authorization header.
    
    #### Health Check
    ```
    GET /health
    ```
    Returns API health status. Does not require authentication.
    
    #### List Models
    ```
    GET /api/v1/models
    GET /api/v1/models?network_type=nnUNet_v2
    GET /api/v1/models?enabled_only=true
    GET /api/v1/models?search=segmentation
    ```
    Returns a list of all models with optional filtering.
    
    #### Get Model Details
    ```
    GET /api/v1/models/{model_name}
    ```
    Returns detailed information about a specific model.
    
    #### List Models by Type
    ```
    GET /api/v1/models/type/{network_type}
    ```
    Returns all models of a specific network type.
    
    #### Get Models as DataFrame
    ```
    GET /api/v1/models/dataframe
    GET /api/v1/models/dataframe?format=csv
    GET /api/v1/models/dataframe?format=records
    ```
    Returns model data in a DataFrame-like format. Supports JSON, CSV, and records formats.
    
    #### List Network Types
    ```
    GET /api/v1/network-types
    ```
    Returns all available network types.
    
    #### Get Current User
    ```
    GET /api/v1/me
    ```
    Returns information about the authenticated user.
    
    ### Example Usage
    
    **Python:**
    ```python
    import requests
    
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    response = requests.get(
        "https://your-server/api/v1/models",
        headers=headers
    )
    models = response.json()
    ```
    
    **cURL:**
    ```bash
    curl -H "Authorization: Bearer YOUR_TOKEN" \\
         https://your-server/api/v1/models
    ```
    """)
