# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: servers
author:
  - Popescu Andrei Cristian (@shbpty)
  
short_description: Servers dynamic inventory plugin
version_added: "0.2.0"
description:
  - Servers dynamic inventory plugin.
extends_documentation_fragment:
  - constructed
  - inventory_cache
options:
  plugin:
    description:
      - The name of the this inventory plugin C(pidginhost.cloud.servers).
    required: true
    choices: ["pidginhost.cloud.servers"]
  token:
    description:
      - PidginHost API token.
      - There are several environment variables which can be used to provide this value.
      - C(PIDGINHOST_TOKEN), C(PIDGINHOST_ACCESS_TOKEN)
    type: str
    required: false
  attributes:
    description:
      - Servers attributes to include as host variables.
      - Consult the API documentation U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_retrieve) for attribute examples.
    type: list
    elements: str
    required: false
"""

EXAMPLES = r"""
plugin: pidginhost.cloud.droplets
cache: true
cache_plugin: ansible.builtin.jsonfile
cache_connection: ./tmp/pidginhost_servers_inventory
cache_timeout: 300
#
#  By default, this plugin will consult the following environment variables for the API token:
#  PIDGINHOST_TOKEN, PIDGINHOST_ACCESS_TOKEN
#
#  The API token can also be set statically (but please, avoid committing secrets):
#  token: hunter1
#
#  Or, lookup plugins can be used:
#  token: "{{ lookup('ansible.builtin.pipe', '/script/which/echoes/token.sh') }}"
#  token: "{{ lookup('ansible.builtin.env', 'PIDGINHOST_TOKEN') }}"
#
attributes:
  - cpus
  - disk_size
  - hostname
  - id
  - image
  - memory
  - networks
  - package
  - project
  - status
compose:
  ansible_host: networks.public.ipv4
keyed_groups:
  - key: status
    prefix: status
    separator: _
  - key: project
    prefix: project
groups:
  ubuntu: "'ubuntu' in image"
"""

from ansible.module_utils.common.parameters import env_fallback
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ..module_utils.common import PidginHostsConstants, PidginHostCommonInventory


class InventoryModule(BaseInventoryPlugin, Cacheable, Constructable):
    NAME = 'pidginhost.cloud.servers'  # used internally by Ansible, it should match the file name
    TOKEN = env_fallback("PIDGINHOST_ACCESS_TOKEN", "PIDGINHOST_TOKEN")
    VALID_ENDSWITH = (
        "inventory.yml",
        "pidginhost.yml",
        "servers.yml",
    )

    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(InventoryModule.VALID_ENDSWITH):
                valid = True
            else:
                self.display.v(
                    msg="Skipping due to inventory source file name mismatch "
                        + "the inventory file name must end with one of the following: "
                        + ", ".join(InventoryModule.VALID_ENDSWITH)
                )
        return valid

    def _populate(self, config, token):
        servers = PidginHostCommonInventory(token).get_inventory()
        for server in servers:
            host_name = server["hostname"]
            if not host_name:
                continue
            self.inventory.add_host(host_name)

            for k, v in server.items():
                attributes = config.get("attributes", [])
                if k in attributes:
                    self.inventory.set_variable(host_name, k, v)
                self.inventory.set_variable(host_name, 'ansible_user', PidginHostsConstants.PH_DEFAULT_USER)
            host_vars = self.inventory.get_host(host_name).get_vars()

            self._set_composite_vars(
                self.get_option("compose"), host_vars, host_name, True
            )
            self._add_host_to_composed_groups(
                self.get_option('groups'), host_vars, host_name, True
            )

            self._add_host_to_keyed_groups(
                self.get_option('keyed_groups'),
                host_vars,
                host_name,
                True,
            )

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        config = self._read_config_data(path)
        token = self.templar.template(config.get("token"))
        if not token:
            token = InventoryModule.TOKEN
            config.update({"token": token})

        cache_key = self.get_cache_key(path)
        use_cache = self.get_option("cache") and cache
        update_cache = self.get_option("cache") and not cache

        servers = None
        if use_cache:
            try:
                servers = self._cache[cache_key]
            except KeyError:
                update_cache = True
        if servers is None:
            servers = PidginHostCommonInventory(token).get_inventory()

        if update_cache:
            self._cache[cache_key] = servers
        self._populate(config, token)
