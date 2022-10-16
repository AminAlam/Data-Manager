import sys
sys.path.append('../database')
sys.path.append('../utils')

import utils
import search_engine
import operators
import flask
from threading import Thread
import csv

class WebApp():
    def __init__(self, db_configs, ip, port, static_folder): 
        self.ip = ip
        self.port = port
        self.db_configs = db_configs
        self.app = flask.Flask(__name__, static_folder=static_folder)
        self.app.config['SECRET_KEY'] = 'evmermrefmwrf92i4=#RKM-!#$Km343FIJ!$Ifofi3fj2q4fj2M943f-02f40-F-132-4fk!#$fi91f-'


    def run(self):    
        app = self.app
        @app.route('/')
        def index():
            return flask.render_template('index.html', post=None)

        @app.route('/experiments', methods=['GET', 'POST'])
        def experiments():
            if flask.request.method == 'POST' and len(flask.request.form):
                experiments_list = search_engine.filter_experiments(self.db_configs.conn, flask.request.form)
                return flask.render_template('experiments.html', experiments_list=experiments_list)
            else:
                return flask.render_template('experiments.html', experiments_list=None)

        

        @app.route('/insert_experiment', methods=('GET', 'POST'))
        def insert_experiment():
            return flask.render_template('insert_experiment.html')

        @app.route('/insert_experiment_to_db', methods=['GET', 'POST'])
        def insert_experiment_to_db():
            if flask.request.method == 'POST':
                try:
                    Author = flask.request.form['Author']
                    date = flask.request.form['date']
                    Tags = flask.request.form['Tags']
                    File_Path = flask.request.form['File_Path']
                    Notes = flask.request.form['Notes']
                except:
                    flask.flash('Please fill all the forms')
                    return flask.redirect(flask.url_for('insert_experiment'))

                if Author == '' or Tags == '' or date == '':
                    flask.flash('Please fill all the forms')
                    return flask.redirect(flask.url_for('insert_experiment'))
                success_bool = operators.insert_experiment_to_db(conn=self.db_configs.conn, Author=Author, date=date, Tags=Tags, File_Path=File_Path, Notes=Notes)

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
            return flask.render_template('experiment.html', experiment=experiment)
        
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
            





        @app.route('/<int:id>/edit_supervisor_in_db', methods=['GET', 'POST'])
        def edit_supervisor_in_db(id):
            if flask.request.method == 'POST':
                try:
                    name = flask.request.form['name']
                    university = flask.request.form['university']
                    email = flask.request.form['email']
                    country = flask.request.form['country']
                    webpage = flask.request.form['webpage']
                    position_type = flask.request.form['position_type']
                    university_rank = flask.request.form['university_rank']
                    emailed = flask.request.form['emailed']
                    answer = flask.request.form['answer']
                    interview = flask.request.form['interview']
                    notes = flask.request.form['notes']
                    email_date = flask.request.form['email_date_value']
                except:
                    flask.flash('Please Fill all the Forms')
                    return flask.redirect(flask.url_for('supervisor', id=id))

                if name == '' or university == '' or email == '' or country == '':
                    flask.flash('Please Fill all the Forms')
                    return flask.redirect(flask.url_for('supervisor', id=id))
                operators.edit_supervisor(self.db_configs.conn, name, university, email, country,
                                webpage=webpage, position_type=position_type, rank=university_rank, 
                                emailed=emailed, answer=answer, interview=interview, notes=notes, id=id,
                                email_date=email_date)
            
                message = 'Supervisor is updated successfully'
                flask.flash(message)
                return flask.redirect(flask.url_for('supervisor', id=id))

        @app.route('/<int:id>/delete_supervisor_in_db', methods=['GET', 'POST'])
        def delete_supervisor_in_db(id):
            operators.delete_supervisor(self.db_configs.conn, id)
            message = 'Supervisor is deleted successfully'
            flask.flash(message)
            return flask.redirect(flask.url_for('supervisors'))

        @app.route('/universities_format', methods=['GET', 'POST'])
        def universities_format():
            rank = flask.request.form['rank']
            if rank == 'Default':
                cursor = self.db_configs.conn.cursor()
                cursor.execute('SELECT * FROM universities')
                filters = ['Default']
            elif rank == 'Ascending':
                cursor = self.db_configs.conn.cursor()
                cursor.execute('SELECT * FROM universities ORDER BY rank ASC')
                filters = ['Ascending']
            else:
                cursor = self.db_configs.conn.cursor()
                cursor.execute('SELECT * FROM universities ORDER BY rank DESC')
                filters = ['Descending']
            universities = cursor.fetchall()

            for university_no in range(0,len(universities)):
                cursor.execute("SELECT rowid FROM supervisors WHERE university = ?", (universities[university_no][0],))
                num_supervisors = len(cursor.fetchall())
                universities[university_no] = universities[university_no]+(num_supervisors, )

            return flask.render_template('universities.html', posts=universities, filters=filters)

        @app.route('/export_csv')
        def export_csv():
            cursor = self.db_configs.conn.cursor()
            cursor.execute('SELECT * FROM supervisors')
            supervisors = cursor.fetchall()
            file_name = 'supervisors.csv'
            with open('web/'+file_name, 'w') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Name', 'University', 'Email', 'Country', 'Emailed?', 'Answered?', 'Interviewed?', 'Position Type', 'Webpage', 'Univerity Rank', 'Notes', 'ID', 'Email Date'])
                for supervisor in supervisors:
                    writer.writerow(supervisor)
            send_file(file_name)
            flask.flash(flask.Markup("CSV file is exported successfully! File is located at: <a href='"+file_name+"' download class='alert-link'>here </a>"))
            return flask.redirect(flask.url_for('index'))

        @app.route("/<path:filename>")
        def static_dir(filename):
            return flask.send_from_directory(app.root_path, filename)

        # flask send file for download
        @app.route('/<path:path>')
        def send_file(path):
            # flask send file to browser for download
            return flask.send_from_directory(app.root_path, path, as_attachment=True)




        t = Thread(target=self.app.run, args=(self.ip,self.port,False))
        t.start()        
