import sys
import requests
import os
import random
import string
import json
import flask
import pathlib
from markupsafe import Markup
parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
sys.path.append(os.path.join(parent_parent_path, 'database'))
import operators
import networkx as nx
import zipfile
import shutil
import datetime as dt

from datetime import datetime, date

from typing import Union

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
    print('Initilizing the databse ...')
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
    cursor.execute('select * from entries where id_hash=?', (hash_id,))
    entries = cursor.fetchall()
    if len(entries)==0:
        return hash_id
    else:
        return generate_hash(conn)

def entry_list_maker(entries_list):
    entries_list = list(entries_list)
    for i, entry in enumerate(entries_list):
        entry = list(entry)
        entry[1] = parse_tags(entry[1])
        entry[6] = parse_conditions(entry[6])
        for j in range(len(entry[6])):
            if len(entry[6][j].split('&')) ==3:
                entry[6][j] = entry[6][j].split('&')[-1]
            else:
                entry[6][j] = '->'.join(entry[6][j].split('&')[-2:])
        entries_list[i] = entry
    return entries_list

def check_for_internet_connection():
    try:
        requests.get('http://www.google.com')
        return True
    except requests.ConnectionError:
        return False

def apply_updates2db(db_configs):
    cursor = db_configs.conn.cursor()
    cursor.execute('SELECT * FROM messages')
    column_names = list(map(lambda x: x[0], cursor.description))
    if 'destination' not in column_names:
        cursor.execute('ALTER TABLE messages ADD COLUMN destination text') 

def read_json_file(json_file):
    with open(json_file) as f:
        data = json.load(f)
    return data    

def modify_conditions_json(conditions, target_conditions):
    for condition in conditions.keys():
        for condition_nested in conditions[condition].keys():
            for indx, single_condition in enumerate(conditions[condition][condition_nested]):
                if len(single_condition.split('&')) == 2:
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
    # conditions = dict(sorted(conditions.items(), key=lambda item: item[0]))
    for condition in conditions.keys():
        conditions[condition] = dict(sorted(conditions[condition].items(), key=lambda item: item[0]))
    for condition in conditions.keys():
        for condition_nested in conditions[condition].keys():
            conditions[condition][condition_nested] = sorted(conditions[condition][condition_nested], key=lambda x: x[0])
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
        conditions_html = Markup(conditions_html)
        conditions_list.append([conditions_html, template_name])
    return conditions_list

def get_conditions_by_template_and_method(conn, app_config, username, templatename, method_name):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conditions_templates WHERE author=? AND template_name=?", (username, templatename))
    conditions_template = cursor.fetchall()    
    template_name = conditions_template[0][1]
    condition = conditions_template[0][2]
    condition_json = read_json_file(os.path.join(app_config['CONDITIONS_JSON_FOLDER'], f'{method_name}.json'))
    condition_json = modify_conditions_json(condition_json, condition)
    conditions_html = flask.render_template('conditions.html', conditions=condition_json, template_name=template_name)
    conditions_html = Markup(conditions_html)
    return conditions_html

def upload_files(app_config, hash_id, Files):
    folder_path = os.path.join(app_config['UPLOAD_FOLDER'], hash_id)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    for file in Files:
        if file.filename != '':
            file.save(os.path.join(folder_path, file.filename))

def remove_files(app_config, hash_id, file_names):
    for file_name in file_names:
        file_path = os.path.join(app_config['UPLOAD_FOLDER'], hash_id, file_name)
        os.remove(file_path)

def get_hash_id_by_entry_id(conn, id):
    cursor = conn.cursor()
    cursor.execute('select * from entries where id=?', (id,))
    entry = cursor.fetchone()
    hash_id = entry[0]
    return hash_id

def get_id_by_hash_id(conn, hash_id):
    cursor = conn.cursor()
    cursor.execute('select * from entries where id_hash=?', (hash_id,))
    entry = cursor.fetchone()
    id = entry[9]
    return id

