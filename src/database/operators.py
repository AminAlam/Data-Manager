import sys
sys.path.append('../utils')

import utils
import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        print('Connected to database using SQLite', sqlite3.version)
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        utils.error_log(e)


### Experiments
def insert_experiment_to_db(conn, Author, date, Tags, File_Path, Notes, conditions):
    try:
        conditions_parsed = utils.parse_conditions(conditions)
        Tags_parsed = utils.parse_tags(Tags)
        insert_tag(conn, Tags_parsed)
        insert_conditions(conn, conditions_parsed)
        insert_author(conn, Author)
        cursor = conn.cursor()
        hash_id = utils.generate_hash(conn)
        rows = [(hash_id, Tags, Notes, File_Path, date, Author, conditions, None)]
        cursor.executemany('insert into experiments values (?,?,?,?,?,?,?,?)', rows)
        conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
        hash_id = None
    return success_bool, hash_id

def update_experiment_in_db(conn, id, post_form):
    try:
        Author = post_form['Author']
        date = post_form['date']
        Tags = post_form['Tags']
        File_Path = post_form['File_Path']
        Notes = post_form['Notes']
        cursor = conn.cursor()
        rows = [(Tags, Notes, File_Path, date, Author, id)]
        cursor.executemany('update experiments set tags=?, extra_txt=?, file_path=?, date=?, author=? where id=?', rows)
        conn.commit()

        if not utils.check_existence_author(conn, Author):
            insert_author(conn, Author)
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool

def delete_experiment_from_db(conn, id):
    try:
        cursor = conn.cursor()
        cursor.execute('delete from experiments where id=?', (id,))
        conn.commit()
        delete_author(conn, id)
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool
### Experiments



### Tags
def insert_tag(conn, Tags_parsed):
    try:
        for tag in Tags_parsed:
            if not utils.check_existence_tag(conn, tag):
                cursor = conn.cursor()
                rows = [(tag, None)]
                cursor.executemany('insert into tags values (?, ?)', rows)
                conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool
### Tags


### Authors
def insert_author(conn, Author):
    try:
        if not utils.check_existence_author(conn, Author):
            cursor = conn.cursor()
            rows = [(Author, None)]
            cursor.executemany('insert into authors values (?, ?)', rows)
            conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool

def delete_author(conn, id):
    if not utils.check_existence_author(conn, id):
        cursor = conn.cursor()
        cursor.execute('delete from authors where id=?', (id,))
        conn.commit()
### Authors

### Conditions
def insert_conditions(conn, conditions):
    try:
        for condition in conditions:
            if not utils.check_existence_condition(conn, condition):
                cursor = conn.cursor()
                rows = [(condition, None)]
                cursor.executemany('insert into conditions values (?, ?)', rows)
                conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool
### Conditions