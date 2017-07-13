from bottle import route, run, request, template, static_file
import requests
import os
from collections import OrderedDict

MANO_TYPES = ['tacker']
VIM_TYPES = ['openstack']
EM_TYPES = ['tacker']
TRAFFIC_TYPES = ['stcv']
VNF_TYPES = ['ubuntu']

# os.chdir(os.path.dirname(__file__))
@route('/')
def index():
    get_env_raw = requests.get(url='http://localhost:8080/v1.0/env')
    active_env_name_raw = requests.get(url='http://localhost:8080/v1.0/config/active-env')
    active_env_name = active_env_name_raw.json()
    get_env_json = get_env_raw.json()
    get_env_data = OrderedDict()
    print active_env_name
    print get_env_json
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
def env_add():
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
    return template('env_add.html', env_list=env_list)

@route('/env/delete/', method="POST")
def env_delete():
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
    env_name = request.forms.get('env_name')
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
    get_manos = requests.get(url='http://localhost:8080/v1.0/mano')
    mano_list = []
    for mano in sorted(get_manos.json().iterkeys()):
        if 'type' in get_manos.json()[mano].keys() and get_manos.json()[mano]['type'] in MANO_TYPES:
            mano_list.append((mano, get_manos.json()[mano]['type']))
        else:
            continue
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
    requests.put(url='http://localhost:8080/v1.0/mano/%s' % name, json=new_mano)
    return mano()

