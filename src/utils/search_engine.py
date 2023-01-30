import flask
from flask import jsonify
import utils

def author_search_in_db(conn, keyword):
    if keyword != '' and keyword != ' ':
        try:
            cursor = conn.cursor()
            cursor.execute("select *  FROM authors WHERE author LIKE ?", (f"%{keyword}%",))
            result = cursor.fetchall()
        except:
            result = None
    else:
        result = None
    return jsonify(result)

def tags_search_in_db(conn, keyword):
    if keyword != '' and keyword != ' ':
        keyword = keyword.split(',')
        keyword = keyword[-1]
        try:
            cursor = conn.cursor()
            cursor.execute("select *  FROM tags WHERE tag LIKE ?", (f"%{keyword}%",))
            result = cursor.fetchall()
        except:
            result = None
    else:
        result = None
    return jsonify(result)

def text_search_in_db(conn, keyword):
    print(keyword)
    if keyword != '' and keyword != ' ':
        try:
            cursor = conn.cursor()
            cursor.execute("select *  FROM experiments WHERE extra_txt LIKE ?", (f"%{keyword}%",))
            result = cursor.fetchall()
        except:
            result = None
    else:
        result = None
    for i,r in enumerate(result):
        r = list(r)
        index = r[2].find(keyword)
        r[2] = r[2][index-20:index+20]
        r = [r[2], r[-1]]
        result[i] = tuple(r)
    return jsonify(result)

def filter_experiments(conn, post_request_form):
    Authors = post_request_form['Author']
    Hash_ID = post_request_form['Hash_ID']
    Text = post_request_form['Text']
    Tags = post_request_form['Tags']
    if 'date_bool' not in post_request_form:
        date_bool = False
    else:
        date_bool = True
    if not date_bool:
        date_start = '0001-01-01'
        date_end = '9999-12-31'
    else:
        date_start = post_request_form['date_start']
        date_end = post_request_form['date_end']
    conditions = []
    for form_input in post_request_form:
        if 'condition' == form_input.split('&')[0]:
                conditions.append('&'.join(form_input.split('&')[1:]))
        elif 'PARAM' == form_input.split('&')[0]:
            list_tmp = form_input.split('&')[2:]
            list_tmp.append(post_request_form[f"PARAMVALUE&{'&'.join(form_input.split('&')[1:])}"].split('&')[-1])
            list_tmp = '&'.join(list_tmp)
            conditions.append(list_tmp)
    conditions = ','.join(conditions)

    rows = []
    if Hash_ID != '':
        sql_command = 'SELECT * FROM experiments WHERE id_hash like ? AND ' 
        rows.append(f'%{Hash_ID}%')
    else:
        sql_command = 'SELECT * FROM experiments WHERE '
        if Authors != '':
            sql_command += 'author == ? AND '
            rows.append(Authors)
        if Text != '':
            sql_command += 'extra_txt like ? AND '
            rows.append(f'%{Text}%')
        if date_start != '':
            sql_command += 'date >= ? AND '
            rows.append(date_start)
        if date_end != '':
            sql_command += 'date <= ? AND '
            rows.append(date_end)
        if Tags != '':
            Tags = Tags.split(',')
            for tag in Tags:
                if tag != '':
                    sql_command += 'tags like ? AND '
                    rows.append(f'%{tag}%')
        if conditions != '':
            conditions = conditions.split(',')
            for condition in conditions:
                if condition != '':
                    sql_command += 'conditions like ? AND '
                    rows.append(f'%{condition}%')
    sql_command = sql_command + '1'
    rows = tuple(rows)
    cursor = conn.cursor()
    cursor.execute(sql_command, rows)
    experiments_list = cursor.fetchall()
    experiments_list=  utils.experiment_list_maker(experiments_list)
    return experiments_list

def experiments_time_line(conn):
    cursor = conn.cursor()
    if flask.session['admin']:
        cursor.execute("SELECT * FROM experiments ORDER BY date DESC LIMIT 12")         
    else:
        cursor.execute("SELECT * FROM experiments WHERE author == ? ORDER BY date DESC LIMIT 12", (flask.session['username'],))                              
    experiments_list = cursor.fetchall()
    experiments_list=  utils.experiment_list_maker(experiments_list)
    return experiments_list
    