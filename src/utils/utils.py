import sys
import requests
import os
import random
import string
import json
import flask
sys.path.append('../database')
import operators
import networkx as nx

from datetime import datetime, date

def error_log(error):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)

def init_directories(DATABASE_FOLDER):
    dir2make = os.path.join(DATABASE_FOLDER, 'uploaded_files')
    if not os.path.exists(dir2make):
        os.makedirs(dir2make)
    dir2make = os.path.join(DATABASE_FOLDER, 'protocols')
    if not os.path.exists(dir2make):
        os.makedirs(dir2make)
    dir2make = os.path.join(DATABASE_FOLDER, 'conditions')
    if not os.path.exists(dir2make):
        os.makedirs(dir2make)
    dir2make = os.path.join(DATABASE_FOLDER, 'reports')
    if not os.path.exists(dir2make):
        os.makedirs(dir2make)
    dir2make = os.path.join(DATABASE_FOLDER, 'family_tree')
    if not os.path.exists(dir2make):
        os.makedirs(dir2make)
    
def init_db(db_configs):
    print('Initilizing the databse')
    for table in db_configs.table_lists:
        operators.create_table(db_configs.conn, table)

def check_existence_table(db_configs):
    conn = db_configs.conn
    cursor = conn.cursor()
    cursor.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name=? ''', ['universities'])
    if cursor.fetchone()[0]==1:
        open_bool = 1
    else:
        open_bool = 0
    return open_bool

def check_existence_author(conn, author):
    cursor = conn.cursor()
    cursor.execute('select * from authors where author=?', (author,))
    authors = cursor.fetchall()
    if len(authors)==0:
        return False
    else:
        return True

def parse_tags(Tags):
    Tags = Tags.split(',')
    Tags = [tag.strip() for tag in Tags]
    return Tags

def parse_conditions(conditions):
    conditions = conditions.split(',')
    conditions = [condition.strip() for condition in conditions]
    return conditions

def check_existence_tag(conn, tag):
    cursor = conn.cursor()
    cursor.execute('select * from tags where tag=?', (tag,))
    tags = cursor.fetchall()
    if len(tags)==0:
        return False
    else:
        return True

def check_existence_condition(conn, condition):
    cursor = conn.cursor()
    cursor.execute('select * from conditions where condition=?', (condition,))
    conditions = cursor.fetchall()
    if len(conditions)==0:
        return False
    else:
        return True

def generate_hash(conn):
    hash_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id_hash=?', (hash_id,))
    experiments = cursor.fetchall()
    if len(experiments)==0:
        return hash_id
    else:
        return generate_hash(conn)

def experiment_list_maker(experiments_list):
    experiments_list = list(experiments_list)
    for i, experiment in enumerate(experiments_list):
        experiment = list(experiment)
        experiment[1] = parse_tags(experiment[1])
        experiment[6] = parse_conditions(experiment[6])
        for j in range(len(experiment[6])):
            if len(experiment[6][j].split('&')) ==3:
                experiment[6][j] = experiment[6][j].split('&')[-1]
            else:
                experiment[6][j] = '->'.join(experiment[6][j].split('&')[-2:])
        experiments_list[i] = experiment
    return experiments_list

def check_for_internet_connection():
    try:
        requests.get('http://www.google.com')
        return True
    except requests.ConnectionError:
        return False

def apply_updates2db(db_configs):
    # add email_date to the database
    cursor = db_configs.conn.cursor()
    cursor.execute('SELECT * FROM messages')
    column_names = list(map(lambda x: x[0], cursor.description))
    if 'destination' not in column_names:
        cursor.execute('ALTER TABLE messages ADD COLUMN destination text NOT NULL') 

def read_json_file(json_file):
    with open(json_file) as f:
        data = json.load(f)
    return data    

def modify_conditions_json(conditions, target_conditions):

    for condition in conditions.keys():
        for condition_nested in conditions[condition].keys():
            for indx, single_condition in enumerate(conditions[condition][condition_nested]):
                if len(single_condition.split('&')) == 4:
                    param_name = single_condition.split("&")[0]
                    if type(target_conditions) == str:
                        target_conditions_list = target_conditions.split(',')
                    else:
                        target_conditions_list = target_conditions
                    for target_condition in target_conditions_list:
                        if param_name in target_condition:
                            conditions[condition][condition_nested][indx] = [single_condition, "checked", target_condition.split('&')[-1]]
                            break
                    else:
                        conditions[condition][condition_nested][indx] = [single_condition, ""]
                else:
                    if f'{condition}&{condition_nested}&{single_condition}' in target_conditions:
                        conditions[condition][condition_nested][indx] = [single_condition, "checked"]
                    else:
                        conditions[condition][condition_nested][indx] = [single_condition, ""]
    return conditions

def init_user(app_config, db_configs, user_name):
        conn = db_configs.conn
        cursor = conn.cursor()
        cursor.execute('insert into conditions_templates values (?, ?, ?, ?)', (user_name, 'default', '', None))
        conn.commit()

def list_user_conditoins_templates(conn, app_config, session):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conditions_templates WHERE author=?", (session['username'],))
    conditions_templates = cursor.fetchall()
    conditions_list = []
    for conditoin_no, condition_template in enumerate(conditions_templates):
        template_name = condition_template[1]
        condition = condition_template[2]
        condition_template = list(condition_template)
        condition_json = read_json_file(app_config['CONDITIONS_JSON'])
        condition_json = modify_conditions_json(condition_json, condition)
        conditions_html = flask.render_template('conditions.html', conditions=condition_json, template_name=template_name, conditoin_no=conditoin_no)
        conditions_html = flask.Markup(conditions_html)
        conditions_list.append([conditions_html, template_name])
    return conditions_list

def get_conditions_by_template_name(conn, app_config, username, templatename):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conditions_templates WHERE author=? AND template_name=?", (username, templatename))
    conditions_template = cursor.fetchall()    
    template_name = conditions_template[0][1]
    condition = conditions_template[0][2]
    condition_json = read_json_file(app_config['CONDITIONS_JSON'])
    condition_json = modify_conditions_json(condition_json, condition)
    conditions_html = flask.render_template('conditions.html', conditions=condition_json, template_name=template_name)
    conditions_html = flask.Markup(conditions_html)
    return conditions_html

def upload_files(app_config, hash_id, Files):
    folder_path = os.path.join(app_config['UPLOAD_FOLDER'], hash_id)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    for file in Files:
        print(Files)
        if file.filename != '':
            file.save(os.path.join(folder_path, file.filename))

def remove_files(app_config, hash_id, file_names):
    for file_name in file_names:
        file_path = os.path.join(app_config['UPLOAD_FOLDER'], hash_id, file_name)
        os.remove(file_path)

def get_hash_id_by_experiment_id(conn, id):
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id=?', (id,))
    experiment = cursor.fetchone()
    hash_id = experiment[0]
    return hash_id

def get_id_by_hash_id(conn, hash_id):
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id_hash=?', (hash_id,))
    experiment = cursor.fetchone()
    id = experiment[9]
    return id

def experiment_report_maker(conn, experiment_id):
    conn = conn
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id=?', (experiment_id,))
    experiment = cursor.fetchone()
    experiment = list(experiment)
    experiment[1] = parse_tags(experiment[1])
    experiment[6] = parse_conditions(experiment[6])
    for i in range(len(experiment[6])):
        experiment[6][i] = experiment[6][i].replace('&', '->')
    # write the report to a text file and send it to the user
    report = f'Hash ID: {experiment[0]}'
    report = report + f'\nParent Hash ID: {experiment[8]}'
    report = report + f'\nName: {experiment[7]}'
    report = report + f'\nAuthor: {experiment[5]}'
    report = report + f'\nDate: {experiment[4]}'
    report = report + f'\nFile Path: {experiment[3]}'
    report = report + f'\nTags: {experiment[1]}'
    report = report + f'\nConditions: {experiment[6]}'
    # report = report + f'\n\n\n\n\n\n\n'
    # for i in range(20):
    #     report = report + f'\n{experiment[0]}_{i}'
    return report

def check_hash_id_existence(conn, hash_id):
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id_hash=?', (hash_id,))
    experiment = cursor.fetchone()
    if experiment is None:
        return False
    else:
        return True

def load_creds(CREDS_FILE_PATH):
    with open(CREDS_FILE_PATH) as f:
        creds = json.load(f)
    return creds

def set_parent_experiment(conn, experiment_id, parent_hash_id):
    cursor = conn.cursor()
    cursor.execute('update experiments set experiment_parent=? where id=?', (parent_hash_id, experiment_id))
    conn.commit()

def get_family_tree(conn, experiment_hash_id):
    family_tree = {'parent': None, 'children': None, 'self': None}
    cursor = conn.cursor()
    cursor.execute('select * from experiments where id_hash=?', (experiment_hash_id,))
    experiment = cursor.fetchone()
    experiment = list(experiment)
    experiment_name = experiment[7]
    parent_hash_id = experiment[8]
    experiment_id = experiment[-1]
    family_tree['self'] = [experiment_name, experiment_id]

    if parent_hash_id is None or parent_hash_id == 'None' or parent_hash_id == '':
        family_tree['parent'] = None
    else:
        cursor.execute('select * from experiments where id_hash=?', (parent_hash_id,))
        parent = cursor.fetchone()
        parent = list(parent)
        parent_name = parent[7]
        parent_id = parent[-1]
        family_tree['parent'] = [parent_name, parent_id]

    cursor.execute('select * from experiments where experiment_parent=?', (experiment_hash_id,))
    children = cursor.fetchall()
    children = list(children)
    if len(children) == 0:
        family_tree['children'] = None
    else:
        children = [[child[7], child[-1]] for child in children]
        family_tree['children'] = children

    return family_tree

def family_tree_to_html(conn, experiment_hash_id, FAMILY_TREE_FOLDER):
    family_tree = get_family_tree(conn, experiment_hash_id)
    parent = family_tree['parent']
    children = family_tree['children']
    self_exp = family_tree['self']
    G = nx.DiGraph()
    url_experiment = flask.url_for('experiment', id=self_exp[1])
    G.add_node(self_exp[0], color='blue', URL=url_experiment)
    if children is not None:
        for child in children:
            url_experiment = flask.url_for('experiment', id=child[1])
            G.add_node(child[0], color='green', URL=url_experiment)
            G.add_edge(self_exp[0], child[0])
    if parent is not None:
        url_experiment = flask.url_for('experiment', id=parent[1])
        G.add_node(parent[0], color='red', URL=url_experiment)
        G.add_edge(parent[0], self_exp[0])
    dot_save_path = os.path.join(FAMILY_TREE_FOLDER, f'{experiment_hash_id}.dot')
    html_save_path = os.path.join(FAMILY_TREE_FOLDER, f'{experiment_hash_id}.html')
    nx.nx_pydot.write_dot(G, f'{dot_save_path}')
    os.system(f'dot -Tsvg {dot_save_path} -o {html_save_path}')
    # read the html file and return it
    with open(html_save_path, 'r') as f:
        html = f.read()
    return html

def get_users(conn):
    cursor = conn.cursor()
    cursor.execute('select * from users')
    users = cursor.fetchall()

    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    columns = [column[1] for column in columns]
    users = [dict(zip(columns, user)) for user in users]
    return users