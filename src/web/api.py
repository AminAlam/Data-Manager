import sys
sys.path.append('../database')
sys.path.append('../utils')

import utils
import search_engine
import operators
import flask
from threading import Thread
import csv
import os

class WebApp():
    def __init__(self, db_configs, ip, port, static_folder): 
        self.ip = ip
        self.port = port
        self.db_configs = db_configs
        self.app = flask.Flask(__name__, static_folder=static_folder)
        self.app.config['SECRET_KEY'] = 'evmermrefmwrf92i4=#RKM-!#$Km343FIJ!$Ifofi3fj2q4fj2M943f-02f40-F-132-4fk!#$fi91f-'
        self.app.config['DATABASE_FOLDER'] = './src/database'
        self.app.config['UPLOAD_FOLDER'] = './src/database/uploaded_files'

    def run(self):    
        app = self.app
        @app.route('/', methods=['GET', 'POST'])
        def index():
            experiments_list = search_engine.experiments_time_line(self.db_configs.conn)
            return flask.render_template('index.html', experiments_list=experiments_list)

        @app.route('/experiments', methods=['GET', 'POST'])
        def experiments():
            if flask.request.method == 'POST' and len(flask.request.form):
                experiments_list = search_engine.filter_experiments(self.db_configs.conn, flask.request.form)
                return flask.render_template('experiments.html', experiments_list=experiments_list)
            else:
                return flask.render_template('experiments.html', experiments_list=None)
        
        @app.route('/insert_experiment', methods=('GET', 'POST'))
        def insert_experiment():
            json_file_path = os.path.join(self.app.config['DATABASE_FOLDER'], 'conditions', 'info.json')
            conditions = utils.read_json_file(json_file_path)
            print(conditions)
            return flask.render_template('insert_experiment.html', conditions=conditions)

        @app.route('/insert_experiment_to_db', methods=['GET', 'POST'])
        def insert_experiment_to_db():
            if flask.request.method == 'POST':
                # try:
                print(flask.request.form)
                Author = flask.request.form['Author']
                date = flask.request.form['date']
                Tags = flask.request.form['Tags']
                File_Path = flask.request.form['File_Path']
                Notes = flask.request.form['Notes']
                Files = flask.request.files.getlist('Files')
                # except:
                #     flask.flash('Please fill all the forms')
                #     return flask.redirect(flask.url_for('insert_experiment'))

                if Author == '' or Tags == '' or date == '':
                    flask.flash('Please fill all the forms')
                    return flask.redirect(flask.url_for('insert_experiment'))
                success_bool, hash_id = operators.insert_experiment_to_db(conn=self.db_configs.conn, Author=Author, date=date, Tags=Tags, File_Path=File_Path, Notes=Notes)
                cwd = os.getcwd()
                folder_path = os.path.join(cwd, app.config['UPLOAD_FOLDER'], hash_id)
                os.mkdir(folder_path)
                if hash_id:
                    for file in Files:
                        if file.filename != '':
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], folder_path, file.filename))
                if success_bool:
                    message = 'Experiment is added successfully'
                else:
                    message = 'Something went wrong'

                flask.flash(message)
                return flask.redirect(flask.url_for('index'))

        @app.route("/author_search", methods=["POST", "GET"])
        def author_search():
            searchbox = flask.request.form.get("text")
            return search_engine.author_search_in_db(conn=self.db_configs.conn, keyword=searchbox)
        
        @app.route("/tags_search", methods=["POST", "GET"])
        def tags_search():
            searchbox = flask.request.form.get("text")
            return search_engine.tags_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/text_search", methods=["POST", "GET"])
        def text_search():
            searchbox = flask.request.form.get("text")
            return search_engine.text_search_in_db(conn=self.db_configs.conn, keyword=searchbox)

        @app.route("/experiment/<int:id>", methods=["POST", "GET"])
        def experiment(id):
            cursor = self.db_configs.conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id=?", (id,))
            experiment = cursor.fetchone()
            hash_id = experiment[0]
            dirName = os.path.join(app.config['UPLOAD_FOLDER'], hash_id)
            List = os.listdir(dirName)
            for count, filename in enumerate(List):
                List[count] = [os.path.join(app.config['UPLOAD_FOLDER'], hash_id, filename), filename]
            Files = List
            return flask.render_template('experiment.html', experiment=experiment, Files=Files)
        
        @app.route("/experiment/<int:id>/update_experiment", methods=["POST", "GET"])
        def update_experiment(id):
            post_form = flask.request.form
            success_bool = operators.update_experiment_in_db(self.db_configs.conn, id, post_form)
            if success_bool:
                message = 'Experiment is updated successfully'
            else:
                message = 'Something went wrong'
            flask.flash(message)
            return flask.redirect(flask.url_for('index'))
            
        @app.route("/experiment/<int:id>/delete_experiment", methods=["POST", "GET"])
        def delete_experiment(id):
            success_bool = operators.delete_experiment_from_db(self.db_configs.conn, id)
            if success_bool:
                message = 'Experiment is deleted successfully'
            else:
                message = 'Something went wrong'
            flask.flash(message)
            return flask.redirect(flask.url_for('index'))
        
        @app.route("/protocols", methods=["POST", "GET"])
        def protocols():
            # list all files in the protocols folder
            dirName = os.path.join(app.config['DATABASE_FOLDER'], 'protocols')
            List = os.listdir(dirName)
            for count, filename in enumerate(List):
                List[count] = [os.path.join(app.config['DATABASE_FOLDER'], 'protocols', filename), filename]
            protocols_file_list = List
            return flask.render_template('protocols.html', Files=protocols_file_list)

        @app.route("/<path:filename>")
        def static_dir(filename):
            return flask.send_from_directory(app.root_path, filename)

        # flask send file for download
        @app.route('/send_file/<path:path>')
        def send_file(path):
            cwd = os.getcwd()
            
            return flask.send_from_directory(cwd, path, as_attachment=True)#flask.redirect(flask.url_for('index'))




        t = Thread(target=self.app.run, args=(self.ip,self.port,False))
        t.start()        
