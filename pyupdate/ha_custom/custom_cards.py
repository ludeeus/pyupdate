"""Logic to handle custom_cards."""
import logging
import os
import requests
from requests import RequestException
from pyupdate.ha_custom import common

LOGGER = logging.getLogger(__name__)


def get_info_all_cards(custom_repos=None):
    """Return all remote info if any."""
    remote_info = {}
    for url in common.get_repo_data('card', custom_repos):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for name, card in response.json().items():
                    try:
                        card = [
                            name,
                            card['version'],
                            card['remote_location'],
                            card['visit_repo'],
                            card['changelog']
                        ]
                        remote_info[name] = card
                    except KeyError:
                        print('Could not get remote info for ' + name)
        except RequestException:
            print('Could not get remote info for ' + url)
    LOGGER.debug('get_info_all_cards: %s', remote_info)
    return remote_info


def get_lovelace_gen(base_dir):
    """Get lovelace-gen true if in use."""
    return_value = False
    conf_file = base_dir + '/ui-lovelace.yaml'
    lovelace_dir = base_dir + '/lovelace'
    if os.path.isfile(conf_file) and os.path.isdir(lovelace_dir):
        with open(conf_file, 'r') as local:
            for line in local.readlines():
                if 'generated by lovelace-gen.py' in line:
                    return_value = True
    return return_value


def get_sensor_data(base_dir, show_installable=False, custom_repos=None):
    """Get sensor data."""
    cards = get_info_all_cards(custom_repos)
    cahce_data = {}
    cahce_data['domain'] = 'custom_cards'
    cahce_data['has_update'] = []
    count_updateable = 0
    if cards:
        for name, card in cards.items():
            remote_version = card[1]
            local_version = get_local_version(base_dir, name)
            has_update = (remote_version and
                          remote_version != local_version)
            not_local = (remote_version and not local_version)
            if (not not_local and
                    remote_version) or (show_installable and remote_version):
                if has_update and not not_local:
                    count_updateable = count_updateable + 1
                    cahce_data['has_update'].append(name)
                cahce_data[name] = {
                    "local": local_version,
                    "remote": remote_version,
                    "has_update": has_update,
                    "not_local": not_local,
                    "repo": card[3],
                    "change_log": card[4],
                }
    return [cahce_data, count_updateable]


def update_all(base_dir, show_installable=False, custom_repos=None):
    """Update all cards."""
    updates = get_sensor_data(base_dir, show_installable,
                              custom_repos)[0]['has_update']
    if updates is not None:
        for name in updates:
            upgrade_single(base_dir, name, custom_repos)


def upgrade_single(base_dir, name, custom_repos=None):
    """Update one card."""
    remote_info = get_info_all_cards(custom_repos)[name]
    remote_file = remote_info[2]
    local_file = get_card_dir(base_dir, name) + name + '.js'
    common.download_file(local_file, remote_file)
    upgrade_lib(base_dir, name, custom_repos)
    update_resource_version(base_dir, name, custom_repos)


def upgrade_lib(base_dir, name, custom_repos=None):
    """Update one card-lib."""
    remote_info = get_info_all_cards(custom_repos)[name]
    remote_file = remote_info[2][:-3] + '.lib.js'
    local_file = get_card_dir(base_dir, name) + name + '.lib.js'
    common.download_file(local_file, remote_file)


def install(base_dir, name, show_installable=False, custom_repos=None):
    """Install single card."""
    if name in get_sensor_data(base_dir, show_installable, custom_repos)[0]:
        upgrade_single(base_dir, name, custom_repos)


def update_resource_version(base_dir, name, custom_repos=None):
    """Update the ui-lovelace file."""
    local_version = get_local_version(base_dir, name)
    remote_version = get_info_all_cards(custom_repos)[name][1]
    conf_file = get_conf_file_path(base_dir)
    common.replace_all(conf_file,
                       name + '.js?v=' + str(local_version),
                       name + '.js?v=' + str(remote_version))


def get_card_dir(base_dir, name):
    """Get card dir."""
    conf_file = get_conf_file_path(base_dir)
    with open(conf_file, 'r') as local:
        for line in local.readlines():
            if get_lovelace_gen(base_dir):
                if name + '.js' in line:
                    card = line.split('!resource ')[1].split(name + '.js')
                    card_dir = base_dir + '/lovelace/' + card[0]
                    break
                else:
                    card_dir = base_dir + '/lovelace/'
            else:
                if '/' + name + '.js' in line:
                    card = line.split(': ')[1].split(name + '.js')
                    card_dir = base_dir + card[0].replace("local", "www")
                    break
                else:
                    card_dir = base_dir + '/www/'
    return card_dir


def get_conf_file_path(base_dir):
    """Get conf file."""
    if get_lovelace_gen(base_dir):
        return_value = os.path.join(base_dir, 'lovelace', 'main.yaml')
    else:
        return_value = os.path.join(base_dir, 'ui-lovelace.yaml')
    return return_value


def get_local_version(base_dir, name):
    """Return the local version if any."""
    return_value = None
    card_config = ''
    conf_file = get_conf_file_path(base_dir)
    if os.path.isfile(conf_file):
        with open(conf_file, 'r') as local:
            for line in local.readlines():
                if '/' + name + '.js' in line:
                    card_config = line
                    break
        local.close()
        if '=' in card_config:
            local_version = card_config.split('=')[1].split('\n')[0]
            return_value = local_version
    return return_value