def entry_report_maker(conn, entry_id):
    conn = conn
    cursor = conn.cursor()
    cursor.execute('select * from entries where id=?', (entry_id,))
    entry = cursor.fetchone()
    entry = list(entry)
    entry[1] = parse_tags(entry[1])
    entry[6] = parse_conditions(entry[6])
    for i in range(len(entry[6])):
        entry[6][i] = entry[6][i].replace('&', '->')
    report = f'Hash ID: {entry[0]}'
    report = report + f'\nParent Hash ID: {entry[8]}'
    report = report + f'\nName: {entry[7]}'
    report = report + f'\nAuthor: {entry[5]}'
    report = report + f'\nDate: {entry[4]}'
    report = report + f'\nFile Path: {entry[3]}'
    report = report + f'\nTags: {entry[1]}'
    report = report + f'\nConditions: {entry[6]}'
    return report

def check_hash_id_existence(conn, hash_id):
    cursor = conn.cursor()
    cursor.execute('select * from entries where id_hash=?', (hash_id,))
    entry = cursor.fetchone()
    if entry is None:
        return False
    else:
        return True

def load_creds(CREDS_FILE_PATH):
    with open(CREDS_FILE_PATH) as f:
        creds = json.load(f)
    return creds

def set_parent_entry(conn, entry_id, parent_hash_id):
    cursor = conn.cursor()
    cursor.execute('update entries set entry_parent=? where id=?', (parent_hash_id, entry_id))
    conn.commit()

def get_family_tree(conn, entry_hash_id):
    family_tree = {'parent': None, 'children': None, 'self': None}
    cursor = conn.cursor()
    cursor.execute('select * from entries where id_hash=?', (entry_hash_id,))
    entry = cursor.fetchone()
    entry = list(entry)
    entry_name = entry[7]
    parent_hash_id = entry[8]
    entry_id = entry[-1]
    family_tree['self'] = [entry_name, entry_id]

    if parent_hash_id is None or parent_hash_id == 'None' or parent_hash_id == '':
        family_tree['parent'] = None
    else:
        cursor.execute('select * from entries where id_hash=?', (parent_hash_id,))
        parent = cursor.fetchone()
        parent = list(parent)
        parent_name = parent[7]
        parent_id = parent[-1]
        family_tree['parent'] = [parent_name, parent_id]

    cursor.execute('select * from entries where entry_parent=?', (entry_hash_id,))
    children = cursor.fetchall()
    children = list(children)
    if len(children) == 0:
        family_tree['children'] = None
    else:
        children = [[child[7], child[-1]] for child in children]
        family_tree['children'] = children

    return family_tree

def family_tree_to_html(conn, entry_hash_id, FAMILY_TREE_FOLDER):
    family_tree = get_family_tree(conn, entry_hash_id)
    parent = family_tree['parent']
    children = family_tree['children']
    self_exp = family_tree['self']
    G = nx.DiGraph()
    url_entry = flask.url_for('entry', id=self_exp[1])
    G.add_node(self_exp[0], color='blue', URL=url_entry)
    if children is not None:
        for child in children:
            url_entry = flask.url_for('entry', id=child[1])
            G.add_node(child[0], color='green', URL=url_entry)
            G.add_edge(self_exp[0], child[0])
    if parent is not None:
        url_entry = flask.url_for('entry', id=parent[1])
        G.add_node(parent[0], color='red', URL=url_entry)
        G.add_edge(parent[0], self_exp[0])
    dot_save_path = os.path.join(FAMILY_TREE_FOLDER, f'{entry_hash_id}.dot')
    html_save_path = os.path.join(FAMILY_TREE_FOLDER, f'{entry_hash_id}.html')
    nx.nx_pydot.write_dot(G, f'{dot_save_path}')
    os.system(f'dot -Tsvg {dot_save_path} -o {html_save_path}')
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

def get_entry_by_id(conn, entry_id):
    cursor = conn.cursor()
    cursor.execute('select * from entries where id=?', (entry_id,))
    entry = cursor.fetchone()
    return entry

