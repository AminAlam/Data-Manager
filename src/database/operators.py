import sys
import pathlib
import os
parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
sys.path.append(os.path.join(parent_parent_path, 'utils'))

import utils
from dictianory import slef_made_codes
import sqlite3
from sqlite3 import Error
import itertools
import hashlib
import datetime as dt

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        print('Connected to database using SQLite')
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        utils.error_log(e)

### User Operations ###
def add_user(conn, username, password, admin, order_manager, name, email, email_enabled=1):
    try:
        cursor = conn.cursor()
        hashed_password = hash_password(password)
        cursor.execute('insert into users (username, password, admin, order_manager, name, email, email_enabled) values (?,?,?,?,?,?,?)', 
                      (username, hashed_password, admin, order_manager, name, email, email_enabled))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def update_user(conn, form_data, user_id):
    try:
        cursor = conn.cursor()
        
        # Check if password needs to be updated
        if form_data.get('password'):
            hashed_password = hash_password(form_data['password'])
            form_data['password'] = hashed_password
            
        # Build the update query dynamically based on available fields
        update_fields = []
        params = []
        
        if 'password' in form_data and form_data['password']:
            update_fields.append("password=?")
            params.append(form_data['password'])
            
        if 'name' in form_data:
            update_fields.append("name=?")
            params.append(form_data['name'])
            
        if 'email' in form_data:
            update_fields.append("email=?")
            params.append(form_data['email'])
            
        if 'email_enabled' in form_data:
            update_fields.append("email_enabled=?")
            params.append(form_data['email_enabled'])
            
        if 'admin' in form_data:
            update_fields.append("admin=?")
            params.append(form_data['admin'])
            
        if 'order_manager' in form_data:
            update_fields.append("order_manager=?")
            params.append(form_data['order_manager'])
            
        if not update_fields:
            return False  # Nothing to update
            
        # Add the WHERE clause parameter
        params.append(user_id)
        
        # Execute the update
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
        cursor.execute(query, tuple(params))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def delete_user(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute('delete from users where id=?', (user_id,))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def get_users(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to list of dictionaries
        users_list = []
        for user in users:
            users_list.append(dict(zip(columns, user)))
            
        return users_list
    except Error as e:
        utils.error_log(e)
        return []

def get_user_by_username(conn, username):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        
        if not user:
            return None
            
        # Get column names
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to dictionary
        return dict(zip(columns, user))
    except Error as e:
        utils.error_log(e)
        return None

def get_user_by_id(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return None
            
        # Get column names
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to dictionary
        return dict(zip(columns, user))
    except Error as e:
        utils.error_log(e)
        return None

### Entry Operations ###
def insert_entry_to_db(conn, Author, date, Tags, File_Path, Notes, conditions, entry_name, parent_entry):
    try:
        conditions_parsed = utils.parse_conditions(conditions)
        Tags_parsed = utils.parse_tags(Tags)
        insert_tag(conn, Tags_parsed)
        insert_conditions(conn, conditions_parsed)
        insert_author(conn, Author)
        cursor = conn.cursor()
        hash_id = utils.generate_hash(conn)
        rows = [(hash_id, Tags, Notes, File_Path, date, Author, conditions, entry_name, parent_entry, None)]
        cursor.executemany('insert into entries values (?,?,?,?,?,?,?,?,?,?)', rows)
        conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
        hash_id = None
    return success_bool, hash_id

def update_entry_in_db(conn, id, post_form, app_config, hash_id, Files):
    try:
        date = post_form['date']
        Tags = post_form['Tags']
        File_Path = post_form['File_Path']
        Notes = post_form['Notes']
        entry_name = post_form['entry_name']
        parent_entry = post_form['parent_entry']

        Tags_parsed = utils.parse_tags(Tags)
        insert_tag(conn, Tags_parsed)

        # Handle file uploads
        if len(Files) > 0:
            upload_success, uploaded_files = utils.upload_files(app_config, hash_id, Files)
            if not upload_success:
                utils.error_log("Failed to upload files")
                # Continue with the update even if file upload fails

        # Handle file removals
        Files2remove = []
        for form_input in post_form:
            try:
                if slef_made_codes[form_input.split('&')[0]] == 'remove':
                    Files2remove.append(form_input.split('&')[1])
            except:
                pass

        if len(Files2remove) > 0:
            utils.remove_files(app_config, hash_id, Files2remove)

        # Process conditions
        conditions = []
        for form_input in post_form:
            if 'condition' == form_input.split('&')[0]:
                conditions.append('&'.join(form_input.split('&')[1:]))
            elif 'PARAM' == form_input.split('&')[0]:
                list_tmp = form_input.split('&')[2:]
                list_tmp.append(post_form[f"PARAMVALUE&{'&'.join(form_input.split('&')[1:])}"].split('&')[-1])
                list_tmp = '&'.join(list_tmp)
                conditions.append(list_tmp)
                
        conditions = ','.join(conditions)
        
        # Update the database
        cursor = conn.cursor()
        rows = [(Tags, Notes, File_Path, date, conditions, entry_name, parent_entry, id)]
        cursor.executemany('update entries set tags=?, extra_txt=?, file_path=?, date=?, conditions=?, entry_name=?, entry_parent=? where id=?', rows)
        conn.commit()
        success_bool = 1

    except Exception as e:
        utils.error_log(e)
        success_bool = 0
    
    return success_bool

def delete_entry_from_db(conn, id):
    try:
        hash_id = utils.get_hash_id_by_entry_id(conn, id)
        cursor = conn.cursor()
        cursor.execute('delete from entries where id=?', (id,))
        conn.commit()
        remove_deleted_entry_as_parent(conn, hash_id)
        delete_author(conn, id)
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool

def remove_deleted_entry_as_parent(conn, hash_id):
    try:
        cursor = conn.cursor()
        cursor.execute("update entries set entry_parent='' where entry_parent=?", (hash_id,))
        conn.commit()
        success_bool = 1
    except Error as e:
        utils.error_log(e)
        success_bool = 0
    return success_bool

def get_entry_by_id(conn, entry_id):
    try:
        cursor = conn.cursor()
        # If entry_id is a tuple (success_bool, hash_id), extract the id
        if isinstance(entry_id, tuple) and len(entry_id) == 2:
            # Check if the first element is success_bool and it's 1 (success)
            if entry_id[0] == 1:
                # Use the hash_id to find the entry
                cursor.execute("SELECT * FROM entries WHERE id_hash=?", (entry_id[1],))
            else:
                print(f"Entry insertion was not successful: {entry_id}")
                return None
        else:
            # Use the id directly
            cursor.execute("SELECT * FROM entries WHERE id=?", (entry_id,))
        
        entry = cursor.fetchone()
        if entry:
            # Convert SQLite Row to dictionary for better serialization
            if hasattr(entry, 'keys'):
                # If it's a Row-like object with keys method
                entry_dict = {key: entry[key] for key in entry.keys()}
            else:
                # Fallback to index-based access if it's a tuple
                columns = [column[0] for column in cursor.description]
                entry_dict = {columns[i]: entry[i] for i in range(len(columns))}
            return entry_dict
        else:
            print(f"No entry found with ID: {entry_id}")
            return None
    except Error as e:
        utils.error_log(e)
        print(f"{type(e)} operators.py 269")
        print(f"Error retrieving entry with ID {entry_id}: {e}")
        return None

def get_hash_id_by_entry_id(conn, entry_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_hash FROM entries WHERE id=?", (entry_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Error as e:
        utils.error_log(e)
        return None

def get_id_by_hash_id(conn, hash_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entries WHERE id_hash=?", (hash_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Error as e:
        utils.error_log(e)
        return None

def check_hash_id_existence(conn, hash_id):
    if not hash_id or hash_id == '':
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entries WHERE id_hash=?", (hash_id,))
        count = cursor.fetchone()[0]
        return count > 0
    except Error as e:
        utils.error_log(e)
        return False

### Tags Operations ###
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

def get_all_tags(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT tag FROM tags")
        tags = cursor.fetchall()
        return [tag[0] for tag in tags]
    except Error as e:
        utils.error_log(e)
        return []

### Authors Operations ###
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

def get_all_authors(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT author FROM authors")
        authors = cursor.fetchall()
        return [author[0] for author in authors]
    except Error as e:
        utils.error_log(e)
        return []

### Conditions Operations ###
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

def update_conditions_templates(conn, post_form, username):
    post_form = post_form.to_dict()
    new_template_name = post_form['new_template_name']
    template_delete_bool = False

    for key, _ in post_form.items():
        if 'delete' == key.split('&')[0]:
            # remove template
            template_name = key.split('&')[1]
            cursor = conn.cursor()
            cursor.execute('delete from conditions_templates where author=? and template_name=?', (username, template_name))
            conn.commit()
            template_delete_bool = True
    if new_template_name.replace(' ', '') == '' and template_delete_bool == False:
        return False
    elif new_template_name.replace(' ', '') == '' and template_delete_bool == True:
        return True

    conditions = []
    for key, _ in post_form.items():
        if 'condition' == key.split('&')[0]:
            conditions.append(key.split('&')[1:])
        elif 'PARAM' == key.split('&')[0]:
            list_tmp = key.split('&')[2:]
            list_tmp.append(post_form[f"PARAMVALUE&{'&'.join(key.split('&')[1:])}"].split('&')[-1])
            conditions.append(list_tmp)
    conditions_dict = {}
    for key, group in itertools.groupby(conditions, lambda x: x[0]):
        conditions_dict[key] = list(group)
    for template_name in conditions_dict.keys():
        condition_this_template_list = conditions_dict[template_name]
        for indx, condition_this_template in enumerate(condition_this_template_list):
            condition_this_template_list[indx] = '&'.join(condition_this_template[1:])
        condition_this_template_list = ','.join(condition_this_template_list)
        cursor = conn.cursor()
        if template_name == 'default':
            cursor.execute('insert into conditions_templates values (?, ?, ?, ?)', (username, new_template_name, condition_this_template_list, None))
        elif template_name != '':
            cursor.execute('update conditions_templates set conditions=? where author=? and template_name=?', (condition_this_template_list, username, template_name))
        conn.commit()

    return True
def get_conditions_by_template_and_method(conn, username, template_name, method_name):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT conditions FROM conditions_templates WHERE author=? AND template_name=?", 
                      (username, template_name))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Error as e:
        utils.error_log(e)
        return None

### Password Operations ###
def hash_password(password):
    """Hash a password with a random salt using SHA-256"""
    salt = os.urandom(32)  # 32 bytes = 256 bits
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',  # Hash algorithm
        password.encode('utf-8'),  # Convert password to bytes
        salt,  # Salt
        100000,  # Number of iterations
    )
    # Store salt and hash together
    return salt.hex() + ':' + hash_obj.hex()

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    if not stored_password or ':' not in stored_password:
        # Handle legacy plain text passwords
        return stored_password == provided_password
        
    salt_hex, hash_hex = stored_password.split(':')
    salt = bytes.fromhex(salt_hex)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        provided_password.encode('utf-8'),
        salt,
        100000,
    )
    return hash_obj.hex() == hash_hex

### Order Operations ###
def get_orders(conn, search_term='', author_term='', status_filter='', date_start='', date_end='', limit=10, offset=0):
    try:
        # Build the query
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND order_name LIKE ?"
            params.append(f'%{search_term}%')
        
        if author_term:
            # Split author terms by comma and create OR conditions
            author_terms = [term.strip() for term in author_term.split(',') if term.strip()]
            if author_terms:
                author_conditions = []
                for term in author_terms:
                    author_conditions.append("order_author LIKE ?")
                    params.append(f'%{term}%')
                query += f" AND ({' OR '.join(author_conditions)})"
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        if date_start:
            query += " AND date >= ?"
            params.append(date_start)
        
        if date_end:
            query += " AND date <= ?"
            # Add 23:59:59 to include the entire end day
            params.append(f"{date_end} 23:59:59")
        
        # Add ordering and pagination
        query += " ORDER BY date DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)
        
        # Execute the query
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        orders = cursor.fetchall()
        
        # Convert to dict with column names
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        return [dict(zip(columns, order)) for order in orders]
    except Error as e:
        utils.error_log(e)
        return []

def get_order_by_id(conn, order_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return None
            
        # Get column names
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to dictionary
        return dict(zip(columns, order))
    except Error as e:
        utils.error_log(e)
        return None

def submit_order(conn, order_data):
    try:
        cursor = conn.cursor()
        
        # Extract order data
        order_name = order_data.get('order_name')
        link = order_data.get('link')
        quantity = order_data.get('quantity')
        note = order_data.get('note')
        order_assignee = order_data.get('order_assignee')
        order_author = order_data.get('order_author')
        status = order_data.get('status', 'pending')
        date = order_data.get('date', dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Insert the order
        cursor.execute(
            'INSERT INTO orders (order_name, link, quantity, note, order_assignee, order_author, status, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (order_name, link, quantity, note, order_assignee, order_author, status, date)
        )
        conn.commit()

        # Get the ID of the inserted order
        order_id = cursor.lastrowid
        return True, order_id
    except Error as e:
        utils.error_log(e)
        return False, None

def update_order(conn, order_id, order_data):
    try:
        cursor = conn.cursor()
        
        # Build the update query dynamically based on available fields
        update_fields = []
        params = []
        
        if 'order_name' in order_data:
            update_fields.append("order_name=?")
            params.append(order_data['order_name'])
            
        if 'link' in order_data:
            update_fields.append("link=?")
            params.append(order_data['link'])
            
        if 'quantity' in order_data:
            update_fields.append("quantity=?")
            params.append(order_data['quantity'])
            
        if 'note' in order_data:
            update_fields.append("note=?")
            params.append(order_data['note'])
            
        if 'order_assignee' in order_data:
            update_fields.append("order_assignee=?")
            params.append(order_data['order_assignee'])
            
        if 'status' in order_data:
            update_fields.append("status=?")
            params.append(order_data['status'])
            
        if not update_fields:
            return False  # Nothing to update
            
        # Add the WHERE clause parameter
        params.append(order_id)
        
        # Execute the update
        query = f"UPDATE orders SET {', '.join(update_fields)} WHERE id=?"
        cursor.execute(query, tuple(params))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def delete_order(conn, order_id):
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM orders WHERE id=?', (order_id,))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

### Notification Operations ###
def add_notification(conn, author, message, destination, notification_type, reference_id=None):
    # try:
        cursor = conn.cursor()
        now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO notifications (author, message, date, destination, read, type, reference_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (author, message, now, destination, 0, notification_type, reference_id)
        )
        conn.commit()
        return True
    # except Error as e:
    #     utils.error_log(e)
    #     return False

def get_notifications(conn, username, limit=10, offset=0):
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, author, message, date, destination, read, type, reference_id 
               FROM notifications 
               WHERE destination = ? 
               ORDER BY date DESC LIMIT ? OFFSET ?''',
            (username, limit, offset)
        )
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'author': row[1],
                'message': row[2],
                'date': row[3],
                'recipient': row[4],
                'read': row[5],
                'type': row[6],
                'reference_id': row[7]
            })
        return notifications
    except Error as e:
        utils.error_log(e)
        return []

def mark_notification_read(conn, notification_id):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def get_unread_notification_count(conn, username):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE destination=? AND read=0", (username,))
        count = cursor.fetchone()[0]
        return count
    except Error as e:
        utils.error_log(e)
        return 0

### Log Operations ###
def add_log(conn, username, action, status='pass', error=None):
    try:
        cursor = conn.cursor()
        time = dt.datetime.now()
        cursor.execute('INSERT INTO logs VALUES (?,?,?,?,?,?)', 
                      (username, action, time, status, error, None))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def get_recent_logs(conn, days=7):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE date > date('now', '-' || ? || ' days')", (days,))
        logs = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to list of dictionaries
        return [dict(zip(columns, log)) for log in logs]
    except Error as e:
        utils.error_log(e)
        return []

### Password Reset Operations ###
def create_password_reset_token(conn, username, token, expiry):
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO password_resets (username, token, expiry) VALUES (?, ?, ?)',
                      (username, token, expiry))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def get_password_reset_token(conn, token):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM password_resets WHERE token=?', (token,))
        result = cursor.fetchone()
        
        if not result:
            return None
            
        # Get column names
        cursor.execute("PRAGMA table_info(password_resets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Convert to dictionary
        return dict(zip(columns, result))
    except Error as e:
        utils.error_log(e)
        return None

def delete_password_reset_token(conn, token):
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM password_resets WHERE token=?', (token,))
        conn.commit()
        return True
    except Error as e:
        utils.error_log(e)
        return False

def get_email_address_by_user_name(conn, user_name):
    cursor = conn.cursor()
    cursor.execute('SELECT email, email_enabled FROM users WHERE username=?', (user_name,))
    user = cursor.fetchone()
    if not user or not user[1]:  # If user doesn't exist or email is disabled
        return None
    return user[0]

def get_column_names(conn, table_name):
    """Get column names for a specified table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]  # Column name is the second field
    return column_names

def set_parent_entry(conn, entry_id, parent_hash_id):
    cursor = conn.cursor()
    cursor.execute('update entries set entry_parent=? where id=?', (parent_hash_id, entry_id))
    conn.commit()