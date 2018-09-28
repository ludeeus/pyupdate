"""Logic to handle custom_components."""
import os
import re
import requests
from requests import RequestException
from pyupdate.ha_custom import common


@staticmethod
def _normalize_path(path):
    path = path.replace('/', os.path.sep)\
        .replace('\\', os.path.sep)

    if path.startswith(os.path.sep):
        path = path[1:]

    return path


def get_info_all_components():
    """Return all remote info if any."""
    remote_info = {}
    for url in common.get_repo_data('component'):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for name, component in response.json().items():
                    try:
                        component = [
                            name,
                            component['version'],
                            _normalize_path(
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
    return remote_info


def get_sensor_data():
    """Get sensor data."""
    components = get_info_all_components()
    cahce_data = {}
    cahce_data['domain'] = 'custom_components'
    cahce_data['has_update'] = []
    count_updateable = 0
    if components:
        for name, component in components.items():
            remote_version = component[1]
            local_version = get_local_version(component[2])
            has_update = (remote_version and
                          remote_version != local_version)
            not_local = (remote_version and not local_version)
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
    return [cahce_data, count_updateable]


def update_all(base_dir):
    """Update all components."""
    updates = get_sensor_data()[0]['has_update']
    if updates is not None:
        for name in updates:
            upgrade_single(base_dir, name)


def upgrade_single(base_dir, name):
    """Update one component."""
    print('Starting upgrade for ' + name)
    remote_info = get_sensor_data()[0][name]
    remote_file = remote_info[3]
    local_file = os.path.join(base_dir, remote_info[2])
    common.download_file(local_file, remote_file)


def install(base_dir, name):
    """Install single component."""
    if name in get_sensor_data()[0]:
        if '.' in name:
            component = str(name).split('.')[0]
            if not os.path.isdir(component):
                path = base_dir + '/custom_components/' + component
                os.mkdir(path)
        upgrade_single(base_dir, name)


def get_local_version(local_path):
    """Return the local version if any."""
    if os.path.isfile(local_path):
        with open(local_path, 'r') as local:
            pattern = re.compile(r"^__version__\s*=\s*['\"](.*)['\"]$")
            for line in local.readlines():
                matcher = pattern.match(line)
                if matcher:
                    return_value = matcher.group(1)
                else:
                    return_value = False
    return return_value
