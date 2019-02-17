"""Logic to handle custom_cards."""
import json
import logging
import os
from typing import IO, Any

import requests
from requests import RequestException
import yaml
from pyupdate.ha_custom import common

LOGGER = logging.getLogger(__name__)


class Loader(yaml.SafeLoader):
    """YAML Loader with `!include` constructor."""

    def __init__(self, stream: IO) -> None:
        """Initialise Loader."""
        try:
            self._root = os.path.split(stream.name)[0]
        except AttributeError:
            self._root = os.path.curdir

        super().__init__(stream)


def construct_include(loader: Loader, node: yaml.Node) -> Any:
    """Include file referenced at node."""
    filename = os.path.abspath(
        os.path.join(loader._root, loader.construct_scalar(node)))
    extension = os.path.splitext(filename)[1].lstrip('.')

    with open(filename, 'r') as localfile:
        if extension in ('yaml', 'yml'):
            return yaml.load(localfile, Loader)
        elif extension in ('json', ):
            return json.load(localfile)
        else:
            return ''.join(localfile.readlines())


yaml.add_constructor('!include', construct_include, Loader)


class CustomCards():
    """Custom_cards class."""

    def __init__(self, base_dir, mode, skip, custom_repos):
        """Init."""
        self.base_dir = base_dir
        self.mode = mode
        self.skip = skip
        self.repos = []
        self.custom_repos = custom_repos
        self.initialize()


    async def initialize(self):
        """Extra initialition."""
        default_repo = await common.get_default_repos()
        self.repos.append(default_repo)



    async def get_info_all_cards(self):
        """Return all remote info if any."""
        remote_info = {}
        for url in common.get_repo_data('card', self.custom_repos):
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


    def init_local_data(self):
        """Init new version file."""
        remote = self.get_info_all_cards()
        local_cards = self.localcards()
        LOGGER.debug("Local cards: %s", local_cards)
        for card in remote:
            current = self.local_data(card, 'get')
            if 'version' not in current:
                if card == local_cards:
                    LOGGER.debug("Setting initial version for %s", card)
                    self.local_data(card, 'set')


    def get_sensor_data(self):
        """Get sensor data."""
        cards = self.get_info_all_cards()
        cahce_data = {}
        cahce_data['domain'] = 'custom_cards'
        cahce_data['has_update'] = []
        count_updateable = 0
        if cards:
            for name, card in cards.items():
                remote_version = card[1]
                local_version = self.get_local_version(name)
                has_update = (remote_version and
                              remote_version != local_version)
                carddir = self.get_card_dir(name)
                not_local = True if carddir is None else False
                if (not not_local and remote_version):
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
        LOGGER.debug('get_sensor_data: [%s, %s]', cahce_data, count_updateable)
        return [cahce_data, count_updateable]


    async def update_all(self):
        """Update all cards."""
        updates = self.get_sensor_data()[0]['has_update']
        if updates is not None:
            LOGGER.info('update_all: "%s"', updates)
            for name in updates:
                self.upgrade_single(name)
        else:
            LOGGER.debug('update_all: No updates avaiable.')


    def upgrade_single(self, name):
        """Update one card."""
        LOGGER.debug('upgrade_single started: "%s"', name)
        remote_info = self.get_info_all_cards()[name]
        remote_file = remote_info[2]
        local_file = self.get_card_dir(name) + name + '.js'
        common.download_file(local_file, remote_file)
        self.upgrade_lib(name)
        self.upgrade_editor(name)
        self.update_resource_version(name)
        LOGGER.info('upgrade_single finished: "%s"', name)


    def upgrade_lib(self, name):
        """Update one card-lib."""
        remote_info = self.get_info_all_cards()[name]
        remote_file = remote_info[2][:-3] + '.lib.js'
        local_file = self.get_card_dir(name) + name + '.lib.js'
        common.download_file(local_file, remote_file)


    def upgrade_editor(self, name):
        """Update one card-editor."""
        remote_info = self.get_info_all_cards()[name]
        remote_file = remote_info[2][:-3] + '-editor.js'
        local_file = self.get_card_dir(name) + name + '-editor.js'
        common.download_file(local_file, remote_file)


    def install(self, name):
        """Install single card."""
        if name in self.get_sensor_data()[0]:
            self.upgrade_single(name)


    def update_resource_version(self, name):
        """Update the ui-lovelace file."""
        remote_version = self.get_info_all_cards()[name][1]
        self.local_data(name, 'set', str(remote_version))


    def get_card_dir(self, name):
        """Get card dir."""
        card_dir = None
        if self.mode == 'storage':
            for entry in self.storage_resources():
                if entry['url'][:4] == 'http':
                    continue
                entry_name = entry['url'].split('/')[-1].split('.js')[0]
                if name == entry_name:
                    card_dir = entry['url']
                    break
        else:
            for entry in self.yaml_resources():
                if entry['url'][:4] == 'http':
                    continue
                entry_name = entry['url'].split('/')[-1].split('.js')[0]
                if name == entry_name:
                    card_dir = entry['url']
                    break

        if card_dir is None:
            return None

        if '/customcards/' in card_dir:
            card_dir = card_dir.replace('/customcards/', '/www/')
        if '/local/' in card_dir:
            card_dir = card_dir.replace('/local/', '/www/')
        return "{}{}".format(self.base_dir, card_dir).split(name + '.js')[0]


    def get_local_version(self, name):
        """Return the local version if any."""
        version = self.local_data(name, 'get').get('version')
        return version


    def local_data(self, name=None, action='get', version=None):
        """Write or get info from storage."""
        returnvalue = None
        jsonfile = "{}/.storage/custom_updater.cards".format(self.base_dir)
        if os.path.isfile(jsonfile):
            with open(jsonfile) as storagefile:
                try:
                    load = json.load(storagefile)
                except Exception as error:  # pylint: disable=W0703
                    load = {}
                    LOGGER.error(error)
        else:
            load = {}

        if action == 'get':
            if name is None:
                returnvalue = load
            else:
                returnvalue = load.get(name, {})
        else:
            card = load.get(name, {})
            card['version'] = version
            load[name] = card
            with open(jsonfile, 'w') as outfile:
                json.dump(load, outfile, indent=4)
        return returnvalue


    def storage_resources(self):
        """Load resources from storage."""
        jsonfile = "{}/.storage/lovelace".format(self.base_dir)
        if os.path.isfile(jsonfile):
            with open(jsonfile) as localfile:
                load = json.load(localfile)
                return load['data']['config'].get('resources', {})
        else:
            LOGGER.error("Lovelace config in .storage not found.")
        return {}


    def yaml_resources(self):
        """Load resources from yaml."""
        yamlfile = "{}/ui-lovelace.yaml".format(self.base_dir)
        if os.path.isfile(yamlfile):
            with open(yamlfile) as localfile:
                load = yaml.load(localfile, Loader)
                return load.get('resources', {})
        else:
            LOGGER.error("Lovelace config in yaml file not found.")
        return {}


    def localcards(self):
        """Return local cards."""
        local_cards = []
        if self.mode == 'storage':
            for entry in self.storage_resources():
                if entry['url'][:4] == 'http':
                    break
                local_cards.append(entry['url'].split('/')[-1].split('.js')[0])
        else:
            for entry in self.yaml_resources():
                if entry['url'][:4] == 'http':
                    break
                local_cards.append(entry['url'].split('/')[-1].split('.js')[0])

        return local_cards
