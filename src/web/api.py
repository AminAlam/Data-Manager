import sys
sys.path.append('../database')
sys.path.append('../utils')

import logging

import utils
import security
import uuid
import search_engine
import operators
from dictianory import slef_made_codes, slef_made_codes_inv_map
import flask
from threading import Thread
import csv
import os
import datetime as dt
from flask_sessionstore import Session
from flask_sqlalchemy import SQLAlchemy

from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField


def add_admin(db_configs, app_configs):
    conn = db_configs.conn
    cursor = conn.cursor()
    cursor.execute('select * from users where username=?', ('admin',))
    users = cursor.fetchall()
    if len(users)==0:
        cursor.execute('insert into users values (?,?,?,?,?,?)', ('admin', 'SIGLAB_IST_VICE', 1, None, None, None))
        conn.commit()
        utils.init_user(app_configs, db_configs, 'admin')

class WebApp():
    def __init__(self, db_configs, ip, port, static_folder): 
        self.ip = ip
        self.port = port
        self.db_configs = db_configs
        self.app = flask.Flask(__name__, static_folder=static_folder)
        self.app.config['DATABASE_FOLDER'] = './src/database'
        self.app.config['UPLOAD_FOLDER'] = './src/database/uploaded_files'
        self.app.config['CONDITIONS_JSON'] = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions', 'info.json')
        self.app.config['TEMPLATES_FOLDER'] = './src/web/templates'
        self.app.session_db = SQLAlchemy()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
        self.app.config['SESSION_TYPE'] = 'sqlalchemy'
        self.app.config['SECRET_KEY'] = "JIEO:FJ:IO9@)#8u2rIUL@HFrfrkeferfG8#"
        self.app.config['RECAPTCHA_PUBLIC_KEY'] = "6LdnS5EjAAAAAAJ28il_17CaciXAswp6r_zeJ7Ap"
        self.app.config['RECAPTCHA_PRIVATE_KEY'] = "6LdnS5EjAAAAANdLvDGQwT-nxv0i8flIbr2PZ3qm"
        with self.app.app_context():
            Session(self.app)
        add_admin(self.db_configs, self.app.config)
    
    class RecaptchaForm(FlaskForm):
        username = StringField("username", validators=[DataRequired()])
        password = PasswordField("password", validators=[DataRequired()])
        recaptcha = RecaptchaField()

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
        def index():

            if security.check_logged_in(flask.session):
                experiments_list = search_engine.experiments_time_line(self.db_configs.conn)
                experiments_html = flask.render_template('experiments_list.html', experiments_list=experiments_list)
                experiments_html = flask.Markup(experiments_html)
                return flask.render_template('index.html', experiments_html=experiments_html)
            else:
                return flask.redirect(flask.url_for('login'))

        @app.route('/logout')
        def logout():
            if security.check_logged_in(flask.session):
                flask.session.pop('logged_in', None)
                flask.session.pop('username', None)
                flask.session.pop('password', None)
                flask.session.pop('admin', None)
                return flask.redirect(flask.url_for('login'))
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/add_user', methods=['GET', 'POST'])
        def add_user():
            if flask.session['admin']:
                return flask.render_template('add_user.html')
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/add_user_to_db', methods=['GET', 'POST'])
        def add_user_to_db():
            if security.check_logged_in(flask.session):
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
                    return flask.redirect(flask.url_for('index'))
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/experiments', methods=['GET', 'POST'])
        def experiments():
            if security.check_logged_in(flask.session):
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
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/insert_experiment', methods=('GET', 'POST'))
        def insert_experiment():
            if security.check_logged_in(flask.session):
                conditions_list = utils.list_user_conditoins_templates(self.db_configs.conn, self.app.config, flask.session)
                today_date = dt.datetime.now().strftime("%Y-%m-%d")
                return flask.render_template('insert_experiment.html', conditions_list=conditions_list, today_date=today_date)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/insert_experiment_to_db', methods=['GET', 'POST'])
        def insert_experiment_to_db():
            if security.check_logged_in(flask.session):
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
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/author_search", methods=["POST", "GET"])
        def author_search():
            if security.check_logged_in(flask.session):
                searchbox = flask.request.form.get("text")
                return search_engine.author_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/tags_search", methods=["POST", "GET"])
        def tags_search():
            if security.check_logged_in(flask.session):
                searchbox = flask.request.form.get("text")
                return search_engine.tags_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/text_search", methods=["POST", "GET"])
        def text_search():
            if security.check_logged_in(flask.session):
                searchbox = flask.request.form.get("text")
                return search_engine.text_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/experiment/<int:id>", methods=["POST", "GET"])
        def experiment(id):
            if security.check_logged_in(flask.session):
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

                for count, filename in enumerate(List):
                    List[count] = [os.path.join(app.config['UPLOAD_FOLDER'], hash_id, filename), f"{slef_made_codes_inv_map['remove']}&{filename}", filename]

                Files = List
                conditions = utils.read_json_file(self.app.config['CONDITIONS_JSON'])
                experiment = tuple(experiment)
                conditions = utils.modify_conditions_json(conditions, target_conditions)
                conditions_html = flask.render_template('conditions.html', conditions=conditions)
                conditions_html = flask.Markup(conditions_html)
                return flask.render_template('experiment.html', experiment=experiment, Files=Files, conditions_html=conditions_html)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/experiment_by_hash_id/<string:hash_id>", methods=["POST", "GET"])
        def experiment_by_hash_id(hash_id):
            if security.check_logged_in(flask.session):
                id = utils.get_id_by_hash_id(self.db_configs.conn, hash_id)
                return flask.redirect(flask.url_for('experiment', id=id))
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/experiment/<int:id>/update_experiment", methods=["POST", "GET"])
        def update_experiment(id):
            if security.check_logged_in(flask.session):
                post_form = flask.request.form
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
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/experiment/<int:id>/delete_experiment", methods=["POST", "GET"])
        def delete_experiment(id):
            if security.check_logged_in(flask.session):
                success_bool = operators.delete_experiment_from_db(self.db_configs.conn, id)

                if success_bool:
                    message = 'Experiment is deleted successfully'

                else:
                    message = 'Something went wrong'

                flask.flash(message)
                return flask.redirect(flask.url_for('index'))
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))
        
        @app.route("/protocols", methods=["POST", "GET"])
        def protocols():
            if security.check_logged_in(flask.session):
                # list all files in the protocols folder
                dirName = os.path.join(app.config['DATABASE_FOLDER'], 'protocols')
                List = os.listdir(dirName)

                for count, filename in enumerate(List):
                    List[count] = filename

                protocols_file_list = List
                return flask.render_template('protocols.html', Files=protocols_file_list)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/conditions_templates", methods=["POST", "GET"])
        def conditions_templates():
            if security.check_logged_in(flask.session):
                conditions_list = utils.list_user_conditoins_templates(self.db_configs.conn, self.app.config, flask.session)
                return flask.render_template('user_condition_templates.html', conditions_list=conditions_list)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/update_conditions_templates_in_db", methods=["POST", "GET"])
        def update_conditions_templates_in_db():
            if security.check_logged_in(flask.session):
                post_form = flask.request.form
                success_bool = operators.update_conditions_templates(self.db_configs.conn, post_form, flask.session['username'])

                if success_bool:
                    message = 'Conditions template is updated successfully'

                else:
                    message = 'Something went wrong'

                flask.flash(message)
                return flask.redirect(flask.url_for('conditions_templates'))
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route("/<path:filename>")
        def static_dir(filename):
            allowed_files = ['static/js/JavaScript.js', 'static/css/style.css', 'static/bootstrap.min.css', '/static/css/style.css', '/static/js/JavaScript.js', '/static/bootstrap.min.css']
            if filename in allowed_files:
                return flask.send_from_directory(app.root_path, filename)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/send_experiment_file/<int:experiment_id>/<path:path>')
        def send_experiment_file(experiment_id, path):
            if security.check_logged_in(flask.session):
                if '/' not in path:
                    cwd = os.getcwd()
                    cwd = os.path.join(cwd, app.config['UPLOAD_FOLDER'])
                    hash_id = utils.get_hash_id_by_experiment_id(self.db_configs.conn, experiment_id)
                    path = os.path.join(hash_id, path)
                    print(cwd, path)
                    return flask.send_from_directory(cwd, path, as_attachment=True)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/send_protocol_file/<path:path>')
        def send_protocol_file(path):
            if security.check_logged_in(flask.session):
                if '/' not in path:
                    cwd = os.getcwd()
                    cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'protocols')
                    print(cwd, path)
                    return flask.send_from_directory(cwd, path, as_attachment=True)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/get_conditoin_by_templatename', methods=["POST", "GET"])
        def get_conditoin_by_templatename():
            if security.check_logged_in(flask.session):
                username = flask.session['username']
                template_name = flask.request.form.get("template_name")
                print(template_name)
                condition_html = utils.get_conditions_by_template_name(self.db_configs.conn, app.config, username, template_name)
                return condition_html
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        @app.route('/experiment_report_maker/<int:id>', methods=["POST", "GET"])
        def experiment_report_maker(id):
            if security.check_logged_in(flask.session):
                cwd = os.getcwd()
                cwd = os.path.join(cwd, app.config['DATABASE_FOLDER'], 'reports')
                experiment_report = utils.experiment_report_maker(self.db_configs.conn, id)
                file_path = os.path.join(cwd, f'report_{id}.txt')
                with open(file_path, 'w') as f:
                    f.write(experiment_report)
                return flask.send_from_directory(cwd,  f'report_{id}.txt',as_attachment=True)
            else:
                flask.flash('You are not logged in, please login first')
                return flask.redirect(flask.url_for('login'))

        t = Thread(target=self.app.run, args=(self.ip,self.port,False))
        t.start()        


                