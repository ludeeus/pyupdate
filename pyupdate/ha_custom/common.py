"""Logic to handle common functions."""
import os
import requests


def get_default_repos():
    """Return default repos."""
    git_base = 'https://raw.githubusercontent.com/'
    cards = git_base + 'custom-cards/information/master/repos.json'
    components = git_base + 'custom-components/information/master/repos.json'
    return [cards, components]


def get_repo_data(resource, extra_repos=None):
    """Update the data about components."""
    if resource == 'card':
        resource = 0
    elif resource == 'component':
        resource = 1
    repos = []
    repos.append(str(get_default_repos()[resource]))
    if extra_repos is not None:
        for repo in extra_repos:
            repos.append(repo)
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
