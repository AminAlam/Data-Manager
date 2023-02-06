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
from dictianory import slef_made_codes, slef_made_codes_inv_map
import flask
from threading import Thread

import datetime as dt
from flask_sessionstore import Session
from flask_sqlalchemy import SQLAlchemy

from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField

from functools import wraps

import waitress

def add_admin(db_configs, app_configs):
    conn = db_configs.conn
    cursor = conn.cursor()
    cursor.execute('select * from users where username=?', ('admin',))
    users = cursor.fetchall()
    if len(users)==0:
        cursor.execute('insert into users values (?,?,?,?,?,?)', ('admin', 'admin', 1, None, None, None))
        conn.commit()
        utils.init_user(app_configs, db_configs, 'admin')

class WebApp():
    def __init__(self, db_configs, ip, port, static_folder): 
        self.ip = ip
        self.port = port
        self.db_configs = db_configs
        self.app = flask.Flask(__name__, static_folder=static_folder)
        self.parent_path = str(pathlib.Path(__file__).parent.absolute())
        self.parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
        self.app.config['DATABASE_FOLDER'] = os.path.join(self.parent_parent_path ,'database')
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.parent_parent_path ,'database' ,'uploaded_files')
        self.app.config['FAMILY_TREE_FOLDER'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'family_tree')
        self.app.config['CONDITIONS_JSON'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions', 'info.json')
        self.app.config['TEMPLATES_FOLDER'] = os.path.join(self.parent_parent_path, 'web', 'templates')
        self.app.session_db = SQLAlchemy()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
        self.app.config['SESSION_TYPE'] = 'sqlalchemy'
        self.app.config['CREDS_FILE_PATH'] = os.path.join(self.app.root_path, 'creds.json')
        self.app.config['CREDS_FILE'] = utils.load_creds(self.app.config['CREDS_FILE_PATH'])
        self.app.config['SECRET_KEY'] = self.app.config['CREDS_FILE']['SECRET_KEY']
        self.app.config['RECAPTCHA_PUBLIC_KEY'] = self.app.config['CREDS_FILE']['RECAPTCHA_PUBLIC_KEY']
        self.app.config['RECAPTCHA_PRIVATE_KEY'] = self.app.config['CREDS_FILE']['RECAPTCHA_PRIVATE_KEY']

        self.ChatRoom = chatroom.ChatRoom(self.db_configs)

        with self.app.app_context():
            Session(self.app)
        add_admin(self.db_configs, self.app.config)

        print(f'App initialized. Server running on http://{self.ip}:{self.port}')
    
    class RecaptchaForm(FlaskForm):
        username = StringField("username", validators=[DataRequired()])
        password = PasswordField("password", validators=[DataRequired()])
        recaptcha = RecaptchaField()
    
    
    def logger(self, f):
        @wraps(f)
        def wrap(*args, **kwargs):
            time = dt.datetime.now()
            conn = self.db_configs.conn
            cursor = conn.cursor()
            try:
                action = f.__name__
                username = flask.session['username']
                cursor.execute('insert into logs values (?,?,?,?,?,?)', (username, action, time, 'pass', None, None))
                conn.commit()
                return f(*args, **kwargs)
            except Exception as e:
                cursor.execute('update logs set status=?, error=? where username=? and action=? and date=?', ('fail', str(e), username, action, time))
                conn.commit()
                return flask.render_template
        return wrap

    def run(self):
        app = self.app

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if flask.request.method == 'POST':
                username = flask.request.form['username']
                password = flask.request.form['password']
                conn = self.db_configs.conn
                cursor = conn.cursor()
                cursor.execute('select * from users where username=? and password=?', (username, password))
                users = cursor.fetchall()

                form = self.RecaptchaForm()
                if len(users)==0:
                    return flask.render_template('login.html', error='Invalid username or password', form=form)
                elif form.validate_on_submit():
                #elif 1:
                    flask.session['username'] = username
                    flask.session['password'] = password
                    flask.session['logged_in'] = True
                    flask.session['admin'] = users[0][2]
                    return flask.redirect(flask.url_for('index'))
                else:
                    form = self.RecaptchaForm()
                    return flask.render_template('login.html', error='Invalid Captcha', form=form)

            else:
                form = self.RecaptchaForm()
                return flask.render_template('login.html', form=form)

        @app.route('/', methods=['GET', 'POST'])
        @security.login_required
        def index():
            experiments_list = search_engine.experiments_time_line(self.db_configs.conn)
            experiments_html = flask.render_template('experiments_list.html', experiments_list=experiments_list)
            experiments_html = flask.Markup(experiments_html)
            return flask.render_template('index.html', experiments_html=experiments_html)

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
            admin = flask.request.form['admin'] == 'True'
            name = flask.request.form['name']
            email = flask.request.form['email']

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

            else:
                cursor.execute('insert into users (username, password, admin, name, email) values (?,?,?,?,?)', (username, password, admin, name, email))
                utils.init_user(app.config, self.db_configs, username)
                conn.commit()
                flask.flash('User added successfully')
                return flask.redirect(flask.url_for('index'))
    
        @app.route("/update_user_in_db/<int:id>", methods=['POST', 'GET'])
        @security.login_required
        @self.logger
        def update_user_in_db(id):
            if flask.request.method == 'POST':
                password = flask.request.form['password']
                repeat_password = flask.request.form['repeat_password']
                if flask.session['admin']:
                    admin = flask.request.form['admin'] == 'True'
                else:
                    admin = 0
                name = flask.request.form['name']
                email = flask.request.form['email']

                if password == '' or admin == '':
                    flask.flash('Please fill all the fields')
                    user = flask.request.form
                    return flask.render_template('profile.html', user=user)

                if password != repeat_password:
                    flask.flash('Passwords do not match')
                    user = flask.request.form
                    return flask.render_template('profile.html', user=user)

                conn = self.db_configs.conn
                cursor = conn.cursor()
                cursor.execute('select * from users where id=?', (id,))
                users = cursor.fetchall()

                if len(users)==0:
                    flask.flash('Username does not exist')
                    user = flask.request.form
                    return flask.render_template('profile.html', user=user)

                else:
                    cursor.execute('update users set password=?, admin=?, name=?, email=? where id=?', (password, admin, name, email, id))
                    conn.commit()
                    flask.flash('User updated successfully')
                    return flask.render_template('index.html')

        @app.route("/delete_user/<int:id>", methods=['POST', 'GET'])
        @security.admin_required
        @self.logger
        def delete_user(id):
            conn = self.db_configs.conn
            cursor = conn.cursor()
            cursor.execute('select * from users where id=?', (id,))
            users = cursor.fetchall()

            if len(users)==0:
                flask.flash('Username does not exist')
                return flask.redirect(flask.url_for('user_management'))

            else:
                cursor.execute('delete from users where id=?', (id,))
                conn.commit()
                flask.flash('User deleted successfully')
                return flask.redirect(flask.url_for('user_management'))
        
        @app.route('/user_management', methods=['GET', 'POST'])
        @security.admin_required
        def user_management():
            users = utils.get_users(self.db_configs.conn)

            users_html = [flask.render_template('user_profile_template.html', user=user) for user in users]
            users_html = [flask.Markup(user_html) for user_html in users_html]

            return flask.render_template('user_management.html', users_html=users_html, users=users)

        @app.route('/experiments', methods=['GET', 'POST'])
        @security.login_required
        def experiments():
            conditions = utils.read_json_file(self.app.config['CONDITIONS_JSON'])
            conditions = utils.modify_conditions_json(conditions, target_conditions=[])
            conditions_html = flask.render_template('conditions.html', conditions=conditions)
            conditions_html = flask.Markup(conditions_html)

            tomorrow_date = (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_date = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")

            dates = [yesterday_date, tomorrow_date]

            if flask.request.method == 'POST' and len(flask.request.form):
                experiments_list = search_engine.filter_experiments(self.db_configs.conn, flask.request.form)
                experiments_html = flask.render_template('experiments_list.html', experiments_list=experiments_list)
                experiments_html = flask.Markup(experiments_html)
                return flask.render_template('experiments.html', experiments_html=experiments_html, conditions_html=conditions_html, dates=dates)

            else:
                return flask.render_template('experiments.html', experiments_html=None, conditions_html=conditions_html, dates=dates)

        @app.route('/insert_experiment', methods=('GET', 'POST'))
        @security.login_required
        def insert_experiment():
            conditions_list = utils.list_user_conditoins_templates(self.db_configs.conn, self.app.config, flask.session)
            today_date = dt.datetime.now().strftime("%Y-%m-%d")
            return flask.render_template('insert_experiment.html', conditions_list=conditions_list, today_date=today_date)

        @app.route('/insert_experiment_to_db', methods=['GET', 'POST'])
        @security.login_required
        @self.logger
        def insert_experiment_to_db():
            if flask.request.method == 'POST':
                try:
                    Author = flask.session['username']
                    date = flask.request.form['date']
                    Tags = flask.request.form['Tags']
                    File_Path = flask.request.form['File_Path']
                    Notes = flask.request.form['Notes']
                    Files = flask.request.files.getlist('Files')
                    experiment_name = flask.request.form['experiment_name']
                    parent_experiment = flask.request.form['parent_experiment']

                except:
                    flask.flash('Please fill all the forms')
                    return flask.redirect(flask.url_for('insert_experiment'))

                if not utils.check_hash_id_existence(self.db_configs.conn, parent_experiment) and parent_experiment != '':
                    flask.flash('Parent experiment does not exist')
                    return flask.redirect(flask.url_for('insert_experiment'))


                if Author == '' or date == '' or experiment_name == '':
                    flask.flash('Please fill all the forms')
                    return flask.redirect(flask.url_for('insert_experiment'))

                conditions = []

                for form_input in flask.request.form:
                    if 'condition' == form_input.split('&')[0]:
                        conditions.append('&'.join(form_input.split('&')[1:]))
                    elif 'PARAM' == form_input.split('&')[0]:
                        list_tmp = form_input.split('&')[2:]
                        list_tmp.append(flask.request.form[f"PARAMVALUE&{'&'.join(form_input.split('&')[1:])}"].split('&')[-1])
                        list_tmp = '&'.join(list_tmp)
                        conditions.append(list_tmp)
                conditions = ','.join(conditions)
                success_bool, hash_id = operators.insert_experiment_to_db(conn=self.db_configs.conn, Author=Author, date=date, Tags=Tags, File_Path=File_Path, Notes=Notes, conditions=conditions, experiment_name=experiment_name, parent_experiment=parent_experiment)
                
                if hash_id:
                    utils.upload_files(self.app.config, hash_id, Files)

                if success_bool:
                    message = flask.Markup(f'Experiment is added successfully! hash_id: {hash_id}')

                else:
                    message = 'Something went wrong'

                flask.flash(message)
                return flask.redirect(flask.url_for('index', session=flask.session))

        @app.route("/author_search", methods=["POST", "GET"])
        @security.login_required
        def author_search():
            searchbox = flask.request.form.get("text")
            return search_engine.author_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/tags_search", methods=["POST", "GET"])
        @security.login_required
        def tags_search():
            searchbox = flask.request.form.get("text")
            return search_engine.tags_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/text_search", methods=["POST", "GET"])
        @security.login_required
        def text_search():
            searchbox = flask.request.form.get("text")
            return search_engine.text_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/experiment/<int:id>", methods=["POST", "GET"])
        @security.login_required
        def experiment(id):
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id=?", (id,))
            experiment = cursor.fetchone()
            target_conditions = experiment[6]
            experiment = list(experiment)
            experiment[6] = utils.parse_conditions(experiment[6])
            for i in range(len(experiment[6])):
                if len(experiment[6][i].split('&')) ==3:
                    experiment[6][i] = experiment[6][i].split('&')[-1]
                else:
                    experiment[6][i] = '->'.join(experiment[6][i].split('&')[-2:])
            hash_id = experiment[0]
            dirName = os.path.join(app.config['UPLOAD_FOLDER'], hash_id)
            List = os.listdir(dirName)

            family_tree_html = utils.family_tree_to_html(self.db_configs.conn, hash_id, self.app.config['FAMILY_TREE_FOLDER'])
            family_tree_html = flask.Markup(family_tree_html)

            for count, filename in enumerate(List):
                List[count] = [os.path.join(app.config['UPLOAD_FOLDER'], hash_id, filename), f"{slef_made_codes_inv_map['remove']}&{filename}", filename]

            Files = List
            conditions = utils.read_json_file(self.app.config['CONDITIONS_JSON'])
            experiment = tuple(experiment)
            conditions = utils.modify_conditions_json(conditions, target_conditions)
            conditions_html = flask.render_template('conditions.html', conditions=conditions)
            conditions_html = flask.Markup(conditions_html)
            return flask.render_template('experiment.html', experiment=experiment, Files=Files, conditions_html=conditions_html, family_tree_html=family_tree_html)

        @app.route("/experiment_by_hash_id/<string:hash_id>", methods=["POST", "GET"])
        @security.login_required
        def experiment_by_hash_id(hash_id):
            id = utils.get_id_by_hash_id(self.db_configs.conn, hash_id)
            return flask.redirect(flask.url_for('experiment', id=id))

        @app.route("/experiment/<int:id>/update_experiment", methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def update_experiment(id):
            post_form = flask.request.form
            experiment = utils.get_experiment_by_id(self.db_configs.conn, id)
            author = experiment[5]
            usename = flask.session['username']
            if author != usename:
                flask.flash('You are not allowed to edit this experiment')
                return flask.redirect(flask.url_for('experiment', id=id))

            # get hash_id from id
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT id_hash FROM experiments WHERE id=?", (id,))
            hash_id = cursor.fetchone()[0]

            parent_experiment = flask.request.form['parent_experiment']
            if not utils.check_hash_id_existence(self.db_configs.conn, parent_experiment) and parent_experiment != '':
                    flask.flash('Parent experiment does not exist')
                    return flask.redirect(flask.url_for('experiment', id=id))

            success_bool = operators.update_experiment_in_db(self.db_configs.conn, id, post_form, app.config, hash_id, flask.request.files.getlist('Files'))

            if success_bool:
                message = 'Experiment is updated successfully'

            else:
                message = 'Something went wrong'

            flask.flash(message)
            return flask.redirect(flask.url_for('index'))


        @app.route("/experiment/<int:id>/delete_experiment", methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def delete_experiment(id):
            experiment = utils.get_experiment_by_id(self.db_configs.conn, id)
            author = experiment[5]
            author = experiment[5]
            usename = flask.session['username']
            if author != usename:
                flask.flash('You are not allowed to delete this experiment')
                return flask.redirect(flask.url_for('experiment', id=id))

            success_bool = operators.delete_experiment_from_db(self.db_configs.conn, id)

            if success_bool:
                message = 'Experiment is deleted successfully'

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
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
            # get columns names from the table
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            columns = [column[1] for column in columns]
            # coonvert user to dict with columns as keys
            user = dict(zip(columns, user))
            user_html = flask.render_template('user_profile_template.html', user=user)
            user_html = flask.Markup(user_html)
            return flask.render_template('profile.html', user_html=user_html)

        @app.route("/<path:filename>")
        def static_dir(filename):
            allowed_files = [os.path.join('static', 'js', 'JavaScript.js'), os.path.join('static', 'css', 'style.css'), os.path.join('static', 'css', 'bootstrap.min.css')]
            if filename in allowed_files:
                return flask.send_from_directory(app.root_path, filename)
            else:
                return flask.redirect(flask.url_for('login'))

        @app.route('/send_experiment_file/<int:experiment_id>/<path:path>')
        @security.login_required
        def send_experiment_file(experiment_id, path):
            if '/' not in path:
                cwd = os.getcwd()
                cwd = os.path.join(cwd, app.config['UPLOAD_FOLDER'])
                hash_id = utils.get_hash_id_by_experiment_id(self.db_configs.conn, experiment_id)
                path = os.path.join(hash_id, path)
                return flask.send_from_directory(cwd, path, as_attachment=True)

        @app.route('/send_protocol_file/<path:path>')
        @security.login_required
        def send_protocol_file(path):
            if '/' not in path:
                cwd = os.getcwd()
                cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'protocols')
                return flask.send_from_directory(cwd, path, as_attachment=True)

        @app.route('/get_conditoin_by_templatename', methods=["POST", "GET"])
        @security.login_required
        def get_conditoin_by_templatename():
            username = flask.session['username']
            template_name = flask.request.form.get("template_name")
            condition_html = utils.get_conditions_by_template_name(self.db_configs.conn, app.config, username, template_name)
            return condition_html

        @app.route('/experiment_report_maker/<int:id>', methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def experiment_report_maker(id):
            cwd = os.getcwd()
            cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'reports')
            experiment_report = utils.experiment_report_maker(self.db_configs.conn, id)
            file_path = os.path.join(cwd, f'report_{id}.txt')
            with open(file_path, 'w') as f:
                f.write(experiment_report)
            return flask.send_from_directory(cwd,  f'report_{id}.txt',as_attachment=True)


        @app.route('/experiments_actions', methods=["POST", "GET"])
        @security.login_required
        @self.logger
        def experiments_actions():
            if flask.request.method == 'POST':
                post_form = flask.request.form
                experiments_ids = []
                action = post_form['action']  
                for key in post_form:
                    if '&' in key:
                        if key.split('&')[0] == 'Select':
                            experiments_ids.append(int(key.split('&')[1]))

                if len(experiments_ids) == 0:
                    flask.flash('No experiments were selected')
                    return flask.redirect(flask.request.referrer)
                        
                if action == 'bulk_report':
                    cwd = os.getcwd()
                    cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'reports')
                    username = flask.session['username']
                    file_path = os.path.join(cwd, f'bulk_report_{username}.txt')
                    with open(file_path, 'w') as f:
                        for id in experiments_ids:
                            experiment_report = utils.experiment_report_maker(self.db_configs.conn, id)
                            f.write(experiment_report)
                            f.write(f"\n\n{'-'*20}\n\n")
                    return flask.send_from_directory(cwd, f'bulk_report_{username}.txt', as_attachment=True)

                elif action == 'set_parent_experiment':
                    parent_experiment_hash_id = post_form['parent_experiment_hash_id']
                    if utils.check_hash_id_existence(self.db_configs.conn, parent_experiment_hash_id):
                        for id in experiments_ids:
                            utils.set_parent_experiment(self.db_configs.conn, id, parent_experiment_hash_id)
                        flask.flash('Parent experiment was set successfully')
                        return flask.redirect(flask.request.referrer)
                    else:
                        flask.flash('Parent experiment Hash ID does not exist')
                        return flask.redirect(flask.request.referrer)
                    


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
            time_now = dt.datetime.now()
            time_now = time_now.strftime("%d/%m/%Y %H:%M:%S")
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
            cusor = self.db_configs.conn.cursor()
            # get all logs since last 7 days
            cusor.execute("SELECT * FROM logs WHERE date > date('now', '-7 days')")
            logs = cusor.fetchall()
            columns = [column[0] for column in cusor.description]
            logs = [dict(zip(columns, row)) for row in logs]
            return flask.render_template('logs.html', logs=logs)

            
        t = Thread(target=waitress.serve, args=([self.app]), kwargs={'host':self.ip, 'port':self.port})
        t.start()        


                