def check_logged_in(session):
    if 'logged_in' in session:
        if session['logged_in']:
            return True
    return False