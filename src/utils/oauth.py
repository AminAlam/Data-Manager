import os
import json
import requests
from flask import redirect, url_for, current_app
import flask
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_oauth(app):
    """Setup OAuth integration with the Flask app"""
    oauth = OAuth(app)
    
    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url=os.getenv('GOOGLE_DISCOVERY_URL'),
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    return oauth

def get_google_user_info(token):
    """Get Google user information from access token"""
    resp = requests.get(
        'https://www.googleapis.com/oauth2/v3/userinfo',
        headers={'Authorization': f'Bearer {token}'}
    )
    if resp.status_code == 200:
        return resp.json()
    return None

def get_user_email_from_google_info(user_info):
    """Extract email from Google user info"""
    if user_info and 'email' in user_info:
        return user_info['email']
    return None

def login_user_with_google(db_conn, user_email):
    """Login user with Google email if exists in the database"""
    from src.database import operators
    
    # Get user by email
    user = operators.get_user_by_email(db_conn, user_email)
    if not user:
        return False
    
    # Set session variables - using flask.session
    flask.session.clear()
    flask.session['username'] = user['username'] 
    flask.session['logged_in'] = True
    flask.session['admin'] = user['admin']
    
    return True 