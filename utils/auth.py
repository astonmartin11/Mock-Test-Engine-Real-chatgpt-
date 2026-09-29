from __future__ import annotations
import os
import streamlit as st
from database.repositories.users import UserRepository

def _oidc_identity():
    try:
        user = st.user
        if user and getattr(user, 'is_logged_in', False):
            return {
                'auth_provider': 'oidc',
                'auth_subject': str(user.get('sub') or user.get('email')),
                'email': user.get('email'),
                'display_name': user.get('name') or user.get('email'),
            }
    except Exception:
        pass
    return None

def current_user():
    identity = _oidc_identity()
    if identity is None:
        if os.getenv('ALLOW_DEV_AUTH', 'true').lower() != 'true':
            st.error('Authentication is not configured.')
            st.stop()
        identity = {
            'auth_provider': 'dev',
            'auth_subject': os.getenv('DEV_AUTH_SUBJECT', 'dev-user'),
            'email': os.getenv('DEV_AUTH_EMAIL', 'developer@example.com'),
            'display_name': os.getenv('DEV_AUTH_NAME', 'Developer'),
        }
    return UserRepository().create(**identity)
