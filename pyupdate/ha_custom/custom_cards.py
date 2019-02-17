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
        self.local_cards = []
        self.custom_repos = custom_repos
        self.remote_info = {}
        self.initialize()


    async def initialize(self):
        """Extra initialition."""
        default_repo = await common.get_default_repos()
        self.repos.append(default_repo)



    async def get_info_all_cards(self, force=False):
        """Return all remote info if any."""
        if not force and self.remote_info:
            return self.remote_info
        remote_info = {}
        for url in await common.get_repo_data('card', self.custom_repos):
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
        self.remote_info = remote_info
        return remote_info


    async def init_local_data(self):
        """Init new version file."""
        remote = await self.get_info_all_cards()
        local_cards = self.localcards()
        LOGGER.debug("Local cards: %s", local_cards)
        for card in remote:
            current = await self.local_data(card, 'get')
            if 'version' not in current:
                if card == local_cards:
                    LOGGER.debug("Setting initial version for %s", card)
                    self.local_data(card, 'set')


    async def get_sensor_data(self):
        """Get sensor data."""
        LOGGER.debug('get_sensor_data')
        cards = await self.get_info_all_cards()
        LOGGER.debug(cards)
        cahce_data = {}
        cahce_data['domain'] = 'custom_cards'
        cahce_data['has_update'] = []
        count_updateable = 0
        if cards:
            for name, card in cards.items():
                remote_version = card[1]
                local_version = await self.get_local_version(name)
                has_update = (remote_version and
                              remote_version != local_version)
                carddir = await self.get_card_dir(name)
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
        updates = await self.get_sensor_data()
        updates = updates[0]['has_update']
        if updates is not None:
            LOGGER.info('update_all: "%s"', updates)
            for name in updates:
                await self.upgrade_single(name)
            await self.get_info_all_cards(force=True)
        else:
            LOGGER.debug('update_all: No updates avaiable.')


    async def upgrade_single(self, name):
        """Update one card."""
        LOGGER.debug('upgrade_single started: "%s"', name)
        remote_info = await self.get_info_all_cards()
        remote_info = remote_info[name]
        remote_file = remote_info[2]
        local_file = await self.get_card_dir(name) + name + '.js'
        await common.download_file(local_file, remote_file)
        await self.upgrade_lib(name)
        await self.upgrade_editor(name)
        await self.update_resource_version(name)
        LOGGER.info('upgrade_single finished: "%s"', name)


    async def upgrade_lib(self, name):
        """Update one card-lib."""
        remote_info = await self.get_info_all_cards()
        remote_info = remote_info[name]
        remote_file = remote_info[2][:-3] + '.lib.js'
        local_file = await self.get_card_dir(name) + name + '.lib.js'
        await common.download_file(local_file, remote_file)


    async def upgrade_editor(self, name):
        """Update one card-editor."""
        remote_info = await self.get_info_all_cards()
        remote_info = remote_info[name]
        remote_file = remote_info[2][:-3] + '-editor.js'
        local_file = await self.get_card_dir(name) + name + '-editor.js'
        await common.download_file(local_file, remote_file)


    async def install(self, name):
        """Install single card."""
        if name in await self.get_sensor_data()[0]:
            await self.upgrade_single(name)


    async def update_resource_version(self, name):
        """Update the ui-lovelace file."""
        remote_version = await self.get_info_all_cards()
        remote_version = remote_version[name][1]
        await self.local_data(name, 'set', version=str(remote_version))


    async def get_card_dir(self, name):
        """Get card dir."""
        resources = {}
        card_dir = None
        stored_dir = await self.local_data(name)
        stored_dir = stored_dir.get('dir', None)
        if stored_dir is not None:
            return stored_dir

        if self.mode == 'storage':
            resources = await self.storage_resources()
        else:
            resources = await self.yaml_resources()
        for entry in resources:
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

        stored_dir = "{}{}".format(
            self.base_dir, card_dir).split(name + '.js')[0]
        await self.local_data(name, action='set', localdir=stored_dir)
        return stored_dir

    async def get_local_version(self, name):
        """Return the local version if any."""
        version = await self.local_data(name)
        version = version.get('version')
        return version


    async def local_data(
            self, name=None, action='get', version=None, localdir=None):
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
            if version is not None:
                card['version'] = version
            if localdir is not None:
                card['dir'] = localdir
            load[name] = card
            with open(jsonfile, 'w') as outfile:
                json.dump(load, outfile, indent=4)
                outfile.close()
        return returnvalue


    async def storage_resources(self):
        """Load resources from storage."""
        resources = {}
        jsonfile = "{}/.storage/lovelace".format(self.base_dir)
        if os.path.isfile(jsonfile):
            with open(jsonfile) as localfile:
                load = json.load(localfile)
                resources = load['data']['config'].get('resources', {})
                localfile.close()
        else:
            LOGGER.error("Lovelace config in .storage not found.")
        return resources

    async def yaml_resources(self):
        """Load resources from yaml."""
        resources = {}
        yamlfile = "{}/ui-lovelace.yaml".format(self.base_dir)
        if os.path.isfile(yamlfile):
            with open(yamlfile) as localfile:
                load = yaml.load(localfile, Loader)
                resources = load.get('resources', {})
                localfile.close()
        else:
            LOGGER.error("Lovelace config in yaml file not found.")
        return resources

    async def localcards(self):
        """Return local cards."""
        local_cards = []
        resources = {}
        if self.mode == 'storage':
            resources = await self.storage_resources()
        else:
            resources = await self.yaml_resources()
        for entry in resources:
            if entry['url'][:4] == 'http':
                continue
            local_cards.append(entry['url'].split('/')[-1].split('.js')[0])
        self.local_cards = local_cards
