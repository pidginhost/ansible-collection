# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: servers
author:
  - Popescu Andrei Cristian (@shbpty)
short_description: PidginHost cloud servers inventory source
version_added: "0.2.0"
description:
  - Builds an inventory of the PidginHost cloud servers in an account.
  - The configuration file name must end with C(pidginhost.yml), C(servers.yml) or C(inventory.yml).
  - Sets C(ansible_user) to the default login user of the server image, except for servers running a custom OS.
  - Hosts missing a value for a keyed group are skipped instead of raising an error.
extends_documentation_fragment:
  - constructed
  - inventory_cache
options:
  plugin:
    description:
      - The name of this inventory plugin.
    required: true
    choices: ["pidginhost.cloud.servers"]
  token:
    description:
      - PidginHost API token. Templates are allowed.
    type: str
    env:
      - name: PIDGINHOST_ACCESS_TOKEN
      - name: PIDGINHOST_TOKEN
  timeout:
    description:
      - Seconds to wait for each API request.
    type: int
    default: 60
  attributes:
    description:
      - Server attributes to set as host variables.
      - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_list) for the available attributes.
    type: list
    elements: str
    default: [id, hostname, project, image, package, generation, status, cpus, memory, disk_size, networks]
"""

EXAMPLES = r"""
# pidginhost.yml
plugin: pidginhost.cloud.servers
cache: true
cache_plugin: ansible.builtin.jsonfile
cache_connection: ./tmp/pidginhost_servers_inventory
cache_timeout: 300
# The token is read from PIDGINHOST_ACCESS_TOKEN or PIDGINHOST_TOKEN when not set here.
# token: "{{ lookup('ansible.builtin.env', 'PIDGINHOST_TOKEN') }}"
compose:
  ansible_host: networks.public.ipv4
keyed_groups:
  - key: status
    prefix: status
  - key: project
    prefix: project
groups:
  ubuntu: "'ubuntu' in image"
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from ansible.errors import AnsibleParserError
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ..module_utils.common import BASE_URL, SERVERS


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "pidginhost.cloud.servers"

    def verify_file(self, path):
        return super(InventoryModule, self).verify_file(path) and path.endswith(
            ("pidginhost.yml", "pidginhost.yaml", "servers.yml", "servers.yaml", "inventory.yml", "inventory.yaml"))

    def _get(self, token, path, page=1):
        url = BASE_URL + path + ("?" + urlencode({"page": page}) if page > 1 else "")
        try:
            resp = open_url(url, method="GET", timeout=self.get_option("timeout"), unredirected_headers=["Authorization"], headers={
                "Authorization": "Token %s" % token, "Accept": "application/json"})
            return json.loads(to_text(resp.read()))
        except HTTPError as e:
            raise AnsibleParserError("PidginHost API GET %s returned HTTP %s: %s" % (path, e.code, to_text(e.read())))
        except (OSError, URLError, ValueError) as e:
            raise AnsibleParserError("PidginHost API GET %s failed: %s" % (path, e))

    def _list(self, token, path):
        items = []
        page = 1
        while True:
            data = self._get(token, path, page)
            items.extend(data["results"])
            if not data.get("next"):
                return items
            page += 1

    def _login_user(self, token, server, users):
        if server.get("custom_os"):
            return None
        if server.get("image") in users:
            return users[server["image"]]
        # Retired images leave the catalog; the server detail still names the user.
        return self._get(token, "%s%s/" % (SERVERS, server["id"])).get("username")

    def _fetch(self, token):
        users = dict((i["slug"], i["default_username"]) for i in self._list(token, "/api/cloud/images/"))
        servers = self._list(token, SERVERS)
        for server in servers:
            server["login_user"] = self._login_user(token, server, users)
        return servers

    def _populate(self, servers):
        strict = self.get_option("strict")
        for server in servers:
            host = server.get("hostname")
            if not host:
                continue
            self.inventory.add_host(host)
            for attribute in self.get_option("attributes"):
                if attribute in server:
                    self.inventory.set_variable(host, attribute, server[attribute])
            if server.get("login_user"):
                self.inventory.set_variable(host, "ansible_user", server["login_user"])

            host_vars = self.inventory.get_host(host).get_vars()
            self._set_composite_vars(self.get_option("compose"), host_vars, host, strict=strict)
            self._add_host_to_composed_groups(self.get_option("groups"), host_vars, host, strict=strict)
            self._add_host_to_keyed_groups(self.get_option("keyed_groups"), host_vars, host, strict=False)

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        token = self.get_option("token")
        if token and self.templar.is_template(token):
            token = self.templar.template(token)
        if not token:
            raise AnsibleParserError(
                "Set the PidginHost API token with the inventory 'token' option or the "
                "PIDGINHOST_ACCESS_TOKEN or PIDGINHOST_TOKEN environment variable.")

        cache_key = self.get_cache_key(path)
        use_cache = self.get_option("cache") and cache
        servers = None
        if use_cache:
            try:
                servers = self._cache[cache_key]
            except KeyError:
                pass
        if servers is None:
            servers = self._fetch(token)
            if self.get_option("cache"):
                self._cache[cache_key] = servers
        self._populate(servers)
