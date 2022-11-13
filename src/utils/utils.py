import sys
import requests
import os
import random
import string
import json
import flask
sys.path.append('../database')
import operators

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
    # cursor = db_configs.conn.cursor()
    # cursor.execute('SELECT * FROM universities')
    # cursor.execute('SELECT * FROM supervisors')
    # column_names = list(map(lambda x: x[0], cursor.description))
    # if 'email_date' not in column_names:
    #     cursor.execute('ALTER TABLE supervisors ADD COLUMN email_date timestamp')
    pass

def read_json_file(json_file):
    with open(json_file) as f:
        data = json.load(f)
    return data    

def modify_conditions_json(conditions, target_conditions):
    for condition in conditions.keys():
        for condition_nested in conditions[condition].keys():
            for indx, single_condition in enumerate(conditions[condition][condition_nested]):
                if f'{condition}&{condition_nested}&{single_condition}' in target_conditions:
                    conditions[condition][condition_nested][indx] = [single_condition, "checked"]
                else:
                    conditions[condition][condition_nested][indx] = [single_condition, ""]
    return conditions