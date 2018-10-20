"""Logic to handle custom_components."""
import os
import re
import logging
import requests
from requests import RequestException
from pyupdate.ha_custom import common

LOGGER = logging.getLogger(__name__)


def get_info_all_components(custom_repos=None):
    """Return all remote info if any."""
    remote_info = {}
    for url in common.get_repo_data('component', custom_repos):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for name, component in response.json().items():
                    try:
                        component = [
                            name,
                            component['version'],
                            common.normalize_path(
                                component['local_location']),
                            component['remote_location'],
                            component['visit_repo'],
                            component['changelog']
                        ]
                        remote_info[name] = component
                    except KeyError:
                        print('Could not get remote info for ' + name)
        except RequestException:
            print('Could not get remote info for ' + url)
    LOGGER.debug('get_info_all_components: %s', remote_info)
    return remote_info


def get_sensor_data(base_dir, show_installable=False, custom_repos=None):
    """Get sensor data."""
    components = get_info_all_components(custom_repos)
    cahce_data = {}
    cahce_data['domain'] = 'custom_components'
    cahce_data['has_update'] = []
    count_updateable = 0
    if components:
        for name, component in components.items():
            remote_version = component[1]
            local_file = base_dir + '/' + str(component[2])
            local_version = get_local_version(local_file)
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
                    "repo": component[4],
                    "change_log": component[5],
                }
    LOGGER.debug('get_sensor_data: [%s, %s]', cahce_data, count_updateable)
    return [cahce_data, count_updateable]


def update_all(base_dir, show_installable=False, custom_repos=None):
    """Update all components."""
    updates = get_sensor_data(base_dir,
                              show_installable, custom_repos)[0]['has_update']
    if updates is not None:
        LOGGER.info('update_all: "%s"', updates)
        for name in updates:
            upgrade_single(base_dir, name, custom_repos)
    else:
        LOGGER.debug('update_all: No updates avaiable.')


def upgrade_single(base_dir, name, custom_repos=None):
    """Update one component."""
    LOGGER.debug('upgrade_single started: "%s"', name)
    remote_info = get_info_all_components(custom_repos)[name]
    remote_file = remote_info[3]
    local_file = base_dir + '/' + str(remote_info[2])
    common.download_file(local_file, remote_file)
    update_requirements(local_file)
    LOGGER.info('upgrade_single finished: "%s"', name)


def install(base_dir, name, custom_repos=None):
    """Install single component."""
    if name in get_sensor_data(base_dir, True, custom_repos)[0]:
        if '.' in name:
            component = str(name).split('.')[0]
            path = base_dir + '/custom_components/' + component
            if not os.path.isdir(path):
                os.mkdir(path)
        upgrade_single(base_dir, name, custom_repos)


def get_local_version(path):
    """Return the local version if any."""
    return_value = ''
    if os.path.isfile(path):
        with open(path, 'r') as local:
            ret = re.compile(r"^\b(VERSION|__version__)\s*=\s*['\"](.*)['\"]")
            for line in local.readlines():
                matcher = ret.match(line)
                if matcher:
                    return_value = str(matcher.group(2))
    return return_value


def update_requirements(path):
    """Update the requirements for a python file."""
    requirements = None
    if os.path.isfile(path):
        with open(path, 'r') as local:
            ret = re.compile(r"^\bREQUIREMENTS\s*=\s*(.*)")
            for line in local.readlines():
                matcher = ret.match(line)
                if matcher:
                    val = str(matcher.group(1))
                    val = val.replace('[', '')
                    val = val.replace(']', '')
                    val = val.replace(',', '')
                    val = val.replace("'", "")
                    requirements = val
        local.close()
        if requirements is not None:
            for package in requirements.split(' '):
                LOGGER.info('Upgrading %s', package)
                common.update(package)
