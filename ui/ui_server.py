#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import os
from collections import OrderedDict

import requests
from bottle import route, run, request, template, static_file, redirect

MANO_TYPES = ['tacker', 'cisco', 'sdl', 'rift', 'openbaton']
VIM_TYPES = ['openstack']
EM_TYPES = ['tacker']
TRAFFIC_TYPES = ['stc']
VNF_TYPES = ['ubuntu']


# os.chdir(os.path.dirname(__file__))
@route('/')
def index():
    """
    This function displays the available environments.
    """

    get_env_raw = requests.get(url='http://localhost:8080/v1.0/env')
    active_env_name_raw = requests.get(url='http://localhost:8080/v1.0/config/active-env')
    active_env_name = active_env_name_raw.json()
    get_env_json = get_env_raw.json()
    get_env_data = OrderedDict()
    for key in sorted(get_env_json.iterkeys()):
        get_env_data[key] = ()
        if 'mano' in get_env_json[key].keys():
            get_env_data[key] = get_env_data[key] + (get_env_json[key]['mano'],)
        else:
            get_env_data[key] = get_env_data[key] + ('N/A',)
        if 'vim' in get_env_json[key].keys():
            get_env_data[key] = get_env_data[key] + (get_env_json[key]['vim'],)
        else:
            get_env_data[key] = get_env_data[key] + ('N/A',)
        if 'em' in get_env_json[key].keys():
            get_env_data[key] = get_env_data[key] + (get_env_json[key]['em'],)
        else:
            get_env_data[key] = get_env_data[key] + ('N/A',)
        if 'traffic' in get_env_json[key].keys():
            get_env_data[key] = get_env_data[key] + (get_env_json[key]['traffic'],)
        else:
            get_env_data[key] = get_env_data[key] + ('N/A',)
        if 'vnf' in get_env_json[key].keys():
            get_env_data[key] = get_env_data[key] + (get_env_json[key]['vnf'],)
        else:
            get_env_data[key] = get_env_data[key] + ('N/A',)
        if key == active_env_name:
            get_env_data[key] = get_env_data[key] + ('Yes',)
        else:
            get_env_data[key] = get_env_data[key] + ('No',)
    return template('index.html', env_list=get_env_data)


@route('/env/add/')
def env_add(warning=None, message=None):
    """
    This function displays the required form to add a new Environment.
    """

    mano_list_raw = requests.get(url='http://localhost:8080/v1.0/mano')
    vim_list_raw = requests.get(url='http://localhost:8080/v1.0/vim')
    em_list_raw = requests.get(url='http://localhost:8080/v1.0/em')
    traffic_list_raw = requests.get(url='http://localhost:8080/v1.0/traffic')
    vnf_list_raw = requests.get(url='http://localhost:8080/v1.0/vnf')
    env_list = {}
    mano_list = mano_list_raw.json().keys()
    vim_list = vim_list_raw.json().keys()
    em_list = em_list_raw.json().keys()
    traffic_list = traffic_list_raw.json().keys()
    vnf_list = vnf_list_raw.json().keys()
    mano_list.append('')
    vim_list.append('')
    em_list.append('')
    traffic_list.append('')
    vnf_list.append('')
    mano_list.sort()
    vim_list.sort()
    em_list.sort()
    traffic_list.sort()
    vnf_list.sort()
    env_list['mano'] = mano_list
    env_list['vim'] = vim_list
    env_list['em'] = em_list
    env_list['traffic'] = traffic_list
    env_list['vnf'] = vnf_list
    return template('env_add.html', env_list=env_list, warning=warning, message=message)


@route('/env/delete/', method="POST")
def env_delete():
    """
    This function displays the required form to delete an existing Environment.
    """

    if request.forms.get('confirmed') == "no":
        env_name = request.forms.get('delete_env')
        env_data_raw = requests.get(url='http://localhost:8080/v1.0/env/%s' % env_name)
        env_data = env_data_raw.json()[env_name]
        return template('env_delete.html', env_data=env_data, env_name=env_name)
    else:
        env_name = request.forms.get('env_name')
        requests.delete(url='http://localhost:8080/v1.0/env/%s' % env_name)
        return index()


@route('/env/update/', method="POST")
def env_update():
    """
    This function displays the required form to update an existing Environment.
    """

    if request.forms.get('confirmed') == "no":
        env_name = request.forms.get('update_env')
        env_data_raw = requests.get(url='http://localhost:8080/v1.0/env/%s' % env_name)
        env_data = env_data_raw.json()[env_name]
        mano_list_raw = requests.get(url='http://localhost:8080/v1.0/mano')
        vim_list_raw = requests.get(url='http://localhost:8080/v1.0/vim')
        em_list_raw = requests.get(url='http://localhost:8080/v1.0/em')
        traffic_list_raw = requests.get(url='http://localhost:8080/v1.0/traffic')
        vnf_list_raw = requests.get(url='http://localhost:8080/v1.0/vnf')
        env_list = {}
        env_list['mano'] = mano_list_raw.json().keys()
        env_list['vim'] = vim_list_raw.json().keys()
        env_list['em'] = em_list_raw.json().keys()
        env_list['traffic'] = traffic_list_raw.json().keys()
        env_list['vnf'] = vnf_list_raw.json().keys()
        for element in ['mano', 'vim', 'em', 'traffic', 'vnf']:
            env_list[element].insert(0, '')
            if element in env_data.keys():
                if env_data[element] in env_list[element]:
                    env_list[element].remove(env_data[element])
                    env_list[element].insert(0, env_data[element])
                else:
                    continue
        return template('env_update.html', env_name=env_name, env_list=env_list)
    else:
        env_name = request.forms.get('env_name')
        new_env = {}
        for element in ['mano', 'vim', 'em', 'traffic', 'vnf']:
            if request.forms.get(element) != '':
                new_env[element] = request.forms.get(element)
        requests.put(url='http://localhost:8080/v1.0/env/%s' % env_name, json=new_env)
        return index()


@route('/env/data/', method="POST")
def env_data():
    """
    This function is used by the env_add function to send the new data to the REST server with 'PUT'
    command.
    """

    env_name = request.forms.get('env_name')
    if not env_name:
        return env_add(warning="Missing mandatory field: name", message=None)
    new_env = {}
    for element in ['mano', 'vim', 'em', 'traffic', 'vnf']:
        if request.forms.get(element) != '':
            new_env[element] = request.forms.get(element)
    requests.put(url='http://localhost:8080/v1.0/env/%s' % env_name, json=new_env)
    return index()


@route('/config/active-env/<active_env>')
def set_active_env(active_env):
    requests.put(url='http://localhost:8080/v1.0/config/active-env', json=active_env)
    return index()


@route('/mano/')
def mano():
    """
    This function displays the available MANO platforms configured.
    """
    get_manos = requests.get(url='http://localhost:8080/v1.0/mano')
    mano_list = []
    for mano in sorted(get_manos.json().iterkeys()):
        if 'type' in get_manos.json()[mano].keys() and get_manos.json()[mano]['type'] in MANO_TYPES:
            mano_list.append((mano, get_manos.json()[mano]['type']))
        else:
            continue
    return template('mano.html', mano_list=mano_list)


