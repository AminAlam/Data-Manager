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
import mailing
import datetime as dt
import logging
import csv
import io
from datetime import datetime, date

from typing import Union

# Define log directory
log_dir = os.path.join(parent_parent_path, 'logs')

def create_log(log_name, log_level=logging.INFO):
    """Create a logger with the specified name and level.
    
    Args:
        log_name (str): Name of the log file
        log_level (int): Logging level (default: logging.INFO)
        
    Returns:
        logging.Logger: Configured logger object
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    
    # Create file handler
    log_file = os.path.join(log_dir, f"{log_name}.log")
    file_handler = logging.FileHandler(log_file)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

def error_log(error):
    """Log an error with traceback information.
    
    Args:
        error: The error to log
    """
    exc_type, exc_obj, exc_tb = sys.exc_info()
    
    # Handle case where there's no traceback (e.g., when called directly with an error)
    if exc_tb is None:
        print(f"Error: {str(error)}")
        
        # Also log to error log file
        os.makedirs(log_dir, exist_ok=True)
        error_logger = create_log('error_log')
        error_logger.error(f"Error without traceback: {str(error)}")
        return
        
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    
    # Also log to error log file
    os.makedirs(log_dir, exist_ok=True)
    error_logger = create_log('error_log')
    error_logger.error(f"{exc_type} in {fname} at line {exc_tb.tb_lineno}: {str(error)}")

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
    cursor.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name=? ''', ['users'])
    if cursor.fetchone()[0]==1:
        return True
    else:
        return False

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
    result_entries = []
    for entry in entries_list:
        # Convert SQLite Row to dict if needed
        if hasattr(entry, 'keys'):  # Check if it's a Row-like object
            entry_dict = dict(entry)
        else:
            entry_dict = dict(zip(range(len(entry)), entry))
        
        # Process tags if they exist
        if 'tags' in entry_dict and entry_dict['tags']:
            entry_dict['tags'] = parse_tags(entry_dict['tags'])
        elif 1 in entry_dict and entry_dict[1]:  # Using numeric index
            entry_dict[1] = parse_tags(entry_dict[1])
            
        # Process conditions if they exist
        if 'conditions' in entry_dict and entry_dict['conditions']:
            conditions = parse_conditions(entry_dict['conditions'])
            processed_conditions = []
            for condition in conditions:
                if len(condition.split('&')) == 3:
                    processed_conditions.append(condition.split('&')[-1])
                else:
                    processed_conditions.append('->'.join(condition.split('&')[-2:]))
            entry_dict['conditions'] = processed_conditions
        elif 6 in entry_dict and entry_dict[6]:  # Using numeric index
            conditions = parse_conditions(entry_dict[6])
            processed_conditions = []
            for condition in conditions:
                if len(condition.split('&')) == 3:
                    processed_conditions.append(condition.split('&')[-1])
                else:
                    processed_conditions.append('->'.join(condition.split('&')[-2:]))
            entry_dict[6] = processed_conditions
            
        result_entries.append(entry_dict)
    
    return result_entries

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
    
    # Import migration functions
    sys.path.append(os.path.join(parent_parent_path, 'database'))
    from database.migrate import add_api_key_to_users_table
    
    # Apply api_key column migration
    add_api_key_to_users_table(db_configs.conn)

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
    try:
        folder_path = os.path.join(app_config['UPLOAD_FOLDER'], hash_id)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            print(f"Folder created: {folder_path}")
        
        uploaded_files = []
        for file in Files:
            if file and file.filename and file.filename != '':
                # Sanitize filename to prevent path traversal
                safe_filename = os.path.basename(file.filename)
                file_path = os.path.join(folder_path, safe_filename)
                
                try:
                    file.save(file_path)
                    uploaded_files.append(safe_filename)
                except Exception as e:
                    error_log(f"Error saving file {safe_filename}: {str(e)}")
        
        return True, uploaded_files
    except Exception as e:
        error_log(f"Error in upload_files: {str(e)}")
        return False, []

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
    report = f"""
    <table>
        <tr>
            <th>Field</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Hash ID</td>
            <td>{entry[0]}</td>
        </tr>
        <tr>
            <td>Parent Hash ID</td>
            <td>{entry[8]}</td>
        </tr>
        <tr>
            <td>Name</td>
            <td>{entry[7]}</td>
        </tr>
        <tr>
            <td>Author</td>
            <td>{entry[5]}</td>
        </tr>
        <tr>
            <td>Date</td>
            <td>{entry[4]}</td>
        </tr>
        <tr>
            <td>File Path</td>
            <td>{entry[3]}</td>
        </tr>
        <tr>
            <td>Tags</td>
            <td>{entry[1]}</td>
        </tr>
        <tr>
            <td>Conditions</td>
            <td>{entry[6]}</td>
        </tr>
    </table>
    """
    return report

def bulk_entry_report_maker(conn, entries_ids):
    # make a csv file with the report for the entries
    report = []
    for entry_id in entries_ids:
        cursor = conn.cursor()
        cursor.execute('select * from entries where id=?', (entry_id,))
        entry = cursor.fetchone()
        column_names = list(map(lambda x: x[0], cursor.description))
        entry = list(entry)
        entry[1] = parse_tags(entry[1])
        entry[6] = parse_conditions(entry[6])
        for i in range(len(entry[6])):
            entry[6][i] = entry[6][i].replace('&', '->')

        report.append(entry)

    # Use StringIO instead of BytesIO for working with text
    report_str = io.StringIO()
    writer = csv.writer(report_str)
    
    # Write column names
    writer.writerow(column_names)
    
    # Write all row data
    for row in report:
        writer.writerow(row)
    
    # Convert to bytes when done
    report_bytes = io.BytesIO()
    report_bytes.write(report_str.getvalue().encode('utf-8'))
    report_bytes.seek(0)
    return report_bytes
            
    

def check_hash_id_existence(conn, hash_id):
    cursor = conn.cursor()
    cursor.execute('select * from entries where id_hash=?', (hash_id,))
    entry = cursor.fetchone()
    if entry is None:
        return False
    else:
        return True

def load_creds(CREDS_FILE_PATH=None):
    """
    Load credentials from environment variables.
    The CREDS_FILE_PATH parameter is kept for backward compatibility but is no longer used.
    """
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Create a dictionary with the same structure as the original creds.json
    creds = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "RECAPTCHA_PUBLIC_KEY": os.environ.get("RECAPTCHA_PUBLIC_KEY", ""),
        "RECAPTCHA_PRIVATE_KEY": os.environ.get("RECAPTCHA_PRIVATE_KEY", ""),
        "SENDER_EMAIL_ADDRESS": os.environ.get("SENDER_EMAIL_ADDRESS", ""),
        "SENDER_EMAIL_PASSWORD": os.environ.get("SENDER_EMAIL_PASSWORD", "")
    }
    
    return creds


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
    """Get all users with their details"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, password, admin, order_manager, name, email, email_enabled, id 
        FROM users
    """)
    users = cursor.fetchall()
    return [{
        'username': user[0],
        'password': user[1],
        'admin': user[2],
        'order_manager': user[3],
        'name': user[4],
        'email': user[5],
        'email_enabled': user[6],
        'id': user[7]
    } for user in users]

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


def check_emails_validity(emails: Union[list, tuple]) -> bool:
    """Check if all emails in a list are valid.
    
    Args:
        emails (Union[list, tuple]): List of email addresses to check
        
    Returns:
        bool: True if all emails are valid, False otherwise
    """
    if not emails:
        return False
    return all(is_valid_email(email) for email in emails)

def is_valid_email(email: str) -> bool:
    """Check if an email address is valid.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if the email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
        
    # Basic email validation
    import re
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))

