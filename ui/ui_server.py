from bottle import route, run, request, response, template, TEMPLATE_PATH, debug, view, static_file, Bottle, \
    LocalRequest
import requests
import os
import json
from collections import OrderedDict


#os.chdir(os.path.dirname(__file__))
@route('/')
def index():
    get_env = requests.get(url='http://10.2.34.13:8080/v1.0/env')
    active_env = requests.get(url='http://10.2.34.13:8080/v1.0/config/active-env')
    print get_env.json()
    print active_env.json()
    return template('index.html', env=get_env.json(), active_env=active_env.json())

@route('/vim/')
def vim():
    get_vims = requests.get(url='http://10.2.34.13:8080/v1.0/vim')
    vim_list={}
    i=1
    for vim in get_vims.json().keys():
        vim_list[vim] = (get_vims.json()[vim]['type'], i)
        i = i+1
    return template('vim.html', vim_list=vim_list)

@route('/vim/data/', method='POST')
def vim_data():
    type = request.forms.get('type')
    if type == 'openstack':
        name = request.forms.get('name')
        user_domain_name = request.forms.get('user_domain_name')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project_domain_name = request.forms.get('project_domain_name')
        project_name = request.forms.get('project_name')
        auth_url = request.forms.get('auth_url')
        identity_api_version = request.forms.get('identity_api_version')
        new_vim={
                'client_config': {
                    'auth_url': auth_url,
                    'identity_api_version': identity_api_version,
                    'password': password,
                    'project_domain_name': project_domain_name,
                    'project_name': project_name,
                    'user_domain_name': user_domain_name,
                    'username': username
                },
                'type': type
        }
    requests.put(url='http://10.2.34.13:8080/v1.0/vim/%s' % name, json=new_vim)
    return vim()

@route('/vim/update/', method='POST')
def vim_update():
    if request.forms.get('confirmed') == "no":
        vim_name = request.forms.get('update_vim')
        vim_data = requests.get(url='http://10.2.34.13:8080/v1.0/vim/%s' % vim_name)
        vim_json = vim_data.json()
        vim_info = OrderedDict()
        # vim_info['name'] = vim_name
        vim_info['user_domain_name'] = vim_json[vim_name]['client_config']['user_domain_name']
        vim_info['username'] = vim_json[vim_name]['client_config']['username']
        vim_info['password'] = vim_json[vim_name]['client_config']['password']
        vim_info['project_domain_name'] = vim_json[vim_name]['client_config']['project_domain_name']
        vim_info['project_name'] = vim_json[vim_name]['client_config']['project_name']
        vim_info['auth_url'] = vim_json[vim_name]['client_config']['auth_url']
        vim_info['identity_api_version'] = vim_json[vim_name]['client_config']['identity_api_version']
        return template('vim_update.html', vim=vim_info, vim_name=vim_name)
    else:
        vim_name = request.forms.get('name')
        vim_data = requests.get(url='http://10.2.34.13:8080/v1.0/vim/%s' % vim_name)
        vim_json = vim_data.json()
        vim_type = vim_json[vim_name]['type']
        vim_to_add = {'client_config': {}, 'type': vim_type}
        vim_to_add['client_config'] = {
            'auth_url': request.forms.get('auth_url'),
            'identity_api_version': request.forms.get('identity_api_version'),
            'password': request.forms.get('password'),
            'project_domain_name': request.forms.get('project_domain_name'),
            'project_name': request.forms.get('project_name'),
            'user_domain_name': request.forms.get('user_domain_name'),
            'username': request.forms.get('username')
        }
        requests.put(url='http://10.2.34.13:8080/v1.0/vim/%s' % vim_name, json=vim_to_add)
        return vim()

@route('/vim/delete/', method='POST')
def vim_delete():
    if request.forms.get('confirmed') == "no":
        vim_name = request.forms.get('delete_vim')
        vim_data = requests.get(url='http://10.2.34.13:8080/v1.0/vim/%s' % vim_name)
        vim_json = vim_data.json()
        vim_info = OrderedDict()
        vim_info['name'] = vim_name
        vim_info['type'] = vim_json[vim_name]['type']
        vim_info['user_domain_name'] = vim_json[vim_name]['client_config']['user_domain_name']
        vim_info['username'] = vim_json[vim_name]['client_config']['username']
        vim_info['password'] = vim_json[vim_name]['client_config']['password']
        vim_info['project_domain_name'] = vim_json[vim_name]['client_config']['project_domain_name']
        vim_info['project_name'] = vim_json[vim_name]['client_config']['project_name']
        vim_info['auth_url'] = vim_json[vim_name]['client_config']['auth_url']
        vim_info['identity_api_version'] = vim_json[vim_name]['client_config']['identity_api_version']
        return template('vim_delete.html', vim=vim_info)
    else:
        vim_name = request.forms.get('name')
        requests.delete(url='http://10.2.34.13:8080/v1.0/vim/%s' % vim_name)
        return vim()

