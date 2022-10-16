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
    if keyword != '' and keyword != ' ':
        try:
            cursor = conn.cursor()
            cursor.execute("select *  FROM experiments WHERE extra_txt LIKE ?", (f"%{keyword}%",))
            result = cursor.fetchall()
        except:
            result = None
    else:
        result = None
    return jsonify(result)

def filter_experiments(conn, post_request_form):
    Authors = post_request_form['Author']
    Hash_ID = post_request_form['Hash_ID']
    Text = post_request_form['Text']
    date_start = post_request_form['date_start']
    date_end = post_request_form['date_end']
    Tags = post_request_form['Tags']
    rows = []
    if Hash_ID != '':
        sql_command = 'SELECT * FROM experiments WHERE id_hash == ? AND ' 
        rows.append(Hash_ID)
    else:
        sql_command = 'SELECT * FROM experiments WHERE '
        if Authors != '':
            sql_command += 'author == ? AND '
            rows.append(Authors)
        if Text != '':
            sql_command += 'text like ? AND '
            rows.append(f'%{Text}%')
        if date_start != '':
            sql_command += 'date >= ? AND '
            rows.append(date_start)
        if date_end != '':
            sql_command += 'date <= ? AND '
            rows.append(date_end)
        if Tags != '':
            Tags = Tags.split(',')
            print(Tags)
            for tag in Tags:
                if tag != '':
                    sql_command += 'tags like ? AND '
                    rows.append(f'%{tag}%')
    sql_command = sql_command + '1'
    rows = tuple(rows)
    cursor = conn.cursor()
    cursor.execute(sql_command, rows)
    experiments_list = cursor.fetchall()
    experiments_list = list(experiments_list)
    for i, experiment in enumerate(experiments_list):
        experiment = list(experiment)
        experiment[1] = utils.parse_tags(experiment[1])
        experiments_list[i] = experiment
    return experiments_list