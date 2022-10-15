import sys
import requests
import os
import random
import string
sys.path.append('../database')
import operators

from datetime import datetime, date

def error_log(error):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)


def init_db(db_configs):
    print('Initilizing the databse')
    for table in db_configs.table_lists:
        operators.create_table(db_configs.conn, table)

def check_existence_table(db_configs):
    conn = db_configs.conn
    cursor = conn.cursor()
    #get the count of tables with the name
    cursor.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name=? ''', ['universities'])
    #if the count is 1, then table exists
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



def check_existence_tag(conn, tag):
    cursor = conn.cursor()
    cursor.execute('select * from tags where tag=?', (tag,))
    tags = cursor.fetchall()
    if len(tags)==0:
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


def apply_updates2db(db_configs):
    # add email_date to the database
    # cursor = db_configs.conn.cursor()
    # cursor.execute('SELECT * FROM universities')
    # cursor.execute('SELECT * FROM supervisors')
    # column_names = list(map(lambda x: x[0], cursor.description))
    # if 'email_date' not in column_names:
    #     cursor.execute('ALTER TABLE supervisors ADD COLUMN email_date timestamp')
    pass

def check_for_update():
    if check_for_internet_connection():
        file_url = 'https://github.com/MohammadAminAlamalhoda/Apply-Doc-Manager/blob/main/apply_doc_manager.py'
        readme_response = requests.get(file_url)
        text_repo = readme_response.text                   
        text_local = os.popen('cat apply_doc_manager.py').read()
        text_local = text_local.split('\n')[0]
        if text_local not in text_repo:
            return True
        else:
            return False
    else:
        return False

def check_for_internet_connection():
    try:
        requests.get('http://www.google.com')
        return True
    except requests.ConnectionError:
        return False

def email_date_check(supervisors):
    for supervisor_no, supervisor in enumerate(supervisors):
        if supervisor[4] == 'Yes':
            diff = calc_difference_dates(supervisor[12])
            supervisor = list(supervisor)
            if type(diff) == int:
                if diff == 0:
                    passed_days = 'Today'
                elif diff == 1:
                    passed_days = 'Yesterday'
                elif diff < 0:
                    passed_days = 'In the future!!'
                else:
                    passed_days = f'{diff} days ago'
            else:
                passed_days = diff
            supervisor[4] = passed_days
            supervisors[supervisor_no] = tuple(supervisor)
    return supervisors