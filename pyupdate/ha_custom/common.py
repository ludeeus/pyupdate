"""Logic to handle common functions."""
import os
import fileinput
import logging
import subprocess
import sys
import requests

LOGGER = logging.getLogger(__name__)


def get_default_repos():
    """Return default repos."""
    git_base = 'https://raw.githubusercontent.com/'
    card = [git_base + 'custom-cards/information/master/repos.json']
    component = [git_base + 'custom-components/information/master/repos.json']
    python_script = [None]
    return {'component': component,
            'card': card,
            'python_script': python_script}


def get_repo_data(resource, extra_repos=None):
    """Update the data about components."""
    repos = []
    default_repos = get_default_repos()[resource]
    if None not in default_repos:
        for repo in default_repos:
            repos.append(str(repo))
    if extra_repos is not None:
        for repo in extra_repos:
            repos.append(str(repo))
    LOGGER.debug('get_repo_data: "%s"', repos)
    return repos


def check_local_premissions(file):
    """Check premissions of a file."""
    dirpath = os.path.dirname(file)
    return os.access(dirpath, os.W_OK)


def check_remote_access(file):
    """Check access to remote file."""
    test_remote_file = requests.get(file)
    return bool(test_remote_file.status_code == 200)


def download_file(local_file, remote_file):
    """Download a file."""
    LOGGER.debug("Downloading '%s' to '%s'", remote_file, local_file)
    if check_local_premissions(local_file):
        if check_remote_access(remote_file):
            with open(local_file, 'wb') as file:
                file.write(requests.get(remote_file).content)
            file.close()
            retrun_value = True
        else:
            print('Remote file not accessable.')
            retrun_value = False
    else:
        print('local file not writable.')
        retrun_value = False
    return retrun_value


def normalize_path(path):
    """Normalize the path."""
    path = path.replace('/', os.path.sep).replace('\\', os.path.sep)

    if path.startswith(os.path.sep):
        path = path[1:]

    return path


def replace_all(file, search, replace):
    """Replace all occupancies of search in file."""
    LOGGER.debug('Replacing all "%s" with "%s" in file "%s"', search,
                 replace, file)
    for line in fileinput.input(file, inplace=True):
        if search in line:
            line = line.replace(search, replace)
        sys.stdout.write(line)


def update(package):
    """Update a pip package."""
    subprocess.call([sys.executable,
                     "-m",
                     "pip",
                     "install",
                     "--upgrade",
                     package])
