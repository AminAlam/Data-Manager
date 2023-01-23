import flask
from functools import wraps

def check_logged_in(session):
    if 'logged_in' in session:
        if session['logged_in']:
            return True
    return False

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' in flask.session:
            if flask.session['admin']:
                return f(*args, **kwargs)
            else:
                flask.flash('You need to login first.')
                return flask.redirect(flask.url_for('login'))
        else:
            flask.flash('You need to login first.')
            return flask.redirect(flask.url_for('login'))
    return wrap

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in flask.session:
            if flask.session['logged_in']:
                return f(*args, **kwargs)
            else:
                flask.flash('You need to login first.')
                return flask.redirect(flask.url_for('login'))
        else:
            flask.flash('You need to login first.')
            return flask.redirect(flask.url_for('login'))
    return wrap