def restore_db(app_config, backup_file_path):
    try:
        parent_folder = os.path.dirname(backup_file_path)
        TEMP_FOLDER = os.path.join(parent_folder, 'temp_backup')
        with zipfile.ZipFile(backup_file_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_FOLDER)
        TEMP_FOLDER = os.path.join(TEMP_FOLDER, os.listdir(TEMP_FOLDER)[0])
        for folder in os.listdir(TEMP_FOLDER):
            folder_path = os.path.join(TEMP_FOLDER, folder)
            if os.path.isdir(folder_path):
                shutil.rmtree(os.path.join(app_config['DATABASE_FOLDER'], folder))
                shutil.copytree(folder_path, os.path.join(app_config['DATABASE_FOLDER'], folder))
            elif os.path.isfile(folder_path):
                os.remove(os.path.join(app_config['DATABASE_FOLDER'], folder))
                shutil.copyfile(folder_path, os.path.join(app_config['DATABASE_FOLDER'], folder))
        shutil.rmtree(TEMP_FOLDER)
        os.remove(backup_file_path)
        return True
    except:
        return False

def backup_db(app_config):
    backup_file_path = os.path.join(app_config['DATABASE_FOLDER'], 'DataManager_backup')
    try:
        parent_folder = os.path.dirname(backup_file_path)
        time_now = datetime.now()
        time_now = time_now.strftime('%Y-%m-%d_%H-%M')
        TEMP_FOLDER = os.path.join(parent_folder, 'backup_datamanager', time_now)
        if os.path.exists(TEMP_FOLDER):
            shutil.rmtree(TEMP_FOLDER)
        # make TEMP_FOLDER and its parents if they don't exist
        os.makedirs(TEMP_FOLDER)

        for folder in ['db_main.db', 'conditions', 'uploaded_files']:
            folder_path = os.path.join(app_config['DATABASE_FOLDER'], folder)
            if os.path.isdir(folder_path):
                shutil.copytree(folder_path, os.path.join(TEMP_FOLDER, folder))
            elif os.path.isfile(folder_path):
                shutil.copyfile(folder_path, os.path.join(TEMP_FOLDER, folder))
        TEMP_FOLDER = os.path.dirname(TEMP_FOLDER)
        shutil.make_archive(backup_file_path, 'zip', TEMP_FOLDER)
        shutil.rmtree(TEMP_FOLDER)
        backup_file_path = f'{backup_file_path}.zip'
        return True, backup_file_path
    except:
        return False, backup_file_path
    
def get_methods_list(app_config):
    methods_list = os.listdir(app_config['CONDITIONS_JSON_FOLDER'])
    methods_list = [method_name.split('.')[0] for method_name in methods_list]    
    methods_list.remove(app_config['CONDITIONS_JSON_DEFAULT'].split('.')[0])
    methods_list.insert(0, app_config['CONDITIONS_JSON_DEFAULT'].split('.')[0])
    return methods_list

def send_order_notification(conn, recipient_username, subject, message):
    """Send email notification for order-related events"""
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE username=?", (recipient_username,))
    result = cursor.fetchone()
    
    if result and result[0]:  # If user has email
        # Add message to messages table
        cursor.execute("""
            INSERT INTO messages (author, message, date, destination)
            VALUES (?, ?, ?, ?)
        """, ('system', message, dt.datetime.now(), recipient_username))
        conn.commit()
        
        # Send email
        send_email(
            to=result[0],
            subject=subject,
            body=message
        )
        return True
    return False


def get_email_address_by_user_name(conn, user_name):
    cursor = conn.cursor()
    cursor.execute('select * from users where username=?', (user_name,))
    user = cursor.fetchone()
    columns = [column[0] for column in cursor.description]
    user = dict(zip(columns, user))
    return user['email']

def check_emails_validity(emails: Union[list, tuple]) -> bool:
    for email in emails:
        if '@' not in email or '.' not in email:
            return False
    return True