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
            cursor.execute("select *  FROM entries WHERE extra_txt LIKE ?", (f"%{keyword}%",))
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

def title_search_in_db(conn, keyword):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT entry_name FROM entries WHERE entry_name LIKE ? LIMIT 10", (f'%{keyword}%',))
    results = cursor.fetchall()
    return flask.jsonify(results)

def filter_entries(conn, post_request_form):
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
        sql_command = 'SELECT * FROM entries WHERE id_hash like ? AND ' 
        rows.append(f'%{Hash_ID}%')
    else:
        sql_command = 'SELECT * FROM entries WHERE '
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
                if len(condition.split('&')) == 5:
                    condition = '&'.join(condition.split('&')[:-1])
                if condition != '':
                    sql_command += 'conditions like ? AND '
                    rows.append(f'%{condition}%')
    sql_command = sql_command + '1'
    rows = tuple(rows)
    cursor = conn.cursor()
    cursor.execute(sql_command, rows)
    entries_list = cursor.fetchall()
    entries_list=  utils.entry_list_maker(entries_list)
    return entries_list

def entries_time_line(conn):
    cursor = conn.cursor()
    if flask.session['admin']:
        cursor.execute("SELECT * FROM entries ORDER BY date DESC LIMIT 12")         
    else:
        cursor.execute("SELECT * FROM entries WHERE author == ? ORDER BY date DESC LIMIT 12", (flask.session['username'],))                              
    entries_list = cursor.fetchall()
    entries_list=  utils.entry_list_maker(entries_list)
    return entries_list
    