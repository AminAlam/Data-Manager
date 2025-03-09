import sys
import pathlib
import os
parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
sys.path.append(os.path.join(parent_parent_path, 'utils'))
sys.path.append(os.path.join(parent_parent_path, 'database'))

import chatroom
import utils
import security
import search_engine
import operators
import mailing
from dictianory import slef_made_codes, slef_made_codes_inv_map
import flask
from threading import Thread
from markupsafe import Markup

import datetime as dt
from flask_sessionstore import Session
from flask_sqlalchemy import SQLAlchemy

from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
import flaskcode

from functools import wraps

import waitress

from datetime import datetime

from llm_search import ExternalLLMSearch, execute_llm_search

import requests
import secrets


def add_admin(db_configs, app_configs):
    conn = db_configs.conn
    cursor = conn.cursor()
    cursor.execute('select * from users where username=?', ('admin',))
    users = cursor.fetchall()
    if len(users)==0:
        cursor.execute('insert into users values (?,?,?,?,?,?,?,?)', ('admin', 'admin', 1, 1, None, None, 1, None))
        conn.commit()
        utils.init_user(app_configs, db_configs, 'admin')

class WebApp():
    def __init__(self, db_configs, ip, port, static_folder, recaptcha_bool, num_threads, mailing_bool, host_url): 
        self.ip = ip
        self.port = port
        self.num_threads = num_threads
        self.db_configs = db_configs
        self.mailing_bool = mailing_bool
        self.host_url = host_url
        self.app = flask.Flask(__name__, static_folder=static_folder)
        self.parent_path = str(pathlib.Path(__file__).parent.absolute())
        self.parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
        self.app.config['RECAPTCHA_ENABLED'] = recaptcha_bool
        self.app.config['DATABASE_FOLDER'] = os.path.join(self.parent_parent_path ,'database')
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.parent_parent_path ,'database' ,'uploaded_files')
        self.app.config['FAMILY_TREE_FOLDER'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'family_tree')
        self.app.config['CONDITIONS_JSON_FOLDER'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions')
        self.app.config['CONDITIONS_JSON'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions', 'default.json')
        self.app.config['CONDITIONS_JSON_DEFAULT'] = 'default.json'
        self.app.config['TEMPLATES_FOLDER'] = os.path.join(self.parent_parent_path, 'web', 'templates')
        
        self.app.config['CREDS_FILE'] = utils.load_creds()
        self.app.config['SECRET_KEY'] = self.app.config['CREDS_FILE']['SECRET_KEY']
        self.app.config['RECAPTCHA_PUBLIC_KEY'] = self.app.config['CREDS_FILE']['RECAPTCHA_PUBLIC_KEY']
        self.app.config['RECAPTCHA_PRIVATE_KEY'] = self.app.config['CREDS_FILE']['RECAPTCHA_PRIVATE_KEY']

        self.app.config.from_object(flaskcode.default_config)
        self.app.config['FLASKCODE_RESOURCE_BASEPATH'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions')
        self.app.register_blueprint(flaskcode.blueprint, url_prefix='/editor')

        self.ChatRoom = chatroom.ChatRoom(self.db_configs)

        add_admin(self.db_configs, self.app.config)
        
        # Initialize LLM search with API key from environment variables
        testing_mode = self.app.config.get('TESTING', False)
        self.llm_search = ExternalLLMSearch(testing_mode=testing_mode)
        if self.llm_search.ready:
            print("Claude API service initialized successfully.")
        else:
            print("WARNING: Claude API key not set. Set the CLAUDE_API_KEY environment variable.")

        # Import and run database migrations
        from database.migrate import migrate_database
        migrate_database()

        print(f'App initialized. Server running on http://{self.ip}:{self.port}')
    
    class RecaptchaForm(FlaskForm):
        username = StringField("username", validators=[DataRequired()])
        password = PasswordField("password", validators=[DataRequired()])
        recaptcha = RecaptchaField()
    
    
    def logger(self, f):
        @wraps(f)
        def wrap(*args, **kwargs):
            time_now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Convert to string format
            conn = self.db_configs.conn
            cursor = conn.cursor()
            try:
                action = f.__name__
                # Check if user is logged in before accessing username
                username = flask.session.get('username', 'anonymous')
                cursor.execute('insert into logs values (?,?,?,?,?,?)', (username, action, time_now, 'pass', None, None))
                conn.commit()
                return f(*args, **kwargs)
            except Exception as e:
                # Use the username from above or default to 'anonymous' if not set
                username = flask.session.get('username', 'anonymous')
                try:
                    cursor.execute('update logs set status=?, error=? where username=? and action=? and date=?', 
                                ('fail', str(e), username, action, time_now))
                    conn.commit()
                except Exception as db_error:
                    print(f"Error updating logs: {db_error}")
                print(e)
                flask.flash('An error occurred. Please try again later.')
                return flask.redirect(flask.url_for('index'))
        return wrap

    def run(self):
        app = self.app

        @app.route('/login', methods=['GET', 'POST'])
        @self.logger
        def login():
            if flask.request.method == 'POST':
                username = flask.request.form['username']
                password = flask.request.form['password']
                conn = self.db_configs.conn
                cursor = conn.cursor()
                cursor.execute('select * from users where username=?', (username,))
                users = cursor.fetchall()

                form = self.RecaptchaForm()
                if len(users)==0:
                    return flask.render_template('login.html', error='Invalid username or password', form=form)
                elif form.validate_on_submit() or not app.config['RECAPTCHA_ENABLED']:
                    if len(users) > 0:
                        stored_password = users[0][1]
                        if security.verify_password(stored_password, password):
                            flask.session['username'] = username
                            flask.session['logged_in'] = True
                            flask.session['admin'] = users[0][2]
                            return flask.redirect(flask.url_for('index'))
                        else:
                            error = 'Invalid Credentials. Please try again.'
                    else:
                        error = 'Invalid Credentials. Please try again.'
                    return flask.render_template('login.html', error=error, form=form)
                else:
                    form = self.RecaptchaForm()
                    return flask.render_template('login.html', error='Invalid Captcha', form=form)

            else:
                form = self.RecaptchaForm()
                return flask.render_template('login.html', form=form)

        @app.route('/', methods=['GET', 'POST'])
        @security.login_required
        def index():
            if not flask.session.get('logged_in'):
                return flask.redirect(flask.url_for('login'))
            entries_list = search_engine.entries_time_line(self.db_configs.conn)
            
            # Convert entries from tuples to dictionaries with named keys
            entries_dict_list = []
            for entry in entries_list:
                entries_dict_list.append({
                    'hash_id': entry[0],
                    'tags': entry[1],
                    'author': entry[5],
                    'date': entry[4],
                    'conditions': entry[6],
                    'title': entry[7],
                    'id': entry[9]
                })
            
            entries_html = flask.render_template('entries_list.html', entries_list=entries_dict_list)
            entries_html = Markup(entries_html)
            return flask.render_template('index.html', entries_html=entries_html)

        @app.route('/logout')
        @security.login_required
        def logout():
            flask.session.pop('logged_in', None)
            flask.session.pop('username', None)
            flask.session.pop('password', None)
            flask.session.pop('admin', None)
            return flask.redirect(flask.url_for('login'))

        @app.route('/add_user', methods=['GET', 'POST'])
        @security.admin_required
        def add_user():
            return flask.render_template('add_user.html')

        @app.route('/add_user_to_db', methods=['GET', 'POST'])
        @security.admin_required
        @self.logger
        def add_user_to_db():
            username = flask.request.form['username']
            password = flask.request.form['password']
            repeat_password = flask.request.form['repeat_password']
            admin = flask.request.form['admin']
            name = flask.request.form['name']
            email = flask.request.form['email']
            order_manager = flask.request.form['order_manager']

            if username == '' or password == '' or admin == '':
                flask.flash('Please fill all the fields')
                return flask.render_template('add_user.html')

            if password != repeat_password:
                flask.flash('Passwords do not match')
                return flask.render_template('add_user.html')

            conn = self.db_configs.conn
            cursor = conn.cursor()
            cursor.execute('select * from users where username=?', (username,))
            users = cursor.fetchall()

            if len(users)>0:
                flask.flash('Username already exists')
                return flask.render_template('add_user.html')

            success = operators.add_user(conn=conn, username=username, password=password, admin=admin, order_manager=order_manager, name=name, email=email)
            if success:
                utils.init_user(app.config, self.db_configs, username)
                flask.flash('User added successfully')
                return flask.redirect(flask.url_for('index'))
            else:
                flask.flash('Error adding user')
                return flask.render_template('add_user.html')
    
        @app.route("/update_user_in_db/<int:id>", methods=['POST', 'GET'])
        @security.login_required
        # @self.logger
        def update_user_in_db(id):
            if flask.request.method == 'POST':
                form_data = {
                    'name': flask.request.form['name'],
                    'email': flask.request.form['email'],
                    'email_enabled': flask.request.form['email_enabled']
                }
                if 'password' in flask.request.form and flask.request.form['password']:
                    form_data['password'] = flask.request.form['password']
                if flask.session['admin']:
                    form_data['admin'] = int(flask.request.form['admin'])
                    form_data['order_manager'] = int(flask.request.form['order_manager'])
                    
                # Validate password if it exists
                if 'password' in form_data and form_data['password'] != flask.request.form['repeat_password']:
                    flask.flash('Passwords do not match')
                    return flask.redirect(flask.url_for('profile'))
                
                success = operators.update_user(self.db_configs.conn, form_data, id)
                if success:
                    flask.flash('User updated successfully')
                    return flask.redirect(flask.url_for('user_management'))
                else:
                    flask.flash('Error updating user')
                    return flask.redirect(flask.url_for('user_management'))

        @app.route("/delete_user/<int:id>", methods=['POST', 'GET'])
        @security.admin_required
        @self.logger
        def delete_user(id):
            success = operators.delete_user(self.db_configs.conn, id)
            
            if success:
                flask.flash('User deleted successfully')
            else:
                flask.flash('Error deleting user')
                
            return flask.redirect(flask.url_for('user_management'))
        
        @app.route('/user_management', methods=['GET', 'POST'])
        @security.admin_required
        def user_management():
            users = operators.get_users(self.db_configs.conn)

            users_html = [flask.render_template('user_profile_template.html', user=user) for user in users]
            users_html = [Markup(user_html) for user_html in users_html]

            return flask.render_template('user_management.html', users_html=users_html, users=users)

        @app.route('/entries', methods=['GET', 'POST'])
        @security.login_required
        def entries():
            # We no longer need conditions for search as per requirements
            tomorrow_date = (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_date = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")

            dates = [yesterday_date, tomorrow_date]

            if flask.request.method == 'POST' and len(flask.request.form):
                entries_list = search_engine.filter_entries(self.db_configs.conn, flask.request.form)
                
                # Store the full results in session for pagination
                entries_dict_list = []
                for entry in entries_list:
                    entries_dict_list.append({
                        'hash_id': entry[0],
                        'tags': entry[1],
                        'author': entry[5],
                        'date': entry[4],
                        'conditions': entry[6],
                        'title': entry[7],
                        'id': entry[-1]
                    })
                
                # Store the full results in session
                flask.session['search_results'] = entries_dict_list
                
                # Only display the first 10 results
                display_entries = entries_dict_list[:10]
                show_more_button = len(entries_dict_list) > 10
                
                entries_html = flask.render_template('entries_list.html', entries_list=display_entries)
                entries_html = Markup(entries_html)
                return flask.render_template('entries.html', entries_html=entries_html, 
                                            dates=dates, show_more_button=show_more_button)
            else:
                return flask.render_template('entries.html', entries_html=None, dates=dates)

        @app.route('/load_more_entries', methods=['GET'])
        @security.login_required
        def load_more_entries():
            # Get the offset from the request
            offset = int(flask.request.args.get('offset', 0))
            limit = 10  # Number of entries to load each time
            
            # Get the stored search results
            all_entries = flask.session.get('search_results', [])
            
            # Get the next batch of entries
            next_entries = all_entries[offset:offset+limit]
            
            # Check if there are more entries to load
            has_more = len(all_entries) > offset + limit
            
            # Return the entries as JSON
            return flask.jsonify({
                'entries': next_entries,
                'has_more': has_more,
                'next_offset': offset + limit if has_more else -1
            })

        @app.route('/insert_entry', methods=('GET', 'POST'))
        @security.login_required
        def insert_entry():
            conditions_list = utils.list_user_conditoins_templates(self.db_configs.conn, self.app.config, flask.session)
            methods_list = utils.get_methods_list(self.app.config)
            today_date = dt.datetime.now().strftime("%Y-%m-%d")
            return flask.render_template('insert_entry.html', conditions_list=conditions_list, today_date=today_date, methods_list=methods_list)

        @app.route('/insert_entry_to_db', methods=['GET', 'POST'])
        @security.login_required
        @self.logger
        def insert_entry_to_db():
            if flask.request.method == 'POST':
                try:
                    print(flask.request.form)
                    Author = flask.session['username']
                    date = flask.request.form.get('date', dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    Tags = flask.request.form.get('Tags', '')
                    File_Path = flask.request.form.get('File_Path', '')
                    Notes = flask.request.form.get('Notes', '')
                    
                    # Handle both 'Files' (multiple) and 'file' (single) parameters for tests
                    if 'Files' in flask.request.files:
                        Files = flask.request.files.getlist('Files')
                    elif 'file' in flask.request.files:
                        Files = [flask.request.files['file']]
                    else:
                        Files = []
                        
                    entry_name = flask.request.form.get('entry_name', '')
                    parent_entry = flask.request.form.get('parent_entry', '')

                except Exception as e:
                    flask.flash(f'Error processing form: {str(e)}')
                    return flask.redirect(flask.url_for('insert_entry'))

                if not utils.check_hash_id_existence(self.db_configs.conn, parent_entry) and parent_entry != '':
                    flask.flash('Parent entry does not exist')
                    return flask.redirect(flask.url_for('insert_entry'))

                if Author == '' or entry_name == '':
                    flask.flash('Please fill all required fields')
                    return flask.redirect(flask.url_for('insert_entry'))

                conditions = flask.request.form.get('conditions', '')
                if not conditions:
                    conditions_list = []
                    for form_input in flask.request.form:
                        if 'condition' == form_input.split('&')[0]:
                            conditions_list.append('&'.join(form_input.split('&')[1:]))
                        elif 'PARAM' == form_input.split('&')[0]:
                            list_tmp = form_input.split('&')[2:]
                            list_tmp.append(flask.request.form[f"PARAMVALUE&{'&'.join(form_input.split('&')[1:])}"].split('&')[-1])
                            list_tmp = '&'.join(list_tmp)
                            conditions_list.append(list_tmp)
                    conditions = ','.join(conditions_list)
                
                success_bool, hash_id = operators.insert_entry_to_db(conn=self.db_configs.conn, Author=Author, date=date, Tags=Tags, File_Path=File_Path, Notes=Notes, conditions=conditions, entry_name=entry_name, parent_entry=parent_entry)
                
                if hash_id and Files:
                    utils.upload_files(self.app.config, hash_id, Files)

                if success_bool:
                    message = Markup(f'Entry is added successfully! hash_id: {hash_id}')
                else:
                    message = 'Something went wrong'

                flask.flash(message)
                

                return flask.redirect(flask.url_for('index', session=flask.session))

        @app.route("/author_search", methods=["POST", "GET"])
        @security.login_required
        def author_search():
            searchbox = flask.request.form.get('search_term', flask.request.form.get('text', ''))

            return search_engine.author_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/tags_search", methods=["POST", "GET"])
        @security.login_required
        def tags_search():
            searchbox = flask.request.form.get('search_term', flask.request.form.get('text', ''))
            return search_engine.tags_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/text_search", methods=["POST", "GET"])
        @security.login_required
        def text_search():
            searchbox = flask.request.form.get('search_term', flask.request.form.get('text', ''))
            return search_engine.text_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/entry/<int:id>", methods=["POST", "GET"])
        @security.login_required
        def entry(id):
            entry = operators.get_entry_by_id(self.db_configs.conn, id)
            
            if not entry:
                flask.flash('Entry not found')
                return flask.redirect(flask.url_for('index'))
            print(entry)
            target_conditions = entry['conditions']
            entry['conditions'] = utils.parse_conditions(entry['conditions'])
            for i in range(len(entry['conditions'])):
                if len(entry['conditions'][i].split('&')) ==3:
                    entry['conditions'][i] = entry['conditions'][i].split('&')[-1]
                else:
                    entry['conditions'][i] = '->'.join(entry['conditions'][i].split('&')[-2:])
            hash_id = entry['id_hash']
            dirName = os.path.join(app.config['UPLOAD_FOLDER'], hash_id)
            List = os.listdir(dirName)

            # family_tree_html = utils.family_tree_to_html(self.db_configs.conn, hash_id, self.app.config['FAMILY_TREE_FOLDER'])
            # family_tree_html = Markup(family_tree_html)
            family_tree_html = None

            for count, filename in enumerate(List):
                List[count] = [os.path.join(app.config['UPLOAD_FOLDER'], hash_id, filename), f"{slef_made_codes_inv_map['remove']}&{filename}", filename]

            Files = List
            conditions = utils.read_json_file(self.app.config['CONDITIONS_JSON'])
            conditions = utils.modify_conditions_json(conditions, target_conditions)
            conditions_html = flask.render_template('conditions.html', conditions=conditions)
            conditions_html = Markup(conditions_html)
            return flask.render_template('entry.html', entry=entry, Files=Files, conditions_html=conditions_html)

        @app.route("/entry_by_hash_id/<string:hash_id>", methods=["POST", "GET"])
        @security.login_required
        def entry_by_hash_id(hash_id):
            id = operators.get_id_by_hash_id(self.db_configs.conn, hash_id)
            if id is None:
                flask.flash('Entry not found')
                return flask.redirect(flask.url_for('index'))
            return flask.redirect(flask.url_for('entry', id=id))

        @app.route("/entry/<int:id>/update_entry", methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def update_entry(id):
            try:
                post_form = flask.request.form
                entry = utils.get_entry_by_id(self.db_configs.conn, id)
                
                if not entry:
                    flask.flash('Entry not found')
                    return flask.redirect(flask.url_for('index'))
                
                author = entry[5]
                usename = flask.session['username']
                admin = flask.session['admin']
                if author != usename and not admin:
                    flask.flash('You are not allowed to edit this entry')
                    return flask.redirect(flask.url_for('entry', id=id))

                # get hash_id from id
                hash_id = operators.get_hash_id_by_entry_id(self.db_configs.conn, id)
                
                if not hash_id:
                    flask.flash('Entry hash ID not found')
                    return flask.redirect(flask.url_for('index'))

                # Check parent entry if provided
                parent_entry = post_form.get('parent_entry', '')
                if parent_entry and not operators.check_hash_id_existence(self.db_configs.conn, parent_entry):
                    flask.flash('Parent entry does not exist')
                    return flask.redirect(flask.url_for('entry', id=id))

                # Update title if provided
                if 'entry_name' in post_form and post_form['entry_name'] != entry[7]:
                    cursor = self.db_configs.conn.cursor()
                    cursor.execute("UPDATE entries SET entry_name=? WHERE id=?", (post_form['entry_name'], id))
                    self.db_configs.conn.commit()

                # Get files from request
                files = flask.request.files.getlist('Files')
                
                # Debug file uploads
                app.logger.info(f"Files in request: {len(files)}")
                for file in files:
                    if file and file.filename:
                        app.logger.info(f"File: {file.filename}")
                
                # Create a mutable copy of the form data
                mutable_post_form = dict(post_form)
                
                # Ensure entry_name is set (use title if available)
                if 'entry_name' not in mutable_post_form:
                    mutable_post_form['entry_name'] = mutable_post_form['title']
                else:
                    mutable_post_form['entry_name'] = entry[7]  # Use existing entry name
                
                # Update the entry
                success_bool = operators.update_entry_in_db(
                    self.db_configs.conn, 
                    id, 
                    mutable_post_form, 
                    app.config, 
                    hash_id, 
                    files
                )

                if success_bool:
                    message = 'Entry updated successfully'
                else:
                    message = 'Something went wrong during the update'

                flask.flash(message)
                return flask.redirect(flask.url_for('entry', id=id))
                
            except Exception as e:
                app.logger.error(f"Error updating entry: {str(e)}")
                flask.flash(f'Error updating entry: {str(e)}')
                return flask.redirect(flask.url_for('entry', id=id))

        @app.route("/entry/<int:id>/delete_entry", methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def delete_entry(id):
            entry = utils.get_entry_by_id(self.db_configs.conn, id)
            author = entry[5]
            author = entry[5]
            usename = flask.session['username']
            admin = flask.session['admin']
            if author != usename and not admin:
                flask.flash('You are not allowed to delete this entry')
                return flask.redirect(flask.url_for('entry', id=id))

            success_bool = operators.delete_entry_from_db(self.db_configs.conn, id)

            if success_bool:
                message = 'entry is deleted successfully'

            else:
                message = 'Something went wrong'

            flask.flash(message)
            return flask.redirect(flask.url_for('index'))
        
        @app.route("/protocols", methods=["POST", "GET"])
        @security.login_required
        def protocols():
            # list all files in the protocols folder
            dirName = os.path.join(app.config['DATABASE_FOLDER'], 'protocols')
            List = os.listdir(dirName)

            for count, filename in enumerate(List):
                List[count] = filename

            protocols_file_list = List
            return flask.render_template('protocols.html', Files=protocols_file_list)

        @app.route("/conditions_templates", methods=["POST", "GET"])
        @security.login_required
        def conditions_templates():
            conditions_list = utils.list_user_conditoins_templates(self.db_configs.conn, self.app.config, flask.session)
            return flask.render_template('user_condition_templates.html', conditions_list=conditions_list)

        @app.route("/update_conditions_templates_in_db", methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def update_conditions_templates_in_db():
            post_form = flask.request.form

            success_bool = operators.update_conditions_templates(self.db_configs.conn, post_form, flask.session['username'])

            if success_bool:
                message = 'Conditions template is updated successfully'
            else:
                message = 'Something went wrong'

            flask.flash(message)
            return flask.redirect(flask.url_for('conditions_templates'))

        @app.route("/profile", methods=["POST", "GET"])
        @security.login_required
        def profile():
            username = flask.session['username']
            user = operators.get_user_by_username(self.db_configs.conn, username)
            
            if not user:
                flask.flash('User not found')
                return flask.redirect(flask.url_for('index'))
                
            user_html = flask.render_template('user_profile_template.html', user=user)
            user_html = Markup(user_html)
            return flask.render_template('profile.html', user_html=user_html)

        @app.route("/<path:filename>")
        def static_dir(filename):
            allowed_files = [os.path.join('static', 'js', 'JavaScript.js'), 
                             os.path.join('static', 'css', 'style.css'), 
                             os.path.join('static', 'css', 'bootstrap.min.css'),
                             os.path.join('static', 'assets', 'loading.gif'),
                             os.path.join('static', 'js', 'orders.js'),
                             os.path.join('static', 'js', 'chatbot.js'),
                             os.path.join('static', 'css', 'chatbot.css'),
                             os.path.join('static', 'js', 'table_sorting.js'),
                             os.path.join('static', 'js', 'entries_list.js')]
            
            if filename in allowed_files:
                return flask.send_from_directory(app.root_path, filename)
            else:
                return flask.redirect(flask.url_for('login'))

        @app.route('/send_entry_file/<int:entry_id>/<path:path>')
        @security.login_required
        def send_entry_file(entry_id, path):
            if '/' not in path:
                cwd = os.getcwd()
                cwd = os.path.join(cwd, app.config['UPLOAD_FOLDER'])
                hash_id = utils.get_hash_id_by_entry_id(self.db_configs.conn, entry_id)
                path = os.path.join(hash_id, path)
                return flask.send_from_directory(cwd, path, as_attachment=True)

        @app.route('/send_protocol_file/<path:path>')
        @security.login_required
        def send_protocol_file(path):
            if '/' not in path:
                cwd = os.getcwd()
                cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'protocols')
                return flask.send_from_directory(cwd, path, as_attachment=True)

        @app.route('/get_conditoin_by_templatename_methodname', methods=["POST", "GET"])
        @security.login_required
        def get_conditoin_by_templatename_methodname():

            username = flask.session['username']
            template_name = flask.request.form.get("template_name")
            method_name = flask.request.form.get("method_name")
            condition_html = utils.get_conditions_by_template_and_method(self.db_configs.conn, app.config, username, template_name, method_name)
            return condition_html

        @app.route('/entry_report_maker/<int:id>', methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def entry_report_maker(id):
                report_bytes = utils.bulk_entry_report_maker(self.db_configs.conn, [id])
                return flask.send_file(report_bytes, as_attachment=True, download_name='entry_report.csv')

        @app.route('/entries_actions', methods=['POST'])
        @security.login_required
        # @self.logger
        def entries_actions():
            post_form = flask.request.form
            action = post_form.get('action')
            
            # Get selected entries
            entries_ids = []
            for key in post_form:
                if key.startswith('Select&'):
                    entries_ids.append(int(key.split('&')[1]))
            
            if not entries_ids:
                flask.flash('No entries selected')
                return flask.redirect(flask.url_for('entries'))
            
            if action == 'delete':
                # Process delete action
                for id in entries_ids:
                    utils.delete_entry(self.db_configs.conn, id)
                flask.flash(f'Deleted {len(entries_ids)} entries')
                return flask.redirect(flask.url_for('entries'))
            if action == 'bulk_report':
                # Process bulk report action
                report_bytes = utils.bulk_entry_report_maker(self.db_configs.conn, entries_ids)
                return flask.send_file(report_bytes, as_attachment=True, download_name='bulk_entry_report.csv')
                    
            
            elif action == "notify_by_email":
                if not self.mailing_bool:
                    flask.flash('Email notifications are not enabled on this server')
                    return flask.redirect(flask.url_for('entries'))

                user_names = post_form['adress_for_notify_by_email']
                if not user_names:
                    flask.flash('No recipients specified')
                    return flask.redirect(flask.url_for('entries'))
                    
                # Process email notifications
                email_addresses = []
                user_list = []  # Keep track of usernames for notifications
                for user_name in user_names.split(','):
                    user_name = user_name.strip()
                    if user_name:
                        email = operators.get_email_address_by_user_name(self.db_configs.conn, user_name)
                        if email:
                            email_addresses.append(email)
                            user_list.append(user_name)

                if not utils.check_emails_validity(email_addresses):
                    flask.flash('No valid email addresses found for the specified users')
                    return flask.redirect(flask.url_for('entries'))

                success_count = 0
                for id in entries_ids:
                    entry_report = utils.entry_report_maker(self.db_configs.conn, id)
                    host_url = self.host_url
                    link2entry = f"{host_url}/entry/{id}"
                    sender_email_address = self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS']
                    sender_username = flask.session['username']
                    
                    # Get entry name for notification
                    cursor = self.db_configs.conn.cursor()
                    cursor.execute("SELECT entry_name FROM entries WHERE id=?", (id,))
                    entry_name = cursor.fetchone()[0]
                    
                    for idx, receiver_email_address in enumerate(email_addresses):
                        args = {
                            'receiver_email': receiver_email_address, 
                            'sender_email': sender_email_address, 
                            'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'], 
                            'subject': f'Entry report notification (by {sender_username})',
                            'txt': entry_report,
                            'link2entry': link2entry,
                            'sender_username': sender_username
                        }
                        if mailing.send_report_mail(args):
                            success_count += 1
                            # Create notification for the user
                        operators.add_notification(
                            self.db_configs.conn,
                            sender_username,
                            f"Entry '{entry_name}' has been shared with you",
                            user_list[idx],
                            'entry_share',
                            id
                            )
                
                if success_count > 0:
                    flask.flash(f'Successfully sent {success_count} email notifications')
                else:
                    flask.flash('Failed to send email notifications')
                
                # Add this return statement to fix the error
                return flask.redirect(flask.url_for('entries'))
            
            elif action == "set_parent_entry":
                parent_entry_hash_id = post_form.get('parent_entry_hash_id')
                if not operators.check_hash_id_existence(self.db_configs.conn, parent_entry_hash_id):
                    flask.flash('Parent entry does not exist')
                    return flask.redirect(flask.url_for('entries'))
                for id in entries_ids:
                    operators.set_parent_entry(self.db_configs.conn, id, parent_entry_hash_id)
                flask.flash('Parent entry set successfully')
                return flask.redirect(flask.url_for('entries'))
            
            # Default fallback
            flask.flash('Unknown action')
            return flask.redirect(flask.url_for('entries'))

        @app.route('/chatroom', methods=["GET", "POST"])
        @security.login_required
        def chatroom():
            messages = self.ChatRoom.get_messages()
            users = utils.get_users(self.db_configs.conn)
            users.insert(0, {'username': 'Group Chat'})
            for i, user in enumerate(users):
                if user['username'] == flask.session['username']:
                    users.insert(1, users.pop(i))
                    break
            return flask.render_template('chat_room.html', messages=messages, users=users)

        @app.route('/chatroom_send_message/<string:destination>', methods=["GET", "POST"])
        @security.login_required
        @self.logger
        def chatroom_send_message(destination):
            message = flask.request.form.get('message')
            username = flask.session['username']
            time_now = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            message = {'author': username, 'message': message, 'date_time':time_now, 'destination': destination}
            self.ChatRoom.add_message(message)
            return flask.redirect(flask.url_for('chatroom'))

        @app.route('/chatroom_delete_message/<int:id>', methods=["GET", "POST"])
        @security.login_required
        @self.logger
        def chatroom_delete_message(id):
            self.ChatRoom.delete_message(id)
            return flask.redirect(flask.url_for('chatroom'))

        @app.route('/logs', methods=["GET", "POST"])
        @security.admin_required
        def logs():
            logs = operators.get_recent_logs(self.db_configs.conn, 7)
            return flask.render_template('logs.html', logs=logs)

        @app.route('/backup', methods=["GET", "POST"])
        @security.admin_required
        @self.logger
        def backup():
            if flask.request.method == 'POST':
                status, backup_file_path = utils.backup_db(self.app.config)
                if status:
                    return flask.send_from_directory(os.path.dirname(backup_file_path), os.path.basename(backup_file_path), as_attachment=True)
                else:
                    flask.flash('Database was not backed up successfully')
                    return flask.render_template('backup.html')
            else:
                return flask.render_template('backup.html')

        @app.route('/restore_db', methods=["GET", "POST"])
        @security.admin_required
        @self.logger
        def restore_db():
            if flask.request.method == 'POST':
                Files = flask.request.files.getlist('Files')
                file = Files[0]
                if file.filename.split('.')[-1] != 'zip':
                    flask.flash('Wrong file format / No file was selected')
                    return flask.render_template('backup.html')
                else:
                    backup_file_path = os.path.join(app.config['DATABASE_FOLDER'], 'backup.zip')
                    file.save(backup_file_path)
                    status = utils.restore_db(self.app.config, backup_file_path)
                    if status:
                        flask.flash('Database was restored successfully. Please restart the server')                        
                    else:
                        flask.flash('Database was not restored. Please try again')
                    return flask.render_template('backup.html')
                
        @app.route('/editor/', methods=["GET", "POST"])
        @security.admin_required
        @self.logger
        def editor():
            return flask.url_for('editor')

        @app.route('/orders', methods=['GET'])
        @security.login_required
        def orders():
            # Get filter parameters
            search_term = flask.request.args.get('search', '')
            author_term = flask.request.args.get('author', '')
            status_filter = flask.request.args.get('status', '')
            date_start = flask.request.args.get('date_start', '')
            date_end = flask.request.args.get('date_end', '')
            format_type = flask.request.args.get('format', '')
            
            # Build the query
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND order_name LIKE ?"
                params.append(f'%{search_term}%')
            
            if author_term:
                # Split author terms by comma and create OR conditions
                author_terms = [term.strip() for term in author_term.split(',') if term.strip()]
                if author_terms:
                    author_conditions = []
                    for term in author_terms:
                        author_conditions.append("order_author LIKE ?")
                        params.append(f'%{term}%')
                    query += f" AND ({' OR '.join(author_conditions)})"
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            if date_start:
                query += " AND date >= ?"
                params.append(date_start)
            
            if date_end:
                query += " AND date <= ?"
                # Add 23:59:59 to include the entire end day
                params.append(f"{date_end} 23:59:59")
            
            # Add ordering
            query += " ORDER BY date DESC LIMIT 10"
            
            # Execute the query
            cursor = self.db_configs.conn.cursor()
            cursor.execute(query, tuple(params))
            orders = cursor.fetchall()
            
            # Convert to dict with column names
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            orders = [dict(zip(columns, order)) for order in orders]
            
            # If JSON format is requested, return JSON response
            if format_type == 'json':
                return flask.jsonify({'orders': orders})
            
            # Get order managers for the dropdown
            cursor.execute("SELECT username FROM users WHERE order_manager = 1")
            order_managers = cursor.fetchall()
            order_managers = [{'username': manager[0]} for manager in order_managers]
            # Render the template
            return flask.render_template('orders.html', orders=orders, order_managers=order_managers)

        @app.route('/load_more_orders', methods=['GET'])
        @security.login_required
        def load_more_orders():
            offset = int(flask.request.args.get('offset', 0))
            search_term = flask.request.args.get('search', '')
            author_term = flask.request.args.get('author', '')
            status_filter = flask.request.args.get('status', '')
            date_start = flask.request.args.get('date_start', '')
            date_end = flask.request.args.get('date_end', '')
            
            # Build the query
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND order_name LIKE ?"
                params.append(f'%{search_term}%')
            
            if author_term:
                # Split author terms by comma and create OR conditions
                author_terms = [term.strip() for term in author_term.split(',') if term.strip()]
                if author_terms:
                    author_conditions = []
                    for term in author_terms:
                        author_conditions.append("order_author LIKE ?")
                        params.append(f'%{term}%')
                    query += f" AND ({' OR '.join(author_conditions)})"
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            if date_start:
                query += " AND date >= ?"
                params.append(date_start)
            
            if date_end:
                query += " AND date <= ?"
                # Add 23:59:59 to include the entire end day
                params.append(f"{date_end} 23:59:59")
            
            # Add ordering and pagination
            query += " ORDER BY date DESC LIMIT 10 OFFSET ?"
            params.append(offset)
            
            # Execute the query
            cursor = self.db_configs.conn.cursor()
            cursor.execute(query, tuple(params))
            orders = cursor.fetchall()
            
            # Convert to dict with column names
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            orders = [dict(zip(columns, order)) for order in orders]
            
            return flask.jsonify({'success': True, 'orders': orders})

        @app.route('/submit_order', methods=['POST'])
        @security.login_required
        @self.logger
        def submit_order():
            try:
                order_data = {
                    'order_name': flask.request.form.get('order_name'),
                    'link': flask.request.form.get('link', ''),
                    'quantity': flask.request.form.get('quantity', 1),
                    'note': flask.request.form.get('note', ''),
                    'order_assignee': flask.request.form.get('order_assignee'),
                    'order_author': flask.session['username'],
                    'status': 'pending',
                    'date': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                success, order_id = operators.submit_order(self.db_configs.conn, order_data)
                if success:
                    # Add notification for the assignee
                    operators.add_notification(
                        self.db_configs.conn,
                        flask.session['username'],
                        f"New order assigned: {order_data['order_name']}",
                        order_data['order_assignee'],
                        'order',
                        order_id
                    )

                    # check if the assignee email_enabled is true
                    cursor = self.db_configs.conn.cursor()
                    cursor.execute("SELECT email_enabled, email FROM users WHERE username=?", (order_data['order_assignee'],)) 
                    email_enabled, email = cursor.fetchone()
                    if email_enabled:
                        mail_args = {
                            'receiver_email': email,
                            'sender_email': self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS'],
                            'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'],
                            'subject': f"New order assigned: {order_data['order_name']}",
                        }
                        mailing.send_new_order_mail(order_data, mail_args)
                        flask.flash('Order submitted successfully and email sent to the assignee')
                    else:
                        flask.flash('Order submitted successfully')

                    return flask.redirect(flask.url_for('orders'))
                else:
                    flask.flash('Failed to submit order')
                    return flask.redirect(flask.url_for('orders'))
            except Exception as e:
                flask.flash(f'Failed to submit order: {str(e)}')
                return flask.redirect(flask.url_for('orders'))

        @app.route('/update_order_status', methods=['POST'])
        @security.login_required
        # @self.logger
        def update_order_status():
            # try:
                # Get data from request
                order_id = flask.request.form.get('order_id')
                new_status = flask.request.form.get('status')
                
                # Validate inputs
                if not order_id or not new_status:
                    return flask.jsonify({'success': False, 'message': 'Missing required parameters'})
                
                # Convert order_id to integer
                try:
                    order_id = int(order_id)
                except ValueError:
                    return flask.jsonify({'success': False, 'message': 'Invalid order ID'})
                
                # Validate status value
                valid_statuses = ['pending', 'ordered', 'rejected']
                if new_status.lower() not in valid_statuses:
                    return flask.jsonify({'success': False, 'message': 'Invalid status value'})
                
                # Get the order from the database
                cursor = self.db_configs.conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                order = cursor.fetchone()
                if not order:
                    return flask.jsonify({'success': False, 'message': 'Order not found'})

                # Convert to dict with column names
                cursor.execute("PRAGMA table_info(orders)")
                columns = [column[1] for column in cursor.fetchall()]
                order_dict = dict(zip(columns, order))

                # Check if user is authorized to update this order
                if not (flask.session['admin'] or flask.session['username'] == order_dict['order_author']):
                    return flask.jsonify({'success': False, 'message': 'Unauthorized'})

                # Update the order in the database
                cursor.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
                self.db_configs.conn.commit()

                # get the updated order
                cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                order = cursor.fetchone()
                column_names = operators.get_column_names(self.db_configs.conn, 'orders')
                order_dict = dict(zip(column_names, order))

                # Send email notification to order assignee
                if self.mailing_bool:
                    cursor.execute("SELECT email, email_enabled FROM users WHERE username=?", (order_dict['order_assignee'],))
                    assignee_email, assignee_email_enabled = cursor.fetchone()
                    if assignee_email_enabled:
                        mail_args = {
                            'receiver_email': assignee_email,
                            'sender_email': self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS'],
                            'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'],
                            'subject': f'Order Status Updated: {order_dict["order_name"]}',
                        }
                        mailing.send_order_status_mail(order_dict, mail_args)

                # Add notification
                operators.add_notification(
                    self.db_configs.conn,
                    flask.session['username'],
                    f"Order '{order_dict['order_name']}' status updated to {new_status}",
                    order_dict['order_author'],
                    'order_status',
                    order_id
                )

                return flask.jsonify({'success': True})

        @app.route('/get_order_details/<int:order_id>')
        @security.login_required
        def get_order_details(order_id):
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            order = cursor.fetchone()
            
            if not order:
                return flask.jsonify({'error': 'Order not found'}), 404
        
            # Convert to dict with column names
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            order_dict = dict(zip(columns, order))
            
            return flask.jsonify(order_dict)

        @app.route('/update_order', methods=['POST'])
        @security.login_required
        @self.logger
        def update_order():
            try:
                # Get data from request
                order_id = flask.request.form.get('order_id')
                order_name = flask.request.form.get('order_name')
                link = flask.request.form.get('link')
                quantity = flask.request.form.get('quantity')
                note = flask.request.form.get('note')
                order_assignee = flask.request.form.get('order_assignee')

                try:
                    order_id = int(order_id)
                    quantity = int(quantity)
                except ValueError:
                    return flask.jsonify({'success': False, 'message': 'Invalid order ID or quantity'})

                # check of order assignee has changed from the original assignee
                cursor = self.db_configs.conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                order = cursor.fetchone()
                cursor.execute("PRAGMA table_info(orders)")
                columns = [column[1] for column in cursor.fetchall()]
                order_dict = dict(zip(columns, order))
                
                if order_dict['order_assignee'] != order_assignee:
                    
                    # get email of the new assignee
                    cursor.execute("SELECT email, email_enabled FROM users WHERE username=?", (order_assignee,))
                    assignee_email, assignee_email_enabled = cursor.fetchone()
                    if assignee_email_enabled:
                        mail_args = {
                            'receiver_email': assignee_email,
                            'sender_email': self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS'],
                            'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'],
                            'subject': f'Order assigned to you: {order_name}',
                        }
                        mailing.send_new_order_mail(order_dict, mail_args)



                # Validate inputs
                if not order_id or not order_name or not quantity or not order_assignee:
                    return flask.jsonify({'success': False, 'message': 'Missing required parameters'})
                
                # Get the order from the database
                cursor = self.db_configs.conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                order = cursor.fetchone()
                
                if not order:
                    return flask.jsonify({'success': False, 'message': 'Order not found'})
                
                # Convert to dict with column names
                cursor.execute("PRAGMA table_info(orders)")
                columns = [column[1] for column in cursor.fetchall()]
                order_dict = dict(zip(columns, order))
                
                # Check if user is authorized to update this order
                if not (flask.session['admin'] or flask.session['username'] == order_dict['order_author']):
                    return flask.jsonify({'success': False, 'message': 'Unauthorized'})
                
                # Update the order in the database
                cursor.execute("""
                    UPDATE orders 
                    SET order_name=?, link=?, quantity=?, note=?, order_assignee=?
                    WHERE id=?
                """, (order_name, link, quantity, note, order_assignee, order_id))
                self.db_configs.conn.commit()
                
                # Return success response
                return flask.jsonify({'success': True})
            except Exception as e:
                # Log the error
                print(f"Error updating order: {str(e)}")
                return flask.jsonify({'success': False, 'message': str(e)})

        @app.route('/delete_order', methods=['POST'])
        @security.login_required
        @self.logger
        def delete_order():
            try:
                # Get data from request
                order_id = flask.request.form.get('order_id')
                
                # Validate inputs
                if not order_id:
                    return flask.jsonify({'success': False, 'message': 'Missing order ID'})
                
                # Convert order_id to integer
                try:
                    order_id = int(order_id)
                except ValueError:
                    return flask.jsonify({'success': False, 'message': 'Invalid order ID'})
                
                # Get the order from the database
                cursor = self.db_configs.conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                order = cursor.fetchone()
                
                if not order:
                    return flask.jsonify({'success': False, 'message': 'Order not found'})
                
                # Convert to dict with column names
                cursor.execute("PRAGMA table_info(orders)")
                columns = [column[1] for column in cursor.fetchall()]
                order_dict = dict(zip(columns, order))
                
                # Check if user is authorized to delete this order
                if not (flask.session['admin'] or flask.session['username'] == order_dict['order_author']):
                    return flask.jsonify({'success': False, 'message': 'Unauthorized'})
                
                # Delete the order from the database
                cursor.execute("DELETE FROM orders WHERE id=?", (order_id,))
                self.db_configs.conn.commit()
                
                # Return success response
                return flask.jsonify({'success': True})
            except Exception as e:
                # Log the error
                print(f"Error deleting order: {str(e)}")
                return flask.jsonify({'success': False, 'message': str(e)})

        @app.route('/notify_by_email/<int:id>', methods=["GET"])
        @security.login_required
        @self.logger
        def notify_by_email(id):
            if not self.mailing_bool:
                flask.flash('Email notifications are not enabled on this server')
                return flask.redirect(flask.url_for('entry', id=id))
            
            try:
                # Get entry details
                entry = utils.get_entry_by_id(self.db_configs.conn, id)
                if not entry:
                    flask.flash('Entry not found')
                    return flask.redirect(flask.url_for('index'))
                
                # Get user email
                cursor = self.db_configs.conn.cursor()
                cursor.execute("SELECT email FROM users WHERE username=?", (flask.session['username'],))
                user_email = cursor.fetchone()[0]
                
                if not user_email:
                    flask.flash('Your email is not set in your profile')
                    return flask.redirect(flask.url_for('entry', id=id))
                
                # Create entry report
                entry_report = utils.entry_report_maker(self.db_configs.conn, id)
                
                # Send email
                mail_args = {
                    'receiver_email': user_email,
                    'sender_email': self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS'],
                    'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'],
                    'subject': f'Entry Report: {entry[7]}',
                    'txt': f"""<p>Here is the report for entry {entry[0]}</p>
                        <pre>{entry_report}</pre>""",
                    'link2entry': f"{self.host_url}/entry/{id}",
                    'sender_username': 'System'
                }
                
                success = mailing.send_entry_report_mail(mail_args)
                
                if success:
                    flask.flash('Entry report has been sent to your email')
                else:
                    flask.flash('Failed to send email. Please try again later.')
                
                # Add notification
                operators.add_notification(
                    self.db_configs.conn,
                    flask.session['username'],
                    f"New entry shared with you: {entry[7]}",
                    entry[4],
                    'entry_share',
                    id
                )
                
                return flask.redirect(flask.url_for('entry', id=id))
            
            except Exception as e:
                flask.flash(f'Error sending email: {str(e)}')
                return flask.redirect(flask.url_for('entry', id=id))

        @app.route("/username_search", methods=["POST", "GET"])
        @security.login_required
        def username_search():
            search_text = flask.request.form.get('text', '')
            if not search_text:
                return flask.jsonify([])
            
            # Search for usernames that match the search text
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 10", [f'%{search_text}%'])
            users = cursor.fetchall()
            
            return flask.jsonify(users)

        @app.route("/title_search", methods=["POST", "GET"])
        @security.login_required
        def title_search():
            searchbox = flask.request.form.get("text")
            return search_engine.title_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/llm_search", methods=["POST"])
        @security.login_required
        def llm_search():
            """
            Handle LLM-based search requests from the chat interface
            """
            # First check if LLM is ready
            if not hasattr(self, 'llm_search') or not self.llm_search.ready:
                return flask.jsonify({
                    "success": False,
                    "message": "The nimA assistant is not available. The model failed to load due to system constraints."
                })
            
            try:
                user_query = flask.request.json.get("query", "")
                
                if not user_query.strip():
                    return flask.jsonify({
                        "success": False,
                        "message": "Please provide a search query or ask me how to use the software."
                    })
                
                # Use a simplified approach without threading
                try:
                    # Extract search parameters using LLM with a timeout
                    import time
                    start_time = time.time()
                    search_params = self.llm_search.extract_search_params(user_query)
                    print(f"LLM processing took {time.time() - start_time:.2f} seconds")
                    
                    if not search_params:
                        return flask.jsonify({
                            "success": False,
                            "message": "**I couldn't understand your query.**\n\nI'm designed to help with software usage and searching for entries. Could you please rephrase your question?"
                        })
                        
                    # Execute the search based on the parameters
                    entries_list = execute_llm_search(self.db_configs.conn, search_params)
                    
                    # Check if this is a usage question rather than a search
                    if search_params.get("is_usage_question"):
                        return flask.jsonify({
                            "success": True,
                            "entries": [],
                            "message": search_params.get("explanation", "I'll help you with using the software.")
                        })
                    
                    # Convert entries from tuples to dictionaries with named keys
                    entries_dict_list = []
                    for entry in entries_list:
                        entries_dict_list.append({
                            'hash_id': entry[0],
                            'tags': entry[1],
                            'author': entry[4],
                            'date': entry[5],
                            'conditions': entry[6],
                            'title': entry[7],
                            'id': entry[-1]
                        })
                    
                    return flask.jsonify({
                        "success": True,
                        "entries": entries_dict_list,
                        "message": search_params.get("explanation", "**Here are the search results** based on your query.")
                    })
                    
                except Exception as e:
                    print(f"Error in LLM processing: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return flask.jsonify({
                        "success": False,
                        "message": f"**There was a problem processing your request:**\n\n{str(e)}\n\nPlease try again with a different query."
                    })
                
            except Exception as e:
                print(f"Error in LLM search route: {str(e)}")
                return flask.jsonify({
                    "success": False,
                    "message": "An error occurred. Please try again with a simpler query."
                })

        @app.route("/llm_status", methods=["GET"])
        @security.login_required
        def llm_status():
            """
            Check if the LLM model is loaded and ready
            """
            return flask.jsonify({
                "ready": self.llm_search.ready
            })

        @app.route('/notifications')
        @security.login_required
        def notifications():
            limit = 10  # Initial number of notifications to show
            cursor = self.db_configs.conn.cursor()
            cursor.execute("""
                SELECT id, author, message, date, read, type, reference_id 
                FROM notifications 
                WHERE destination = ? 
                ORDER BY date DESC
                LIMIT ?
            """, (flask.session['username'], limit))
            notifications_raw = cursor.fetchall()
            
            # Get total count for checking if more exist
            cursor.execute("""
                SELECT COUNT(*) 
                FROM notifications 
                WHERE destination = ?
            """, (flask.session['username'],))
            total_count = cursor.fetchone()[0]
            
            notifications = [
                {
                    'id': row[0],
                    'author': row[1],
                    'message': row[2],
                    'date': row[3],
                    'read': row[4],
                    'type': row[5],
                    'reference_id': row[6]
                } for row in notifications_raw
            ]
            
            has_more = total_count > limit
            
            return flask.render_template('notifications.html', 
                                       notifications=notifications,
                                       has_more=has_more)

        @app.route('/api/notifications/load-more', methods=['GET'])
        @security.login_required
        def load_more_notifications():
            offset = int(flask.request.args.get('offset', 0))
            limit = 10
            
            cursor = self.db_configs.conn.cursor()
            cursor.execute("""
                SELECT id, author, message, date, read, type, reference_id 
                FROM notifications 
                WHERE destination = ? 
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """, (flask.session['username'], limit, offset))
            notifications_raw = cursor.fetchall()
            
            # Get total count for checking if more exist
            cursor.execute("""
                SELECT COUNT(*) 
                FROM notifications 
                WHERE destination = ?
            """, (flask.session['username'],))
            total_count = cursor.fetchone()[0]
            
            notifications = [
                {
                    'id': row[0],
                    'author': row[1],
                    'message': row[2],
                    'date': row[3],
                    'read': row[4],
                    'type': row[5],
                    'reference_id': row[6]
                } for row in notifications_raw
            ]
            
            return flask.jsonify({
                'notifications': notifications,
                'has_more': total_count > (offset + limit)
            })

        @app.route('/api/notifications/unread', methods=['GET'])
        @security.login_required
        def unread_notifications():
            try:
                username = flask.session['username']
                if not username:
                    return flask.jsonify({'error': 'User not authenticated properly', 'notifications': []}), 401

                cursor = self.db_configs.conn.cursor()
                cursor.execute(""" SELECT * FROM notifications WHERE destination = ? AND read = 0 """, (username,))

                notifications = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                notifications_dict = [dict(zip(columns, row)) for row in notifications]

                return flask.jsonify({'notifications': notifications_dict})
            except Exception as e:
                app.logger.error(f"Error fetching unread notifications: {str(e)}")
                return flask.jsonify({'error': 'Failed to fetch notifications', 'notifications': []}), 500

        @app.route('/api/notifications/mark-read', methods=['POST'])
        @security.login_required
        def mark_notification_read():
            if not flask.request.is_json:
                return flask.jsonify({'error': 'Content-Type must be application/json'}), 415

            data = flask.request.get_json()
            notification_id = data.get('id')
            
            if not notification_id:
                return flask.jsonify({'error': 'Missing notification id'}), 400
            
            cursor = self.db_configs.conn.cursor()
            cursor.execute("""
                UPDATE notifications 
                SET read = 1 
                WHERE id = ? AND destination = ?
            """, (notification_id, flask.session['username']))
            self.db_configs.conn.commit()
            
            if cursor.rowcount == 0:
                return flask.jsonify({'error': 'No notification found with given id'}), 404
            
            return flask.jsonify({'success': True})

        @app.route("/keyword_search", methods=["POST", "GET"])
        @security.login_required
        def keyword_search():
            searchbox = flask.request.form.get("text")

            return search_engine.keyword_search_in_db(conn=self.db_configs.conn, keyword=searchbox)
            
        @app.route("/realtime_search", methods=["POST"])
        @security.login_required
        def realtime_search():
            # Get search parameters from the request
            search_params = flask.request.form.to_dict()
            
            # Get the offset for pagination
            offset = int(search_params.get('offset', 0))
            limit = int(search_params.get('limit', 10))
            
            # Perform the search
            entries_list = search_engine.realtime_filter_entries(
                self.db_configs.conn, 
                search_params,
                offset=offset,
                limit=limit
            )
            
            # Count total results for pagination
            total_count = search_engine.count_matching_entries(
                self.db_configs.conn,
                search_params
            )
            
            # Format entries for display
            entries_dict_list = []
            for entry in entries_list:
                entries_dict_list.append({
                    'hash_id': entry[0],
                    'tags': entry[1],
                    'author': entry[5],
                    'date': entry[4],
                    'conditions': entry[6],
                    'title': entry[7],
                    'id': entry[9]
                })
            
            # Return the results as JSON
            return flask.jsonify({
                'entries': entries_dict_list,
                'total_count': total_count,
                'has_more': total_count > (offset + limit)
            })

        @app.route('/forgot_password', methods=['GET', 'POST'])
        # @self.logger
        def forgot_password():
            if flask.request.method == 'GET':
                return flask.render_template('forgot_password.html')
            return flask.redirect(flask.url_for('login'))

        @app.route('/request_password_reset', methods=['POST'])
        # @self.logger
        def request_password_reset():
            if not self.mailing_bool:
                flask.flash('Email notifications are not enabled on this server')
                return flask.redirect(flask.url_for('login'))
            
            identifier = flask.request.form.get('identifier', '')
            
            # Look up user by username or email
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT id, username, email FROM users WHERE username=? OR email=?", 
                          (identifier, identifier))
            user = cursor.fetchone()
            
            if user:
                user_id, username, email = user
                
                if not email:
                    flask.flash('This user does not have an email address set')
                    return flask.redirect(flask.url_for('forgot_password'))
                
                # Generate a secure token
                token = secrets.token_urlsafe(32)
                expiry = dt.datetime.now() + dt.timedelta(hours=24)
                expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S')
                
                # Store the token in the database (you'll need to create a password_reset_tokens table)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        token TEXT PRIMARY KEY,
                        user_id INTEGER,
                        expiry TEXT,
                        used INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("INSERT INTO password_reset_tokens VALUES (?, ?, ?, 0)", 
                              (token, user_id, expiry_str))
                self.db_configs.conn.commit()
                
                # Send email with reset link
                reset_link = f"{self.host_url}/reset_password/{token}"
                mail_args = {
                    'receiver_email': email,
                    'sender_email': self.app.config['CREDS_FILE']['SENDER_EMAIL_ADDRESS'],
                    'password': self.app.config['CREDS_FILE']['SENDER_EMAIL_PASSWORD'],
                    'subject': 'Password Reset Request',
                    'txt': f"""<p>Hello {username},</p>
                        <p>You requested a password reset. Please click the link below to set a new password:</p>
                        <p><a href="https://{reset_link}">Reset Password</a></p>
                        <p>This link will expire in 24 hours.</p>
                        <p>If you did not request this reset, please ignore this email.</p>""",
                }
                success = mailing.send_password_reset_mail(mail_args)
                
                if success:
                    flask.flash('Password reset instructions have been sent to your email')
                else:
                    flask.flash('Failed to send password reset email')
            else:
                # Don't reveal whether the account exists
                flask.flash('If that account exists, password reset instructions have been sent to the associated email')
            
            return flask.redirect(flask.url_for('login'))

        @app.route('/reset_password/<string:token>', methods=['GET', 'POST'])
        # @self.logger
        def reset_password(token):
            print(f"Resetting password for token: {token}")
            # Verify token
            cursor = self.db_configs.conn.cursor()
            cursor.execute("""
                SELECT user_id, expiry, used FROM password_reset_tokens 
                WHERE token = ?
            """, (token,))
            result = cursor.fetchone()
            
            if not result:
                flask.flash('Invalid or expired password reset link')
                return flask.redirect(flask.url_for('login'))
            
            user_id, expiry_str, used = result
            
            if used:
                flask.flash('This password reset link has already been used')
                return flask.redirect(flask.url_for('login'))
            
            expiry = dt.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
            if dt.datetime.now() > expiry:
                flask.flash('This password reset link has expired')
                return flask.redirect(flask.url_for('login'))
            
            if flask.request.method == 'POST':
                password = flask.request.form.get('password')
                repeat_password = flask.request.form.get('repeat_password')
                
                if password != repeat_password:
                    flask.flash('Passwords do not match')
                    return flask.render_template('reset_password.html', token=token)
                
                # Update password
                hashed_password = security.hash_password(password)
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", 
                              (hashed_password, user_id))
                
                # Mark token as used
                cursor.execute("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", 
                              (token,))
                self.db_configs.conn.commit()
                
                flask.flash('Your password has been updated successfully')
                return flask.redirect(flask.url_for('login'))
            
            return flask.render_template('reset_password.html', token=token)

        @app.route('/api/browser_addon/insert_entry', methods=['POST'])
        def browser_addon_insert_entry():
            """
            API endpoint for browser add-on to insert entries.
            Requires API key authentication.
            
            Expected JSON payload:
            {
                "username": "username",
                "api_key": "api_key",
                "entry_name": "Document Title",
                "url": "https://docs.google.com/...",
                "notes": "Notes about the document",
                "tags": "tag1,tag2,tag3",
                "document_type": "Google Sheet/Google Doc/Google Slide",
                "date": "YYYY-MM-DD HH:MM:SS" (optional, defaults to current datetime)
            }
            """
            try:
                data = flask.request.json
                
                # Validate required fields
                required_fields = ['username', 'api_key', 'entry_name', 'url']
                for field in required_fields:
                    if field not in data or not data[field]:
                        return flask.jsonify({
                            'success': False,
                            'message': f'Missing required field: {field}'
                        }), 400
                
                # Authenticate user
                user = operators.get_user_by_username(self.db_configs.conn, data['username'])
                if not user:
                    return flask.jsonify({
                        'success': False,
                        'message': 'User not found'
                    }), 401
                
                # Check API key from the dedicated api_key field
                cursor = self.db_configs.conn.cursor()
                cursor.execute('SELECT api_key FROM users WHERE username = ?', (data['username'],))
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    return flask.jsonify({
                        'success': False,
                        'message': 'API key not configured for user'
                    }), 401
                
                stored_api_key = result[0]
                if stored_api_key != data['api_key']:
                    return flask.jsonify({
                        'success': False,
                        'message': 'Invalid API key'
                    }), 401
                
                # Process entry data
                author = data['username']
                
                # Handle date - use provided date or current datetime
                if 'date' in data and data['date']:
                    # Validate date format
                    try:
                        # Parse the date to ensure it's valid
                        dt.datetime.strptime(data['date'], "%Y-%m-%d")
                        date = data['date']
                    except ValueError:
                        # If invalid format, use current datetime
                        date = dt.datetime.now().strftime("%Y-%m-%d")
                else:
                    date = dt.datetime.now().strftime("%Y-%m-%d")
                
                tags = data.get('tags', '')
                file_path = data.get('url', '')
                notes = data.get('notes', '')
                
                # Add document type information to notes
                doc_type = data.get('document_type', 'Google Document')
                if notes:
                    notes = f"Type: {doc_type}\n\n{notes}"
                else:
                    notes = f"Type: {doc_type}"
                    
                entry_name = data['entry_name']
                parent_entry = data.get('parent_entry', '')
                
                # Process conditions (similar to insert_entry_to_db)
                conditions = data.get('conditions', '')
                
                # Check if parent entry exists
                if parent_entry and not utils.check_hash_id_existence(self.db_configs.conn, parent_entry):
                    return flask.jsonify({
                        'success': False,
                        'message': 'Parent entry does not exist'
                    }), 400
                
                # Insert entry
                success_bool, hash_id = operators.insert_entry_to_db(
                    conn=self.db_configs.conn,
                    Author=author,
                    date=date,
                    Tags=tags,
                    File_Path=file_path,
                    Notes=notes,
                    conditions=conditions,
                    entry_name=entry_name,
                    parent_entry=parent_entry
                )
                utils.upload_files(self.app.config, hash_id, []) # to make sure the folder exist
                # Handle file uploads if provided (base64 encoded files)
                if success_bool and 'files' in data and data['files']:
                    try:
                        import base64
                        import tempfile
                        import os
                        from werkzeug.datastructures import FileStorage
                        
                        uploaded_files = []
                        
                        # Process each file in the files array
                        for file_data in data['files']:
                            if 'name' in file_data and 'content' in file_data and 'type' in file_data:
                                # Decode base64 content
                                file_content = base64.b64decode(file_data['content'])
                                
                                # Create a temporary file
                                temp_file = tempfile.NamedTemporaryFile(delete=False)
                                temp_file.write(file_content)
                                temp_file.close()
                                
                                # Create a FileStorage object
                                file_obj = FileStorage(
                                    stream=open(temp_file.name, 'rb'),
                                    filename=file_data['name'],
                                    content_type=file_data['type']
                                )
                                
                                uploaded_files.append(file_obj)
                        
                        # Upload files
                        if uploaded_files:
                            utils.upload_files(self.app.config, hash_id, uploaded_files)
                            
                            # Clean up temporary files
                            for file_obj in uploaded_files:
                                file_obj.stream.close()
                                os.unlink(file_obj.stream.name)
                    except Exception as e:
                        utils.error_log(f"Error processing file uploads: {str(e)}")
                
                if success_bool:
                    return flask.jsonify({
                        'success': True,
                        'message': f'Entry added successfully',
                        'hash_id': hash_id
                    })
                else:
                    return flask.jsonify({
                        'success': False,
                        'message': 'Error adding entry'
                    }), 500
                
            except Exception as e:
                utils.error_log(str(e))
                return flask.jsonify({
                    'success': False,
                    'message': f'Server error: {str(e)}'
                }), 500

        @app.route('/api/browser_addon/configure', methods=['GET', 'POST'])
        @security.login_required
        def browser_addon_configure():
            """Page to configure the browser add-on for the current user"""
            if flask.request.method == 'POST':
                try:
                    # Generate a new API key
                    api_key = secrets.token_hex(16)
                    
                    # Update the user's api_key field
                    cursor = self.db_configs.conn.cursor()
                    
                    # Store API key in the dedicated column
                    cursor.execute('UPDATE users SET api_key = ? WHERE username = ?', 
                                  (api_key, flask.session['username']))
                    self.db_configs.conn.commit()
                    
                    flask.flash('API key generated successfully. Please save it securely.')
                    return flask.render_template('browser_addon_config.html', 
                                              api_key=api_key, 
                                              username=flask.session['username'])
                except Exception as e:
                    utils.error_log(str(e))
                    flask.flash(f'Error generating API key: {str(e)}')
                    return flask.redirect(flask.url_for('profile'))
            else:
                # Check if user already has an API key
                cursor = self.db_configs.conn.cursor()
                cursor.execute('SELECT api_key FROM users WHERE username = ?', (flask.session['username'],))
                result = cursor.fetchone()
                has_api_key = result and result[0] is not None
                
                return flask.render_template('browser_addon_config.html',
                                          api_key=None,
                                          username=flask.session['username'],
                                          has_api_key=has_api_key)

        @app.route('/api/browser_addon/download', methods=['GET'])
        @security.login_required
        def download_browser_addon():
            """
            Endpoint to download the browser extension as a ZIP file.
            Creates a ZIP file on-the-fly containing all the extension files.
            """
            try:
                import io
                import zipfile
                import pathlib
                import os
                
                # Create an in-memory ZIP file
                memory_file = io.BytesIO()
                extension_zip = zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED)
                
                # Get the path to the browser-extension directory
                # Assuming the browser-extension directory is at the project root
                project_root = str(pathlib.Path(__file__).parent.parent.parent.absolute())
                extension_dir = os.path.join(project_root, 'browser-extension')
                
                # Check if the directory exists
                if not os.path.exists(extension_dir):
                    flask.flash('Browser extension files not found.')
                    return flask.redirect(flask.url_for('browser_addon_configure'))
                
                # Add all files in the browser-extension directory to the ZIP
                for root, dirs, files in os.walk(extension_dir):
                    for file in files:
                        # Skip any temporary or hidden files
                        if file.startswith('.') or file.startswith('~'):
                            continue
                            
                        file_path = os.path.join(root, file)
                        # Get the relative path to maintain directory structure in ZIP
                        relative_path = os.path.relpath(file_path, extension_dir)
                        extension_zip.write(file_path, arcname=relative_path)
                
                # Finalize the ZIP file
                extension_zip.close()
                memory_file.seek(0)
                
                # Return the ZIP file as a download
                return flask.send_file(
                    memory_file,
                    download_name='data-manager-browser-extension.zip',
                    as_attachment=True,
                    mimetype='application/zip'
                )
                
            except Exception as e:
                utils.error_log(str(e))
                flask.flash(f'Error creating extension package: {str(e)}')
                return flask.redirect(flask.url_for('browser_addon_configure'))

        # Check if we're in testing mode
        if not self.app.config.get('TESTING', False):
            # Only start the waitress server if not in testing mode
            t = Thread(target=waitress.serve, args=([self.app]), kwargs={'host':self.ip, 'port':self.port, 'threads':self.num_threads})
            t.start()        