@route('/vim/add/<vim_type>/')
def vim_add(vim_type):
    return template('vim_add.html', vim_type=vim_type)

@route('/mano/')
def mano():
    get_manos = requests.get(url='http://10.2.34.13:8080/v1.0/mano')
    mano_list={}
    i=1
    for mano in get_manos.json().keys():
        mano_list[mano] = (get_manos.json()[mano]['type'], i)
        i = i+1
    return template('mano.html', mano_list=mano_list)


@route('/mano/add/<mano_type>/')
def mano_add(mano_type):
    return template('mano_add.html', mano_type=mano_type)


@route('/mano/data/', method='POST')
def mano_data():
    type = request.forms.get('type')
    if type == 'tacker':
        name = request.forms.get('name')
        user_domain_name = request.forms.get('user_domain_name')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project_domain_name = request.forms.get('project_domain_name')
        project_name = request.forms.get('project_name')
        auth_url = request.forms.get('auth_url')
        identity_api_version = request.forms.get('identity_api_version')
        new_mano={
                'client_config': {
                    'auth_url': auth_url,
                    'identity_api_version': identity_api_version,
                    'password': password,
                    'project_domain_name': project_domain_name,
                    'project_name': project_name,
                    'user_domain_name': user_domain_name,
                    'username': username
                },
                'type': type
        }
    requests.put(url='http://10.2.34.13:8080/v1.0/mano/%s' % name, json=new_mano)
    return mano()

@route('/mano/update/', method='POST')
def mano_update():
    if request.forms.get('confirmed') == "no":
        mano_name = request.forms.get('update_mano')
        mano_data = requests.get(url='http://10.2.34.13:8080/v1.0/mano/%s' % mano_name)
        mano_json = mano_data.json()
        mano_info = OrderedDict()
        mano_info['user_domain_name'] = mano_json[mano_name]['client_config']['user_domain_name']
        mano_info['username'] = mano_json[mano_name]['client_config']['username']
        mano_info['password'] = mano_json[mano_name]['client_config']['password']
        mano_info['project_domain_name'] = mano_json[mano_name]['client_config']['project_domain_name']
        mano_info['project_name'] = mano_json[mano_name]['client_config']['project_name']
        mano_info['auth_url'] = mano_json[mano_name]['client_config']['auth_url']
        mano_info['identity_api_version'] = mano_json[mano_name]['client_config']['identity_api_version']
        return template('mano_update.html', mano=mano_info, mano_name=mano_name)
    else:
        mano_name = request.forms.get('name')
        mano_data = requests.get(url='http://10.2.34.13:8080/v1.0/mano/%s' % mano_name)
        mano_json = mano_data.json()
        mano_type = mano_json[mano_name]['type']
        mano_to_add = {'client_config': {}, 'type': mano_type}
        mano_to_add['client_config'] = {
            'auth_url': request.forms.get('auth_url'),
            'identity_api_version': request.forms.get('identity_api_version'),
            'password': request.forms.get('password'),
            'project_domain_name': request.forms.get('project_domain_name'),
            'project_name': request.forms.get('project_name'),
            'user_domain_name': request.forms.get('user_domain_name'),
            'username': request.forms.get('username')
        }
        requests.put(url='http://10.2.34.13:8080/v1.0/mano/%s' % mano_name, json=mano_to_add)
        return mano()

@route('/mano/delete/', method='POST')
def mano_delete():
    if request.forms.get('confirmed') == "no":
        mano_name = request.forms.get('delete_mano')
        mano_data = requests.get(url='http://10.2.34.13:8080/v1.0/mano/%s' % mano_name)
        mano_json = mano_data.json()
        mano_info = OrderedDict()
        mano_info['name'] = mano_name
        mano_info['type'] = mano_json[mano_name]['type']
        mano_info['user_domain_name'] = mano_json[mano_name]['client_config']['user_domain_name']
        mano_info['username'] = mano_json[mano_name]['client_config']['username']
        mano_info['password'] = mano_json[mano_name]['client_config']['password']
        mano_info['project_domain_name'] = mano_json[mano_name]['client_config']['project_domain_name']
        mano_info['project_name'] = mano_json[mano_name]['client_config']['project_name']
        mano_info['auth_url'] = mano_json[mano_name]['client_config']['auth_url']
        mano_info['identity_api_version'] = mano_json[mano_name]['client_config']['identity_api_version']
        return template('mano_delete.html', mano=mano_info)
    else:
        mano_name = request.forms.get('name')
        requests.delete(url='http://10.2.34.13:8080/v1.0/mano/%s' % mano_name)
        return mano()


@route('/static/<filename:re:.*\.css>')
def all_css(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/css/")))

@route('/static/<filename:re:.*\.png>')
def all_png(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/img/")))

@route('/static/<filename:re:.*\.js>')
def all_js(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/js/")))


run(host='0.0.0.0', port=8081, debug=False)