@route('/mano/add/<mano_type>/')
def mano_add(mano_type, warning=None, message=None, mano=None, name=None, additional_params=None):
    """
    This function displays the required form to add a new MANO platform.
    :param mano_type: Type of MANO platform to be added
    :param warning: Warning information from the REST server at the validation operation.
    :param message: Success message from the REST server at the validation operation.
    :param mano: MANO element data structure
    :param name: Name of MANO element
    """

    if additional_params == None:
        additional_params = {}
        additional_params['vim_list'] = prepare_option_list(option_type="vim")
    return template('mano_add.html', mano_type=mano_type, warning=warning, message=message, mano=mano, name=name,
                    additional_params=additional_params)


@route('/mano/validate/', method='POST')
def mano_validate():
    """
    This function is used by the mano_add and mano_update functions to send the new data to the REST server with 'PUT'
    command and to validate the MANO configuration.
    """

    type = request.forms.get('type')
    if type == 'tacker':
        name = request.forms.get('name')
        user_domain_name = request.forms.get('user_domain_name')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project_domain_name = request.forms.get('project_domain_name')
        project_name = request.forms.get('project_name')
        auth_url = request.forms.get('auth_url')
        vnfd_id = request.forms.get('vnfd_id')
        nsd_id = request.forms.get('nsd_id')
        if not request.forms.get('identity_api_version'):
            identity_api_version = 0
        else:
            identity_api_version = int(request.forms.get('identity_api_version'))
        (name, new_mano) = struct_mano(type=type, name=name, user_domain_name=user_domain_name, username=username,
                                       password=password, project_domain_name=project_domain_name,
                                       project_name=project_name, auth_url=auth_url,
                                       identity_api_version=identity_api_version, vnfd_id=vnfd_id, nsd_id=nsd_id)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_add(mano_type=type, warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_update(warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('add'):
            if not name:
                return mano_add(mano_type=type, warning='Mandatory field missing: name', message=None,
                                mano=new_mano, name=name)
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
    if type == 'cisco':
        name = request.forms.get('name')
        nso_hostname = request.forms.get('nso_hostname')
        nso_username = request.forms.get('nso_username')
        nso_password = request.forms.get('nso_password')
        nso_port = request.forms.get('nso_port')
        esc_hostname = request.forms.get('esc_hostname')
        esc_username = request.forms.get('esc_username')
        esc_password = request.forms.get('esc_password')
        esc_port = request.forms.get('esc_port')
        vnfd_id = request.forms.get('vnfd_id')
        flavour_id = request.forms.get('flavour_id')
        nsd_id = request.forms.get('nsd_id')
        instantiation_level__id = request.forms.get('instantiation_level_id')
        (name, new_mano) = struct_mano(type=type, name=name, nso_hostname=nso_hostname, nso_username=nso_username,
                                       nso_password=nso_password, nso_port=nso_port, esc_hostname=esc_hostname,
                                       esc_username=esc_username, esc_password=esc_password, esc_port=esc_port,
                                       vnfd_id=vnfd_id, flavour_id=flavour_id,
                                       instantiation_level_id=instantiation_level__id, nsd_id=nsd_id)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_add(mano_type=type, warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_update(warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('add'):
            if not name:
                return mano_add(mano_type=type, warning='Mandatory field missing: name', message=None,
                                mano=new_mano, name=name)
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
    if type == 'sdl':
        name = request.forms.get('name')
        nfv_api_url = request.forms.get('nfv_api_url')
        ui_api_url = request.forms.get('ui_api_url')
        tenant_id = request.forms.get('tenant_id')
        username = request.forms.get('username')
        password = request.forms.get('password')
        nsd_id = request.forms.get('nsd_id')
        (name, new_mano) = struct_mano(type=type, name=name, nfv_api_url=nfv_api_url, ui_api_url=ui_api_url,
                                       tenant_id=tenant_id, username=username, password=password, nsd_id=nsd_id)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_add(mano_type=type, warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_update(warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('add'):
            if not name:
                return mano_add(mano_type=type, warning='Mandatory field missing: name', message=None,
                                mano=new_mano, name=name)
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
    if type == 'rift':
        name = request.forms.get('name')
        url = request.forms.get('url')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project = request.forms.get('project')
        nsd_id = request.forms.get('nsd_id')
        datacenter = request.forms.get('datacenter')
        scaling_group_name = request.forms.get('scaling_group_name')
        (name, new_mano) = struct_mano(type=type, name=name, url=url, username=username, password=password,
                                       project=project, nsd_id=nsd_id, datacenter=datacenter,
                                       scaling_group_name=scaling_group_name)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_add(mano_type=type, warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            return mano_update(warning=warning, message=message, mano=new_mano, name=name)
        elif request.forms.get('add'):
            if not name:
                return mano_add(mano_type=type, warning='Mandatory field missing: name', message=None,
                                mano=new_mano, name=name)
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
    if type == 'openbaton':
        name = request.forms.get('name')
        url = request.forms.get('url')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project = request.forms.get('project')
        nsd_id = request.forms.get('nsd_id')
        vim_name = request.forms.get('vim_info')
        if vim_name:
            vim_info = requests.get(url='http://localhost:8080/v1.0/vim/%s' % vim_name).json()
        else:
            vim_info = None
        (name, new_mano) = struct_mano(type=type, name=name, url=url, username=username, password=password,
                                       project=project, nsd_id=nsd_id, vim_info=vim_info)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            additional_params = {}
            additional_params['vim_list'] = prepare_option_list(option_type="vim", selected=vim_name)
            return mano_add(mano_type=type, warning=warning, message=message, mano=new_mano, name=name,
                            additional_params=additional_params)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('mano', new_mano)
            warning = validation['warning']
            message = validation['message']
            additional_params = {}
            additional_params['vim_list'] = prepare_option_list(option_type="vim", selected=vim_name)
            return mano_update(warning=warning, message=message, mano=new_mano, name=name,
                               additional_params=additional_params)
        elif request.forms.get('add'):
            if not name:
                return mano_add(mano_type=type, warning='Mandatory field missing: name', message=None,
                                mano=new_mano, name=name)
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)

    return mano()


@route('/mano/update/', method='POST')
def mano_update(warning=None, message=None, mano=None, name=None, additional_params=None):
    """
    This function displays the required form to update an existing MANO platform.
    :param warning: Warning information from the REST server at the validation operation.
    :param message: Success message from the REST server at the validation operation.
    :param mano: MANO structure containing data to reach the MANO element.
    :param name: name of MANO element.
    """

    if mano is None:
        name = request.forms.get('update_mano')
        mano_data = requests.get(url='http://localhost:8080/v1.0/mano/%s' % name)
        mano_json = mano_data.json()[name]
        if additional_params == None:
            additional_params = {}
            if mano_json['client_config'].get('vim_info', {}):
                selected_vim = mano_json['client_config']['vim_info'].keys()[0]
            else:
                selected_vim = None
            additional_params['vim_list'] = prepare_option_list(option_type="vim", selected=selected_vim)
        return template('mano_update.html', warning=warning, message=message, mano=mano_json, name=name,
                        additional_params=additional_params)
    else:
        return template('mano_update.html', warning=warning, message=message, mano=mano, name=name,
                        additional_params=additional_params)


@route('/mano/delete/', method='POST')
def mano_delete():
    """
    This function displays the required form to delete an existing MANO platform.
    """

    if request.forms.get('confirmed') == "no":
        mano_name = request.forms.get('delete_mano')
        mano_data = requests.get(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
        mano_json = mano_data.json()
        mano_info = OrderedDict()
        mano_info['name'] = mano_name
        mano_info['type'] = mano_json[mano_name]['type']
        if mano_json[mano_name]['type'] == 'tacker':
            mano_info['user_domain_name'] = mano_json[mano_name]['client_config']['user_domain_name']
            mano_info['username'] = mano_json[mano_name]['client_config']['username']
            mano_info['password'] = mano_json[mano_name]['client_config']['password']
            mano_info['project_domain_name'] = mano_json[mano_name]['client_config']['project_domain_name']
            mano_info['project_name'] = mano_json[mano_name]['client_config']['project_name']
            mano_info['auth_url'] = mano_json[mano_name]['client_config']['auth_url']
            mano_info['identity_api_version'] = mano_json[mano_name]['client_config']['identity_api_version']
            mano_info['vnfd_id'] = mano_json[mano_name]['vnfd_id']
            mano_info['nsd_id'] = mano_json[mano_name]['nsd_id']
        elif mano_json[mano_name]['type'] == 'cisco':
            mano_info['nso_hostname'] = mano_json[mano_name]['client_config']['nso_hostname']
            mano_info['nso_username'] = mano_json[mano_name]['client_config']['nso_username']
            mano_info['nso_password'] = mano_json[mano_name]['client_config']['nso_password']
            mano_info['nso_port'] = mano_json[mano_name]['client_config']['nso_port']
            mano_info['esc_hostname'] = mano_json[mano_name]['client_config']['esc_hostname']
            mano_info['esc_username'] = mano_json[mano_name]['client_config']['esc_username']
            mano_info['esc_password'] = mano_json[mano_name]['client_config']['esc_password']
            mano_info['esc_port'] = mano_json[mano_name]['client_config']['esc_port']
            mano_info['vnfd_id'] = mano_json[mano_name]['vnfd_id']
            mano_info['nsd_id'] = mano_json[mano_name]['nsd_id']
            mano_info['flavour_id'] = mano_json[mano_name]['flavour_id']
            mano_info['instantiation_level_id'] = mano_json[mano_name]['instantiation_level_id']
        elif mano_json[mano_name]['type'] == 'sdl':
            mano_info['nfv_api_url'] = mano_json[mano_name]['client_config']['nfv_api_url']
            mano_info['ui_api_url'] = mano_json[mano_name]['client_config']['ui_api_url']
            mano_info['tenant_id'] = mano_json[mano_name]['client_config']['tenant_id']
            mano_info['username'] = mano_json[mano_name]['client_config']['username']
            mano_info['password'] = mano_json[mano_name]['client_config']['password']
            mano_info['nsd_id'] = mano_json[mano_name]['nsd_id']
        elif mano_json[mano_name]['type'] == 'rift':
            mano_info['url'] = mano_json[mano_name]['client_config']['url']
            mano_info['username'] = mano_json[mano_name]['client_config']['username']
            mano_info['password'] = mano_json[mano_name]['client_config']['password']
            mano_info['project'] = mano_json[mano_name]['client_config']['project']
            mano_info['datacenter'] = mano_json[mano_name]['instantiation_params_for_ns']['datacenter']
            mano_info['scaling_group_name'] = mano_json[mano_name]['scale_params']['scaling_group_name']
            mano_info['nsd_id'] = mano_json[mano_name]['nsd_id']
        elif mano_json[mano_name]['type'] == 'openbaton':
            mano_info['url'] = mano_json[mano_name]['client_config']['url']
            mano_info['username'] = mano_json[mano_name]['client_config']['username']
            mano_info['password'] = mano_json[mano_name]['client_config']['password']
            mano_info['project'] = mano_json[mano_name]['client_config']['project']
            mano_info['nsd_id'] = mano_json[mano_name]['nsd_id']
            mano_info['vim_info'] = mano_json[mano_name]['client_config']['vim_info'].keys()[0]
        return template('mano_delete.html', mano=mano_info)
    else:
        mano_name = request.forms.get('name')
        requests.delete(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
        return mano()


@route('/vim/')
def vim(warning=None):
    """
    This function displays the available VIM platforms configured.
    """
    get_vims = requests.get(url='http://localhost:8080/v1.0/vim')
    vim_list = []
    i = 1
    for vim in sorted(get_vims.json().iterkeys()):
        if 'type' in get_vims.json()[vim].keys() and get_vims.json()[vim]['type'] in VIM_TYPES:
            vim_list.append((vim, get_vims.json()[vim]['type']))
        else:
            continue
        i = i + 1
    return template('vim.html', vim_list=vim_list, warning=warning)


@route('/vim/update/', method='POST')
def vim_update(warning=None, message=None, vim=None, name=None):
    """
    This function displays the required form to update an existing VIM platform.
    """

    if vim is None:
        name = request.forms.get('update_vim')
        vim_data = requests.get(url='http://localhost:8080/v1.0/vim/%s' % name)
        vim_json = vim_data.json()[name]
        return template('vim_update.html', warning=warning, message=message, vim=vim_json, name=name)
    else:
        return template('vim_update.html', warning=warning, message=message, vim=vim, name=name)


@route('/vim/delete/', method='POST')
def vim_delete():
    """
    This function displays the required form to delete an existing VIM platform.
    """

    if request.forms.get('confirmed') == "no":
        vim_name = request.forms.get('delete_vim')
        vim_data = requests.get(url='http://localhost:8080/v1.0/vim/%s' % vim_name)
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
        requests.delete(url='http://localhost:8080/v1.0/vim/%s' % vim_name)
        return vim()


@route('/vim/add/<vim_type>/')
def vim_add(vim_type, warning=None, message=None, vim=None, name=None):
    """
    This function displays the required form to add a new VIM platform.
    :param vim_type: Type of VIM platform to be added
    :param warning: Warning information from the REST server at the validation operation.
    :param message: Success message from the REST server at the validation operation.
    :param vim: VIM structure containing data to reach the VIM element.
    :param name: name of VIM element.
    """

    return template('vim_add.html', vim_type=vim_type, warning=warning, message=message, vim=vim, name=name)


@route('/vim/validate/', method='POST')
def vim_validate():
    """
    This function is used by the vim_add and vim_update functions to send the new data to the REST server with 'PUT'
    command and to validate the VIM configuration.
    """

    type = request.forms.get('type')
    if type == 'openstack':
        name = request.forms.get('name')
        user_domain_name = request.forms.get('user_domain_name')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project_domain_name = request.forms.get('project_domain_name')
        project_name = request.forms.get('project_name')
        auth_url = request.forms.get('auth_url')
        if not request.forms.get('identity_api_version'):
            identity_api_version = 0
        else:
            identity_api_version = int(request.forms.get('identity_api_version'))
        (name, new_vim) = struct_vim(type=type, name=name, user_domain_name=user_domain_name, username=username,
                                     password=password, project_domain_name=project_domain_name,
                                     project_name=project_name, auth_url=auth_url,
                                     identity_api_version=identity_api_version)
        if request.forms.get('validate') and request.forms.get('action') == 'Add':
            validation = validate('vim', new_vim)
            warning = validation['warning']
            message = validation['message']
            return vim_add(vim_type=type, warning=warning, message=message, vim=new_vim, name=name)
        elif request.forms.get('validate') and request.forms.get('action') == 'Update':
            validation = validate('vim', new_vim)
            warning = validation['warning']
            message = validation['message']
            return vim_update(warning=warning, message=message, vim=new_vim, name=name)
        elif request.forms.get('add'):
            if not name:
                return vim_add(vim_type=type, warning='Mandatory field missing: name', message=None,
                               vim=new_vim, name=name)
            requests.put(url='http://localhost:8080/v1.0/vim/%s' % name, json=new_vim)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/vim/%s' % name, json=new_vim)
    return vim()


@route('/em/')
def em():
    """
    This function displays the available Element Manager platforms configured.
    """

    get_ems = requests.get(url='http://localhost:8080/v1.0/em')
    em_list = []
    i = 1
    for em in sorted(get_ems.json().iterkeys()):
        if 'type' in get_ems.json()[em].keys() and get_ems.json()[em]['type'] in EM_TYPES:
            em_list.append((em, get_ems.json()[em]['type']))
        else:
            continue
        i = i + 1
    return template('em.html', em_list=em_list)


@route('/em/add/<em_type>/')
def em_add(em_type, warning=None, message=None, em=None, name=None):
    """
    This function displays the required form to add a new Element Manager platform.
    :param em_type: Type of Element Manager platform to be added
    """

    return template('em_add.html', em_type=em_type, warning=warning, message=message, em=em, name=name)


@route('/em/validate/', method='POST')
def em_validate():
    """
    This function is used by the vim_add and em_update functions to send the new data to the REST server with 'PUT'
    command and to validate the EM configuration.
    """

    type = request.forms.get('type')
    if type == 'tacker':
        name = request.forms.get('name')
        user_domain_name = request.forms.get('user_domain_name')
        username = request.forms.get('username')
        password = request.forms.get('password')
        project_domain_name = request.forms.get('project_domain_name')
        project_name = request.forms.get('project_name')
        auth_url = request.forms.get('auth_url')
        if not request.forms.get('identity_api_version'):
            identity_api_version = 0
        else:
            identity_api_version = int(request.forms.get('identity_api_version'))
        (name, new_em) = struct_em(type=type, name=name, user_domain_name=user_domain_name, username=username,
                                   password=password, project_domain_name=project_domain_name,
                                   project_name=project_name, auth_url=auth_url,
                                   identity_api_version=identity_api_version)
        if request.forms.get('add'):
            if not name:
                return em_add(em_type=type, warning='Mandatory field missing: name', message=None,
                              em=new_em, name=name)
            requests.put(url='http://localhost:8080/v1.0/em/%s' % name, json=new_em)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/em/%s' % name, json=new_em)
    return em()


@route('/em/update/', method='POST')
def em_update(warning=None, message=None, em=None, name=None):
    """
    This function displays the required form to update an existing Element Manager platform.
    """

    if em is None:
        name = request.forms.get('update_em')
        em_data = requests.get(url='http://localhost:8080/v1.0/em/%s' % name)
        em_json = em_data.json()[name]
        return template('em_update.html', warning=warning, message=message, em=em_json, name=name)
    else:
        return template('em_update.html', warning=warning, message=message, em=em, name=name)


@route('/em/delete/', method='POST')
def em_delete():
    """
    This function displays the required form to delete an existing Element Manager platform.
    """

    if request.forms.get('confirmed') == "no":
        em_name = request.forms.get('delete_em')
        em_data = requests.get(url='http://localhost:8080/v1.0/em/%s' % em_name)
        em_json = em_data.json()
        em_info = OrderedDict()
        em_info['name'] = em_name
        em_info['type'] = em_json[em_name]['type']
        em_info['user_domain_name'] = em_json[em_name]['client_config']['user_domain_name']
        em_info['username'] = em_json[em_name]['client_config']['username']
        em_info['password'] = em_json[em_name]['client_config']['password']
        em_info['project_domain_name'] = em_json[em_name]['client_config']['project_domain_name']
        em_info['project_name'] = em_json[em_name]['client_config']['project_name']
        em_info['auth_url'] = em_json[em_name]['client_config']['auth_url']
        em_info['identity_api_version'] = em_json[em_name]['client_config']['identity_api_version']
        return template('em_delete.html', em=em_info)
    else:
        em_name = request.forms.get('name')
        requests.delete(url='http://localhost:8080/v1.0/em/%s' % em_name)
        return em()


@route('/traffic/')
def traffic():
    """
    This function displays the available Traffic generation platforms configured.
    """

    get_traffics = requests.get(url='http://localhost:8080/v1.0/traffic')
    traffic_list = []
    i = 1
    for traffic in sorted(get_traffics.json().iterkeys()):
        if 'type' in get_traffics.json()[traffic].keys() and get_traffics.json()[traffic]['type'] in TRAFFIC_TYPES:
            traffic_list.append((traffic, get_traffics.json()[traffic]['type']))
        else:
            continue
        i = i + 1
    return template('traffic.html', traffic_list=traffic_list)


@route('/traffic/add/<traffic_type>/')
def traffic_add(traffic_type, warning=None, message=None, traffic=None, name=None):
    """
    This function displays the required form to add a new Traffic generation element.
    :param traffic_type: Type of Traffic generation element to be added

    """
    return template('traffic_add', traffic_type=traffic_type, warning=warning, message=message, traffic=traffic,
                    name=name)


@route('/traffic/validate/', method='POST')
def traffic_validate():
    """
    This function is used by the traffic_add and traffic_update functions to send the new data to the REST server with
    'PUT' command and to validate the MANO configuration.
    """

    type = request.forms.get('type')

    # The first case is when the VNF has type VNF_TRANSIENT
    if type == 'VNF_TRANSIENT':
        name = request.forms.get('name')
        lab_server_addr = request.forms.get('lab_server_addr')
        left_port_location = request.forms.get('left_port_location')
        left_traffic_addr = request.forms.get('left_traffic_addr')
        left_traffic_plen = request.forms.get('left_traffic_plen')
        left_traffic_gw = request.forms.get('left_traffic_gw')
        left_traffic_gw_mac = request.forms.get('left_traffic_gw_mac')
        ingress_cp_name = get_list_by_string(request.forms.get('ingress_cp_name'))
        right_port_location = request.forms.get('right_port_location')
        right_traffic_addr = request.forms.get('right_traffic_addr')
        right_traffic_plen = request.forms.get('right_traffic_plen')
        right_traffic_gw = request.forms.get('right_traffic_gw')
        new_traffic = {
            'client_config': {
                'lab_server_addr': lab_server_addr
            },
            'traffic_config': {
                'type': 'VNF_TRANSIENT',
                'left_port_location': left_port_location,
                'left_traffic_addr': left_traffic_addr,
                'left_traffic_plen': left_traffic_plen,
                'left_traffic_gw': left_traffic_gw,
                'left_traffic_gw_mac': left_traffic_gw_mac,
                'ingress_cp_name': ingress_cp_name,
                'right_port_location': right_port_location,
                'right_traffic_addr': right_traffic_addr,
                'right_traffic_plen': right_traffic_plen,
                'right_traffic_gw': right_traffic_gw
            },
            'type': 'stc'
        }
        if request.forms.get('add'):
            if not name:
                return traffic_add(traffic_type=type, warning='Mandatory field missing: name', message=None,
                                   traffic=new_traffic, name=name)
            requests.put(url='http://localhost:8080/v1.0/traffic/%s' % name, json=new_traffic)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/traffic/%s' % name, json=new_traffic)

            # The second case is when the VNF has type VNF_TERMINATED
    if type == 'VNF_TERMINATED':
        name = request.forms.get('name')
        lab_server_addr = request.forms.get('lab_server_addr')
        payload = request.forms.get('payload')
        port_location = request.forms.get('port_location')
        traffic_src_addr = request.forms.get('traffic_src_addr')
        traffic_dst_addr = request.forms.get('traffic_dst_addr')
        ingress_cp_name = get_list_by_string(request.forms.get('ingress_cp_name'))
        new_traffic = {
            'client_config': {
                'lab_server_addr': lab_server_addr
            },
            'traffic_config': {
                'type': 'VNF_TERMINATED',
                'payload': payload,
                'port_location': port_location,
                'traffic_src_addr': traffic_src_addr,
                'traffic_dst_addr': traffic_dst_addr,
                'ingress_cp_name': ingress_cp_name
            },
            'type': 'stc'
        }
        if request.forms.get('add'):
            if not name:
                return traffic_add(traffic_type=type, warning='Mandatory field missing: name', message=None,
                                   traffic=new_traffic, name=name)
            requests.put(url='http://localhost:8080/v1.0/traffic/%s' % name, json=new_traffic)
        elif request.forms.get('update'):
            requests.put(url='http://localhost:8080/v1.0/traffic/%s' % name, json=new_traffic)

    return traffic()


@route('/traffic/update/', method='POST')
def traffic_update(warning=None, message=None, traffic=None, name=None):
    """
    This function displays the required form to update an existing Traffic generation element.
    """

    if traffic is None:
        name = request.forms.get('update_traffic')
        traffic_data = requests.get(url='http://localhost:8080/v1.0/traffic/%s' % name)
        traffic_json = traffic_data.json()[name]
        traffic_json['traffic_config']['ingress_cp_name'] = get_string_by_list(
            traffic_json['traffic_config']['ingress_cp_name'])
        return template('traffic_update.html', warning=warning, message=message, traffic=traffic_json, name=name)
    else:
        return template('traffic_update.html', warning=warning, message=message, traffic=traffic, name=name)


@route('/traffic/delete/', method='POST')
def traffic_delete():
    """
    This function displays the required form to delete an existing Traffic generation element.
    """

    if request.forms.get('confirmed') == "no":
        traffic_name = request.forms.get('delete_traffic')
        traffic_data = requests.get(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        traffic_json = traffic_data.json()
        traffic_info = OrderedDict()
        traffic_info['name'] = traffic_name
        traffic_info['type'] = traffic_json[traffic_name]['traffic_config']['type']
        if traffic_info['type'] == 'VNF_TRANSIENT':
            traffic_info['lab_server_addr'] = traffic_json[traffic_name]['client_config']['lab_server_addr']
            traffic_info['left_port_location'] = traffic_json[traffic_name]['traffic_config']['left_port_location']
            traffic_info['left_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['left_traffic_addr']
            traffic_info['left_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['left_traffic_plen']
            traffic_info['left_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw']
            traffic_info['left_traffic_gw_mac'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw_mac']
            traffic_info['ingress_cp_name'] = get_string_by_list(traffic_json[traffic_name]['traffic_config'][
                                                                     'ingress_cp_name'])
            traffic_info['right_port_location'] = traffic_json[traffic_name]['traffic_config']['right_port_location']
            traffic_info['right_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['right_traffic_addr']
            traffic_info['right_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['right_traffic_plen']
            traffic_info['right_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['right_traffic_gw']
        elif traffic_info['type'] == 'VNF_TERMINATED':
            traffic_info['lab_server_addr'] = traffic_json[traffic_name]['client_config']['lab_server_addr']
            traffic_info['payload'] = traffic_json[traffic_name]['traffic_config']['payload']
            traffic_info['port_location'] = traffic_json[traffic_name]['traffic_config']['port_location']
            traffic_info['traffic_src_addr'] = traffic_json[traffic_name]['traffic_config']['traffic_src_addr']
            traffic_info['traffic_dst_addr'] = traffic_json[traffic_name]['traffic_config']['traffic_dst_addr']
            traffic_info['ingress_cp_name'] = get_string_by_list(traffic_json[traffic_name]['traffic_config'][
                                                                     'ingress_cp_name'])
        return template('traffic_delete.html', traffic=traffic_info)
    else:
        traffic_name = request.forms.get('name')
        requests.delete(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        return traffic()


@route('/vnf/')
def vnf(warning=None):
    """
    This function displays the available Virtual Network Functions configured.
    """

    get_vnfs = requests.get(url='http://localhost:8080/v1.0/vnf')
    vnf_list = []
    for vnf in sorted(get_vnfs.json().iterkeys()):
        if 'type' in get_vnfs.json()[vnf].keys():
            vnf_type = get_vnfs.json()[vnf]['type']
            vnf_list.append((vnf, vnf_type))
        else:
            continue
    return template('vnf.html', vnf_list=vnf_list, warning=warning)


@route('/vnf/add/', method="POST")
def vnf_add(warning=None, message=None, vnf=None, instance_name=None):
    """
    This function displays the required form to add a new Virtual Network Function element.
    """

    return template('vnf_add.html', warning=warning, message=message, vnf=vnf, instance_name=None)


@route('/vnf/data/', method='POST')
def vnf_data():
    """
    This function is used by the vnf_add function to send the new data to the REST server with 'PUT'
    command.
    """

    type = request.forms.get('type')
    instance_name = request.forms.get('instance_name')
    mgmt_ip_addr = request.forms.get('mgmt_ip_addr')
    username = request.forms.get('username')
    password = request.forms.get('password')
    config = request.forms.get('config')
    new_vnf = {
        'client_config': {
            'mgmt_ip_addr': mgmt_ip_addr,
            'password': password,
            'username': username
        },
        'type': type,
        'instance_name': instance_name,
        'config': config
    }
    if not instance_name:
        return vnf_add(warning='Mandatory field missing: Instance Name', message=None, vnf=new_vnf,
                       instance_name=instance_name)
    elif not type:
        return vnf_add(warning='Mandatory field missing: Type', message=None, vnf=new_vnf,
                       instance_name=instance_name)
    response = requests.put(url='http://localhost:8080/v1.0/vnf/%s' % instance_name, json=new_vnf)
    if response.status_code == 504:
        return vnf(warning=response.json().get('warning'))
    return vnf()


@route('/vnf/update/', method='POST')
def vnf_update():
    """
    This function displays the required form to update an existing VNF element.
    """

    if request.forms.get('confirmed') == "no":
        vnf_name = request.forms.get('update_vnf')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_info = OrderedDict()
        vnf_info['type'] = vnf_json[vnf_name]['type']
        vnf_info['instance_name'] = vnf_json[vnf_name]['instance_name']
        vnf_info['mgmt_ip_addr'] = vnf_json[vnf_name]['client_config']['mgmt_ip_addr']
        vnf_info['username'] = vnf_json[vnf_name]['client_config']['username']
        vnf_info['password'] = vnf_json[vnf_name]['client_config']['password']
        vnf_info['config'] = vnf_json[vnf_name]['config']
        return template('vnf_update.html', vnf=vnf_info, vnf_name=vnf_name)
    else:
        vnf_name = request.forms.get('instance_name')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_type = vnf_json[vnf_name]['type']
        vnf_to_add = {'client_config': {},
                      'type': vnf_type,
                      'instance_name': request.forms.get('instance_name'),
                      'config': request.forms.get('config')}
        vnf_to_add['client_config'] = {
            'mgmt_ip_addr': request.forms.get('mgmt_ip_addr'),
            'username': request.forms.get('username'),
            'password': request.forms.get('password'),
        }
        requests.put(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name, json=vnf_to_add)
        return vnf()


@route('/vnf/delete/', method='POST')
def vnf_delete():
    """
    This function displays the required form to delete an existing Virtual Network Function element.
    """

    if request.forms.get('confirmed') == "no":
        vnf_name = request.forms.get('delete_vnf')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_info = OrderedDict()
        vnf_info['type'] = vnf_json[vnf_name]['type']
        vnf_info['instance_name'] = vnf_name
        vnf_info['config'] = vnf_json[vnf_name]['config']
        vnf_info['mgmt_ip_addr'] = vnf_json[vnf_name]['client_config']['mgmt_ip_addr']
        vnf_info['username'] = vnf_json[vnf_name]['client_config']['username']
        vnf_info['password'] = vnf_json[vnf_name]['client_config']['password']
        return template('vnf_delete.html', vnf=vnf_info)
    else:
        vnf_name = request.forms.get('instance_name')
        requests.delete(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        return vnf()


@route('/additional/')
def additional():
    """
    This function displays the additional parameters that a customer must setup.
    """
    set_default_additional()
    scaling_policy_name = requests.get(url='http://localhost:8080/v1.0/config/scaling_policy_name')
    desired_scale_out_steps = requests.get(url='http://localhost:8080/v1.0/config/desired_scale_out_steps')
    operate_vnf_data = get_str_by_unicode(
        requests.get(url='http://localhost:8080/v1.0/config/operate_vnf_data').json())
    vnf_instantiate_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_INSTANTIATE_TIMEOUT')
    vnf_scale_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_SCALE_TIMEOUT')
    vnf_stop_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_STOP_TIMEOUT')
    vnf_start_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_START_TIMEOUT')
    vnf_terminate_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_TERMINATE_TIMEOUT')
    vnf_stable_state_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_STABLE_STATE_TIMEOUT')
    ns_instantiate_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_INSTANTIATE_TIMEOUT')
    ns_scale_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_SCALE_TIMEOUT')
    ns_terminate_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_TERMINATE_TIMEOUT')
    poll_interval = requests.get(url='http://localhost:8080/v1.0/config/POLL_INTERVAL')
    low_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/LOW_TRAFFIC_LOAD')
    normal_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/NORMAL_TRAFFIC_LOAD')
    max_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/MAX_TRAFFIC_LOAD')
    traffic_tolerance = requests.get(url='http://localhost:8080/v1.0/config/TRAFFIC_TOLERANCE')
    additional_params = {
        'scaling_policy_name': scaling_policy_name.json(),
        'desired_scale_out_steps': desired_scale_out_steps.json(),
        'operate_vnf_data': operate_vnf_data,
        'VNF_INSTANTIATE_TIMEOUT': vnf_instantiate_timeout.json(),
        'VNF_SCALE_TIMEOUT': vnf_scale_timeout.json(),
        'VNF_STOP_TIMEOUT': vnf_stop_timeout.json(),
        'VNF_START_TIMEOUT': vnf_start_timeout.json(),
        'VNF_TERMINATE_TIMEOUT': vnf_terminate_timeout.json(),
        'VNF_STABLE_STATE_TIMEOUT': vnf_stable_state_timeout.json(),
        'NS_INSTANTIATE_TIMEOUT': ns_instantiate_timeout.json(),
        'NS_SCALE_TIMEOUT': ns_scale_timeout.json(),
        'NS_TERMINATE_TIMEOUT': ns_terminate_timeout.json(),
        'POLL_INTERVAL': poll_interval.json(),
        'LOW_TRAFFIC_LOAD': low_traffic_load.json(),
        'NORMAL_TRAFFIC_LOAD': normal_traffic_load.json(),
        'MAX_TRAFFIC_LOAD': max_traffic_load.json(),
        'TRAFFIC_TOLERANCE': float(traffic_tolerance.json()) * 100
    }
    return template('additional_params.html', additional_params=additional_params)


@route('/additional/update/', method="POST")
def additional_update():
    """
    This function displays a form to update the additional parameters that a customer has setup.
    """

    confirmed = request.forms.get('confirmed')
    if confirmed == 'yes':
        scaling_policy_name = request.forms.get('scaling_policy_name')
        desired_scale_out_steps = int(request.forms.get('desired_scale_out_steps') or 0)
        operate_vnf_data = get_list_by_string(request.forms.get('operate_vnf_data'))
        vnf_instantiate_timeout = int(request.forms.get('vnf_instantiate_timeout'))
        vnf_scale_timeout = int(request.forms.get('vnf_scale_timeout'))
        vnf_stop_timeout = int(request.forms.get('vnf_stop_timeout'))
        vnf_start_timeout = int(request.forms.get('vnf_start_timeout'))
        vnf_terminate_timeout = int(request.forms.get('vnf_terminate_timeout'))
        vnf_stable_state_timeout = int(request.forms.get('vnf_stable_state_timeout'))
        ns_instantiate_timeout = int(request.forms.get('ns_instantiate_timeout'))
        ns_scale_timeout = int(request.forms.get('ns_scale_timeout'))
        ns_terminate_timeout = int(request.forms.get('ns_terminate_timeout'))
        poll_interval = int(request.forms.get('poll_interval'))
        low_traffic_load = int(request.forms.get('low_traffic_load'))
        normal_traffic_load = int(request.forms.get('normal_traffic_load'))
        max_traffic_load = int(request.forms.get('max_traffic_load'))
        traffic_tolerance = float(request.forms.get('traffic_tolerance')) / 100
        requests.put(url='http://localhost:8080/v1.0/config/scaling_policy_name', json=scaling_policy_name)
        requests.put(url='http://localhost:8080/v1.0/config/desired_scale_out_steps', json=desired_scale_out_steps)
        requests.put(url='http://localhost:8080/v1.0/config/operate_vnf_data', json=operate_vnf_data)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_INSTANTIATE_TIMEOUT', json=vnf_instantiate_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_SCALE_TIMEOUT', json=vnf_scale_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_STOP_TIMEOUT', json=vnf_stop_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_START_TIMEOUT', json=vnf_start_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_TERMINATE_TIMEOUT', json=vnf_terminate_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/VNF_STABLE_STATE_TIMEOUT', json=vnf_stable_state_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/NS_INSTANTIATE_TIMEOUT', json=ns_instantiate_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/NS_SCALE_TIMEOUT', json=ns_scale_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/NS_TERMINATE_TIMEOUT', json=ns_terminate_timeout)
        requests.put(url='http://localhost:8080/v1.0/config/POLL_INTERVAL', json=poll_interval)
        requests.put(url='http://localhost:8080/v1.0/config/LOW_TRAFFIC_LOAD', json=low_traffic_load)
        requests.put(url='http://localhost:8080/v1.0/config/NORMAL_TRAFFIC_LOAD', json=normal_traffic_load)
        requests.put(url='http://localhost:8080/v1.0/config/MAX_TRAFFIC_LOAD', json=max_traffic_load)
        requests.put(url='http://localhost:8080/v1.0/config/TRAFFIC_TOLERANCE', json=traffic_tolerance)
        return additional()
    else:
        scaling_policy_name = requests.get(url='http://localhost:8080/v1.0/config/scaling_policy_name')
        desired_scale_out_steps = requests.get(url='http://localhost:8080/v1.0/config/desired_scale_out_steps')
        operate_vnf_data = get_str_by_unicode(
            requests.get(url='http://localhost:8080/v1.0/config/operate_vnf_data').json())
        vnf_instantiate_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_INSTANTIATE_TIMEOUT')
        vnf_scale_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_SCALE_TIMEOUT')
        vnf_stop_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_STOP_TIMEOUT')
        vnf_start_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_START_TIMEOUT')
        vnf_terminate_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_TERMINATE_TIMEOUT')
        vnf_stable_state_timeout = requests.get(url='http://localhost:8080/v1.0/config/VNF_STABLE_STATE_TIMEOUT')
        ns_instantiate_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_INSTANTIATE_TIMEOUT')
        ns_scale_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_SCALE_TIMEOUT')
        ns_terminate_timeout = requests.get(url='http://localhost:8080/v1.0/config/NS_TERMINATE_TIMEOUT')
        poll_interval = requests.get(url='http://localhost:8080/v1.0/config/POLL_INTERVAL')
        low_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/LOW_TRAFFIC_LOAD')
        normal_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/NORMAL_TRAFFIC_LOAD')
        max_traffic_load = requests.get(url='http://localhost:8080/v1.0/config/MAX_TRAFFIC_LOAD')
        traffic_tolerance = requests.get(url='http://localhost:8080/v1.0/config/TRAFFIC_TOLERANCE')
        additional_params = {
            'scaling_policy_name': scaling_policy_name.json(),
            'desired_scale_out_steps': desired_scale_out_steps.json(),
            'operate_vnf_data': operate_vnf_data,
            'VNF_INSTANTIATE_TIMEOUT': vnf_instantiate_timeout.json(),
            'VNF_SCALE_TIMEOUT': vnf_scale_timeout.json(),
            'VNF_STOP_TIMEOUT': vnf_stop_timeout.json(),
            'VNF_START_TIMEOUT': vnf_start_timeout.json(),
            'VNF_TERMINATE_TIMEOUT': vnf_terminate_timeout.json(),
            'VNF_STABLE_STATE_TIMEOUT': vnf_stable_state_timeout.json(),
            'NS_INSTANTIATE_TIMEOUT': ns_instantiate_timeout.json(),
            'NS_SCALE_TIMEOUT': ns_scale_timeout.json(),
            'NS_TERMINATE_TIMEOUT': ns_terminate_timeout.json(),
            'POLL_INTERVAL': poll_interval.json(),
            'LOW_TRAFFIC_LOAD': low_traffic_load.json(),
            'NORMAL_TRAFFIC_LOAD': normal_traffic_load.json(),
            'MAX_TRAFFIC_LOAD': max_traffic_load.json(),
            'TRAFFIC_TOLERANCE': float(traffic_tolerance.json()) * 100
        }
        return template('additional_params_update.html', additional_params=additional_params)


@route('/twister/')
def twister():
    twister_url = 'http://%s:8000' % request.headers['Host'].split(':')[0]
    redirect(twister_url)


@route('/kibana/')
def kibana():
    kibana_url = 'http://%s:5601' % request.headers['Host'].split(':')[0]
    redirect(kibana_url)


@route('/reports/')
def get_reports_list():
    reports = requests.get(url='http://localhost:8080/v1.0/reports?type=html')
    reports_list = reports.json()['reports']
    return template('reports.html', reports_list=reports_list)


@route('/reports/<report_name>')
def get_report(report_name):
    return requests.get(url='http://localhost:8080/v1.0/reports/%s' % report_name)


@route('/static/<filename:re:.*\.css|.*\.css\.map>')
def all_css(filename):
    """
    This function is for bottle to find the path to the .css files used for styling.
    :param filename: Name of the css file
    """
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/css/")))


@route('/static/<filename:re:.*\.png|.*\.jpeg>')
def all_img(filename):
    """
    This function is for bottle to find the path to the image files.
    :param filename: Name of the image file
    """

    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/img/")))


@route('/static/<filename:re:.*\.js>')
def all_js(filename):
    """
    This function is for bottle to find the path to the javascript files.
    :param filename: Name of the javascript file
    """

    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/js/")))


@route('/fonts/<font>')
def all_img(font):
    """
    This function is for bottle to find the path to the font files.
    :param font: Name of the font file
    """

    return static_file(font,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/fonts/")))


def set_default_additional():
    timers = {'VNF_INSTANTIATE_TIMEOUT': 600,
              'VNF_SCALE_TIMEOUT': 360,
              'VNF_START_TIMEOUT': 300,
              'VNF_STOP_TIMEOUT': 300,
              'VNF_TERMINATE_TIMEOUT': 300,
              'VNF_STABLE_STATE_TIMEOUT': 360,
              'NS_INSTANTIATE_TIMEOUT': 600,
              'NS_SCALE_TIMEOUT': 360,
              'NS_TERMINATE_TIMEOUT': 300,
              'POLL_INTERVAL': 5,
              'TRAFFIC_TOLERANCE': 1}
    traffic_load_values = {'LOW_TRAFFIC_LOAD': 1,
                           'NORMAL_TRAFFIC_LOAD': 3,
                           'MAX_TRAFFIC_LOAD': 5}
    for item in timers.keys():
        config = requests.get(url='http://localhost:8080/v1.0/config/' + item)
        if str(config.json()) == 'None':
            default_value = timers[item]
            requests.put(url='http://localhost:8080/v1.0/config/' + item, json=default_value)
    for item in traffic_load_values:
        config = requests.get(url='http://localhost:8080/v1.0/config/' + item)
        if str(config.json()) == 'None':
            default_value = traffic_load_values[item]
            requests.put(url='http://localhost:8080/v1.0/config/' + item, json=default_value)


def struct_mano(type, name, **kwargs):
    """
    This is a helper function for building the JSON for a MANO element
    :param type: MANO type
    :param name: MANO name
    :param user_domain_name: User Domain Name
    :param username: Username
    :param password: Password
    :param project_domain_name: Project Domain Name
    :param project_name: Project Name
    :param auth_url: Authentication URL
    :param identity_api_version: Keystone version
    :return: The function returns a tuple containing MANO name and associated structure
    """
    if type == 'tacker':
        mano = {
            'type': type,
            'client_config': {
                'user_domain_name': kwargs['user_domain_name'],
                'username': kwargs['username'],
                'password': kwargs['password'],
                'project_domain_name': kwargs['project_domain_name'],
                'project_name': kwargs['project_name'],
                'auth_url': kwargs['auth_url'],
                'identity_api_version': kwargs['identity_api_version']
            },
            'vnfd_id': kwargs['vnfd_id'],
            'nsd_id': kwargs['nsd_id']
        }
    elif type == 'cisco':
        mano = {
            'type': type,
            'client_config': {
                'nso_hostname': kwargs['nso_hostname'],
                'nso_username': kwargs['nso_username'],
                'nso_password': kwargs['nso_password'],
                'nso_port': kwargs['nso_port'],
                'esc_hostname': kwargs['esc_hostname'],
                'esc_username': kwargs['esc_username'],
                'esc_password': kwargs['esc_password'],
                'esc_port': kwargs['esc_port']
            },
            'vnfd_id': kwargs['vnfd_id'],
            'nsd_id': kwargs['nsd_id'],
            'flavour_id': kwargs['flavour_id'],
            'instantiation_level_id': kwargs['instantiation_level_id']
        }
    elif type == 'sdl':
        mano = {
            'type': type,
            'client_config': {
                'nfv_api_url': kwargs['nfv_api_url'],
                'ui_api_url': kwargs['ui_api_url'],
                'tenant_id': kwargs['tenant_id'],
                'username': kwargs['username'],
                'password': kwargs['password']
            },
            'nsd_id': kwargs['nsd_id']
        }
    elif type == 'rift':
        mano = {
            'type': type,
            'client_config': {
                'url': kwargs['url'],
                'username': kwargs['username'],
                'password': kwargs['password'],
                'project': kwargs['project']
            },
            'instantiation_params_for_ns': {'datacenter': kwargs['datacenter']},
            'scale_params': {'scaling_group_name': kwargs['scaling_group_name']},
            'nsd_id': kwargs['nsd_id']
        }
    elif type == 'openbaton':
        mano = {
            'type': type,
            'client_config': {
                'url': kwargs['url'],
                'username': kwargs['username'],
                'password': kwargs['password'],
                'project': kwargs['project'],
                'vim_info': kwargs['vim_info']
            },
            'nsd_id': kwargs['nsd_id']
        }

    return (name, mano)


def struct_vim(type, name, user_domain_name, username, password, project_domain_name, project_name, auth_url,
               identity_api_version):
    """
    This is a helper function for building the JSON for a VIM element
    :param type: VIM type
    :param name: VIM name
    :param user_domain_name: User Domain Name
    :param username: Username
    :param password: Password
    :param project_domain_name: Project Domain Name
    :param project_name: Project Name
    :param auth_url: Authentication URL
    :param identity_api_version: Keystone version
    :return: The function returns a tuple containing MANO name and associated structure
    """

    vim = {
        'type': type,
        'client_config': {
            'user_domain_name': user_domain_name,
            'username': username,
            'password': password,
            'project_domain_name': project_domain_name,
            'project_name': project_name,
            'auth_url': auth_url,
            'identity_api_version': identity_api_version
        }
    }
    return (name, vim)


def struct_em(type, name, user_domain_name, username, password, project_domain_name, project_name, auth_url,
              identity_api_version):
    """
    This is a helper function for building the JSON for a VIM element
    :param type: EM type
    :param name: EM name
    :param user_domain_name: User Domain Name
    :param username: Username
    :param password: Password
    :param project_domain_name: Project Domain Name
    :param project_name: Project Name
    :param auth_url: Authentication URL
    :param identity_api_version: Keystone version
    :return: The function returns a tuple containing MANO name and associated structure
    """

    em = {
        'type': type,
        'client_config': {
            'user_domain_name': user_domain_name,
            'username': username,
            'password': password,
            'project_domain_name': project_domain_name,
            'project_name': project_name,
            'auth_url': auth_url,
            'identity_api_version': identity_api_version
        }
    }
    return (name, em)


def validate(element, struct):
    """
    This is a helper function to validate one configured MANO or VIM against the REST API server. The REST server
    actually tries to connect to the configured element.
    :param element: Element can be a MANO or a VIM
    :param struct: a dictionary containing the
    :return: The function returns a dictionary containig either warning or message keys. If warning is set, then
    connection to the element has failed. If message is set, then connection to the element succeeded.
    """
    response = requests.put(url='http://localhost:8080/v1.0/validate/%s' % element, json=struct)
    if response.status_code == 504:
        warning = response.json().get('warning')
        return {'warning': warning, 'message': None}
    elif response.status_code == 200:
        message = response.json().get('message')
        return {'warning': None, 'message': message}


def get_list_by_string(raw_input):
    result_list = []
    for element in raw_input.split(','):
        element = element.lstrip()
        element = element.rstrip()
        result_list.append(element)
    return result_list


def get_string_by_list(elem_list):
    result = ', '.join(elem_list)
    return result


def get_str_by_unicode(raw_input):
    result_list = []
    result_string = ''
    temp_list = raw_input.lstrip('[').rstrip(']').split(',')
    for item in temp_list:
        item = item.lstrip()
        item = item.lstrip('u')
        item = item.lstrip('\'').rstrip('\'')
        result_list.append(str(item))
    result_string = ', '.join(result_list)
    return result_string


def prepare_option_list(option_type, selected=None):
    if option_type == "vim":
        option_list = requests.get(url='http://localhost:8080/v1.0/vim').json().keys()
        if selected and selected in option_list:
            option_list.remove(selected)
            option_list.insert(0, selected)

    return option_list


run(host='0.0.0.0', port=8081, debug=False)
