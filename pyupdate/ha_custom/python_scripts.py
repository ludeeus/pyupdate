"""Logic to handle python_scripts."""
import logging
import os
import re
import requests
from requests import RequestException
from pyupdate.ha_custom import common

LOGGER = logging.getLogger(__name__)


def get_info_all_python_scripts(custom_repos=None):
    """Return all remote info if any."""
    remote_info = {}
    for url in common.get_repo_data('python_script', custom_repos):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for name, py_script in response.json().items():
                    try:
                        py_script = [
                            name,
                            py_script['version'],
                            common.normalize_path(
                                py_script['local_location']),
                            py_script['remote_location'],
                            py_script['visit_repo'],
                            py_script['changelog']
                        ]
                        remote_info[name] = py_script
                    except KeyError:
                        print('Could not get remote info for ' + name)
        except RequestException:
            print('Could not get remote info for ' + url)
    LOGGER.debug('get_info_all_python_scripts: %s', remote_info)
    return remote_info


def get_sensor_data(base_dir, show_installable=False, custom_repos=None):
    """Get sensor data."""
    python_scripts = get_info_all_python_scripts(custom_repos)
    cahce_data = {}
    cahce_data['domain'] = 'python_scripts'
    cahce_data['has_update'] = []
    count_updateable = 0
    if python_scripts:
        for name, py_script in python_scripts.items():
            remote_version = py_script[1]
            local_file = base_dir + '/' + str(py_script[2])
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
                    "repo": py_script[4],
                    "change_log": py_script[5],
                }
    LOGGER.debug('get_sensor_data: [%s, %s]', cahce_data, count_updateable)
    return [cahce_data, count_updateable]


def update_all(base_dir, show_installable=False, custom_repos=None):
    """Update all python_script."""
    updates = get_sensor_data(base_dir,
                              show_installable, custom_repos)[0]['has_update']
    if updates is not None:
        LOGGER.info('update_all: "%s"', updates)
        for name in updates:
            upgrade_single(base_dir, name, custom_repos)
    else:
        LOGGER.debug('update_all: No updates avaiable.')


def upgrade_single(base_dir, name, custom_repos=None):
    """Update one python_script."""
    LOGGER.debug('upgrade_single started: "%s"', name)
    remote_info = get_info_all_python_scripts(custom_repos)[name]
    remote_file = remote_info[3]
    local_file = base_dir + '/' + str(remote_info[2])
    common.download_file(local_file, remote_file)
    LOGGER.info('upgrade_single finished: "%s"', name)


def install(base_dir, name, custom_repos=None):
    """Install single python_script."""
    if name in get_sensor_data(base_dir, True, custom_repos)[0]:
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
