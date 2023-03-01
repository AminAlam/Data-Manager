# -*- coding: utf-8 -*-
import os
import io
import sys
import shutil
from functools import wraps
from flask import request, make_response

import json

def check_conditions_json(content, target_conditions=[]):
    try:
        conditions = json.loads(content)
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
        conditions = dict(sorted(conditions.items(), key=lambda item: item[0]))
        for condition in conditions.keys():
            conditions[condition] = dict(sorted(conditions[condition].items(), key=lambda item: item[0]))
        for condition in conditions.keys():
            for condition_nested in conditions[condition].keys():
                conditions[condition][condition_nested] = sorted(conditions[condition][condition_nested], key=lambda x: x[0])

        status = True
        message = ''
    except Exception as e:
        message = e
        status = False
    return status, message


PY2 = sys.version_info.major == 2
DEFAULT_CHUNK_SIZE = 16 * 1024


if PY2:
    string_types = basestring # pylint:disable=undefined-variable
else:
    string_types = str


def get_file_extension(filename):
    # return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    ext = os.path.splitext(filename)[1]
    if ext.startswith('.'):
        ext = ext[1:]
    return ext.lower()


def write_file(content, filepath, encoding='utf-8', chunk_size=None):
    success = True
    message = 'File saved successfully'
    _, file_nmae = os.path.split(filepath)
    if file_nmae == 'info.json':
        conditoins_status, err_message = check_conditions_json(content)
        if not conditoins_status:
            success = False
            message = f'Could not save file: Invalid input in info.json {err_message}'
            return success, message
    if isinstance(content, string_types):
        content_io = io.StringIO()
        content_io.write(content)
        with io.open(filepath, 'w', encoding=encoding, newline='\n') as dest:
            content_io.seek(0)
            try:
                shutil.copyfileobj(content_io, dest, chunk_size or DEFAULT_CHUNK_SIZE)
            except OSError as e:
                success = False
                message = 'Could not save file: ' + str(e)
    else:
        success = False
        message = 'Could not save file: Invalid content'
    return success, message


def dir_tree(abs_path, abs_root_path, exclude_names=None, excluded_extensions=None, allowed_extensions=None):
    tree = dict(
        name=os.path.basename(abs_path),
        path_name=abs_path[len(abs_root_path):].lstrip('/\\'),# TODO: use os.path.relpath
        children=[]
    )
    try:
        dir_entries = os.listdir(abs_path)
    except OSError:
        pass
    else:
        for name in dir_entries:
            if exclude_names and name in exclude_names:
                continue
            new_path = os.path.join(abs_path, name)
            if os.path.isdir(new_path):
                tree['children'].append(dir_tree(new_path, abs_root_path, exclude_names, excluded_extensions, allowed_extensions))
            else:
                ext = get_file_extension(name)
                if (excluded_extensions and ext in excluded_extensions) or (allowed_extensions and ext not in allowed_extensions):
                    continue
                tree['children'].append(dict(
                    name=os.path.basename(new_path),
                    path_name=new_path[len(abs_root_path):].lstrip('/\\'),# TODO: use os.path.relpath
                    is_file=True,
                ))
    return tree


def head_compatible(route_handler):
    """View decorator to make view handler compatible for `HEAD` method request."""
    @wraps(route_handler)
    def decorated_function(*args, **kwargs):
        if request.method == 'HEAD':
            route_response = route_handler(*args, **kwargs)
            response = make_response()
            response.headers.clear()
            response.headers.extend(route_response.headers)
            return response
        else:
            return route_handler(*args, **kwargs)
    return decorated_function