@route('/mano/update/', method='POST')
def mano_update():
    if request.forms.get('confirmed') == "no":
        mano_name = request.forms.get('update_mano')
        mano_data = requests.get(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
        mano_json = mano_data.json()
        mano_info = OrderedDict()
        mano_info['type'] = mano_json[mano_name]['type']
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
        mano_data = requests.get(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
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
        requests.put(url='http://localhost:8080/v1.0/mano/%s' % mano_name, json=mano_to_add)
        return mano()

@route('/mano/delete/', method='POST')
def mano_delete():
    if request.forms.get('confirmed') == "no":
        mano_name = request.forms.get('delete_mano')
        mano_data = requests.get(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
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
        requests.delete(url='http://localhost:8080/v1.0/mano/%s' % mano_name)
        return mano()

@route('/vim/')
def vim(warning=None):
    get_vims = requests.get(url='http://localhost:8080/v1.0/vim')
    vim_list=[]
    i=1
    for vim in sorted(get_vims.json().iterkeys()):
        if 'type' in get_vims.json()[vim].keys() and get_vims.json()[vim]['type'] in VIM_TYPES:
            vim_list.append((vim, get_vims.json()[vim]['type']))
        else:
            continue
        i = i+1
    return template('vim.html', vim_list=vim_list, warning=warning)

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
    response = requests.put(url='http://localhost:8080/v1.0/vim/%s' % name, json=new_vim)
    if response.status_code == 504:
        return vim(warning=response.json().get('warning'))

    return vim()

@route('/vim/update/', method='POST')
def vim_update():
    if request.forms.get('confirmed') == "no":
        vim_name = request.forms.get('update_vim')
        vim_data = requests.get(url='http://localhost:8080/v1.0/vim/%s' % vim_name)
        vim_json = vim_data.json()
        vim_info = OrderedDict()
        vim_info['type'] = vim_json[vim_name]['type']
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
        vim_data = requests.get(url='http://localhost:8080/v1.0/vim/%s' % vim_name)
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
        requests.put(url='http://localhost:8080/v1.0/vim/%s' % vim_name, json=vim_to_add)
        return vim()

@route('/vim/delete/', method='POST')
def vim_delete():
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
def vim_add(vim_type):
    return template('vim_add.html', vim_type=vim_type)

@route('/em/')
def em():
    get_ems = requests.get(url='http://localhost:8080/v1.0/em')
    em_list=[]
    i=1
    for em in sorted(get_ems.json().iterkeys()):
        if 'type' in get_ems.json()[em].keys() and get_ems.json()[em]['type'] in EM_TYPES:
            em_list.append((em, get_ems.json()[em]['type']))
        else:
            continue
        i = i+1
    return template('em.html', em_list=em_list)

@route('/em/add/<em_type>/')
def em_add(em_type):
    return template('em_add.html', em_type=em_type)

@route('/em/data/', method='POST')
def em_data():
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
        new_em={
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
    requests.put(url='http://localhost:8080/v1.0/em/%s' % name, json=new_em)
    return em()

@route('/em/update/', method='POST')
def em_update():
    if request.forms.get('confirmed') == "no":
        em_name = request.forms.get('update_em')
        em_data = requests.get(url='http://localhost:8080/v1.0/em/%s' % em_name)
        em_json = em_data.json()
        em_info = OrderedDict()
        em_info['type'] = em_json[em_name]['type']
        em_info['user_domain_name'] = em_json[em_name]['client_config']['user_domain_name']
        em_info['username'] = em_json[em_name]['client_config']['username']
        em_info['password'] = em_json[em_name]['client_config']['password']
        em_info['project_domain_name'] = em_json[em_name]['client_config']['project_domain_name']
        em_info['project_name'] = em_json[em_name]['client_config']['project_name']
        em_info['auth_url'] = em_json[em_name]['client_config']['auth_url']
        em_info['identity_api_version'] = em_json[em_name]['client_config']['identity_api_version']
        return template('em_update.html', em=em_info, em_name=em_name)
    else:
        em_name = request.forms.get('name')
        em_data = requests.get(url='http://localhost:8080/v1.0/em/%s' % em_name)
        em_json = em_data.json()
        em_type = em_json[em_name]['type']
        em_to_add = {'client_config': {}, 'type': em_type}
        em_to_add['client_config'] = {
            'auth_url': request.forms.get('auth_url'),
            'identity_api_version': request.forms.get('identity_api_version'),
            'password': request.forms.get('password'),
            'project_domain_name': request.forms.get('project_domain_name'),
            'project_name': request.forms.get('project_name'),
            'user_domain_name': request.forms.get('user_domain_name'),
            'username': request.forms.get('username')
        }
        requests.put(url='http://localhost:8080/v1.0/em/%s' % em_name, json=em_to_add)
        return em()

@route('/em/delete/', method='POST')
def em_delete():
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
    get_traffics = requests.get(url='http://localhost:8080/v1.0/traffic')
    traffic_list=[]
    i=1
    for traffic in sorted(get_traffics.json().iterkeys()):
        if 'type' in get_traffics.json()[traffic].keys() and get_traffics.json()[traffic]['type'] in TRAFFIC_TYPES:
            traffic_list.append((traffic, get_traffics.json()[traffic]['type']))
        else:
            continue
        i = i+1
    return template('traffic.html', traffic_list=traffic_list)

@route('/traffic/add/<traffic_type>/')
def traffic_add(traffic_type):
    return template('traffic_add.html', traffic_type=traffic_type)

@route('/traffic/data/', method='POST')
def traffic_data():
    type = request.forms.get('type')
    if type == 'stcv':
        name = request.forms.get('name')
        lab_server_addr = request.forms.get('lab_server_addr')
        user_name = request.forms.get('user_name')
        session_name = request.forms.get('session_name')
        left_port_location = request.forms.get('left_port_location')
        left_traffic_addr = request.forms.get('left_traffic_addr')
        left_traffic_plen = request.forms.get('left_traffic_plen')
        left_traffic_gw = request.forms.get('left_traffic_gw')
        left_traffic_gw_mac = request.forms.get('left_traffic_gw_mac')
        left_cp_name = request.forms.get('left_cp_name')
        right_port_location = request.forms.get('right_port_location')
        right_traffic_addr = request.forms.get('right_traffic_addr')
        right_traffic_plen = request.forms.get('right_traffic_plen')
        right_traffic_gw = request.forms.get('right_traffic_gw')
        port_speed = request.forms.get('port_speed')
        new_traffic={
                'client_config': {
                    'lab_server_addr': lab_server_addr,
                    'user_name': user_name,
                    'session_name': session_name,
                },
                'traffic_config': {
                    'left_port_location': left_port_location,
                    'left_traffic_addr': left_traffic_addr,
                    'left_traffic_plen': left_traffic_plen,
                    'left_traffic_gw': left_traffic_gw,
                    'left_traffic_gw_mac': left_traffic_gw_mac,
                    'left_cp_name': left_cp_name,
                    'right_port_location': right_port_location,
                    'right_traffic_addr': right_traffic_addr,
                    'right_traffic_plen': right_traffic_plen,
                    'right_traffic_gw': right_traffic_gw,
                    'port_speed': port_speed
                },
                'type': type
        }
    requests.put(url='http://localhost:8080/v1.0/traffic/%s' % name, json=new_traffic)
    return traffic()

@route('/traffic/update/', method='POST')
def traffic_update():
    if request.forms.get('confirmed') == "no":
        traffic_name = request.forms.get('update_traffic')
        traffic_data = requests.get(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        traffic_json = traffic_data.json()
        traffic_info = OrderedDict()
        traffic_info['type'] = traffic_json[traffic_name]['type']
        traffic_info['lab_server_addr'] = traffic_json[traffic_name]['client_config']['lab_server_addr']
        traffic_info['user_name'] = traffic_json[traffic_name]['client_config']['user_name']
        traffic_info['session_name'] = traffic_json[traffic_name]['client_config']['session_name']
        traffic_info['left_port_location'] = traffic_json[traffic_name]['traffic_config']['left_port_location']
        traffic_info['left_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['left_traffic_addr']
        traffic_info['left_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['left_traffic_plen']
        traffic_info['left_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw']
        traffic_info['left_traffic_gw_mac'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw_mac']
        traffic_info['left_cp_name'] = traffic_json[traffic_name]['traffic_config']['left_cp_name']
        traffic_info['right_port_location'] = traffic_json[traffic_name]['traffic_config']['right_port_location']
        traffic_info['right_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['right_traffic_addr']
        traffic_info['right_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['right_traffic_plen']
        traffic_info['right_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['right_traffic_gw']
        traffic_info['port_speed'] = traffic_json[traffic_name]['traffic_config']['port_speed']
        return template('traffic_update.html', traffic=traffic_info, traffic_name=traffic_name)
    else:
        traffic_name = request.forms.get('name')
        traffic_data = requests.get(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        traffic_json = traffic_data.json()
        traffic_type = traffic_json[traffic_name]['type']
        traffic_to_add = {'client_config': {}, 'type': traffic_type, 'traffic_config': {}}
        traffic_to_add['client_config'] = {
            'lab_server_addr': request.forms.get('lab_server_addr'),
            'user_name': request.forms.get('user_name'),
            'session_name': request.forms.get('session_name')
        }
        traffic_to_add['traffic_config'] = {
            'left_port_location': request.forms.get('left_port_location'),
            'left_traffic_addr': request.forms.get('left_traffic_addr'),
            'left_traffic_plen': request.forms.get('left_traffic_plen'),
            'left_traffic_gw': request.forms.get('left_traffic_gw'),
            'left_traffic_gw_mac': request.forms.get('left_traffic_gw_mac'),
            'left_cp_name': request.forms.get('left_cp_name'),
            'right_port_location': request.forms.get('right_port_location'),
            'right_traffic_addr': request.forms.get('right_traffic_addr'),
            'right_traffic_plen': request.forms.get('right_traffic_plen'),
            'right_traffic_gw': request.forms.get('right_traffic_gw'),
            'port_speed': request.forms.get('port_speed')
        }
        requests.put(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name, json=traffic_to_add)
        return traffic()

@route('/traffic/delete/', method='POST')
def traffic_delete():
    if request.forms.get('confirmed') == "no":
        traffic_name = request.forms.get('delete_traffic')
        traffic_data = requests.get(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        traffic_json = traffic_data.json()
        traffic_info = OrderedDict()
        traffic_info['name'] = traffic_name
        traffic_info['type'] = traffic_json[traffic_name]['type']
        traffic_info['lab_server_addr'] = traffic_json[traffic_name]['client_config']['lab_server_addr']
        traffic_info['user_name'] = traffic_json[traffic_name]['client_config']['user_name']
        traffic_info['session_name'] = traffic_json[traffic_name]['client_config']['session_name']
        traffic_info['left_port_location'] = traffic_json[traffic_name]['traffic_config']['left_port_location']
        traffic_info['left_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['left_traffic_addr']
        traffic_info['left_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['left_traffic_plen']
        traffic_info['left_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw']
        traffic_info['left_traffic_gw_mac'] = traffic_json[traffic_name]['traffic_config']['left_traffic_gw_mac']
        traffic_info['left_cp_name'] = traffic_json[traffic_name]['traffic_config']['left_cp_name']
        traffic_info['right_port_location'] = traffic_json[traffic_name]['traffic_config']['right_port_location']
        traffic_info['right_traffic_addr'] = traffic_json[traffic_name]['traffic_config']['right_traffic_addr']
        traffic_info['right_traffic_plen'] = traffic_json[traffic_name]['traffic_config']['right_traffic_plen']
        traffic_info['right_traffic_gw'] = traffic_json[traffic_name]['traffic_config']['right_traffic_gw']
        traffic_info['port_speed'] = traffic_json[traffic_name]['traffic_config']['port_speed']
        return template('traffic_delete.html', traffic=traffic_info)
    else:
        traffic_name = request.forms.get('name')
        requests.delete(url='http://localhost:8080/v1.0/traffic/%s' % traffic_name)
        return traffic()

@route('/vnf/')
def vnf(warning=None):
    get_vnfs = requests.get(url='http://localhost:8080/v1.0/vnf')
    vnf_list=[]
    for vnf in sorted(get_vnfs.json().iterkeys()):
        if 'type' in get_vnfs.json()[vnf].keys():
	    vnf_type = get_vnfs.json()[vnf]['type']
            vnf_list.append((vnf, vnf_type))
        else:
            continue
    return template('vnf.html', vnf_list=vnf_list, warning=warning)

@route('/vnf/add/', method="POST")
def vnf_add():
    return template('vnf_add.html')

@route('/vnf/data/', method='POST')
def vnf_data():
    type = request.forms.get('type')
    instance_name = request.forms.get('instance_name')
    mgmt_ip_addr = request.forms.get('mgmt_ip_addr')
    username = request.forms.get('username')
    password = request.forms.get('password')
    config = request.forms.get('config')
    new_vnf={
            'credentials': {
                'mgmt_ip_addr': mgmt_ip_addr,
                'password': password,
                'username': username
            },
            'type': type,
            'instance_name': instance_name,
            'config': config
    }
    response = requests.put(url='http://localhost:8080/v1.0/vnf/%s' % instance_name, json=new_vnf)
    if response.status_code == 504:
        return vnf(warning=response.json().get('warning'))
    return vnf()

@route('/vnf/update/', method='POST')
def vnf_update():
    if request.forms.get('confirmed') == "no":
        vnf_name = request.forms.get('update_vnf')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_info = OrderedDict()
        vnf_info['type'] = vnf_json[vnf_name]['type']
        vnf_info['instance_name'] = vnf_json[vnf_name]['instance_name']
        vnf_info['mgmt_ip_addr'] = vnf_json[vnf_name]['credentials']['mgmt_ip_addr']
        vnf_info['username'] = vnf_json[vnf_name]['credentials']['username']
        vnf_info['password'] = vnf_json[vnf_name]['credentials']['password']
        vnf_info['config'] = vnf_json[vnf_name]['config']
        return template('vnf_update.html', vnf=vnf_info, vnf_name=vnf_name)
    else:
        vnf_name = request.forms.get('instance_name')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_type = vnf_json[vnf_name]['type']
        vnf_to_add = {'credentials': {}, 
		'type': vnf_type, 
		'instance_name': request.forms.get('instance_name'), 
		'config': request.forms.get('config')}
        vnf_to_add['credentials'] = {
            'mgmt_ip_addr': request.forms.get('mgmt_ip_addr'),
            'username': request.forms.get('username'),
            'password': request.forms.get('password'),
        }
        requests.put(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name, json=vnf_to_add)
        return vnf()

@route('/vnf/delete/', method='POST')
def vnf_delete():
    if request.forms.get('confirmed') == "no":
        vnf_name = request.forms.get('delete_vnf')
        vnf_data = requests.get(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        vnf_json = vnf_data.json()
        vnf_info = OrderedDict()
        vnf_info['type'] = vnf_json[vnf_name]['type']
        vnf_info['instance_name'] = vnf_name
        vnf_info['config'] = vnf_json[vnf_name]['config']
        vnf_info['mgmt_ip_addr'] = vnf_json[vnf_name]['credentials']['mgmt_ip_addr']
        vnf_info['username'] = vnf_json[vnf_name]['credentials']['username']
        vnf_info['password'] = vnf_json[vnf_name]['credentials']['password']
        return template('vnf_delete.html', vnf=vnf_info)
    else:
        vnf_name = request.forms.get('instance_name')
        requests.delete(url='http://localhost:8080/v1.0/vnf/%s' % vnf_name)
        return vnf()

@route('/static/<filename:re:.*\.css>')
def all_css(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/css/")))

@route('/static/<filename:re:.*\.png|.*\.jpeg>')
def all_img(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/img/")))

@route('/static/<filename:re:.*\.js>')
def all_js(filename):
    return static_file(filename,
                       root=os.path.abspath(os.path.join(os.path.dirname(__file__), "bootstrap-3.3.7-dist/js/")))

run(host='0.0.0.0', port=8081, debug=False)
