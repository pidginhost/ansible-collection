# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import io
import json
import sys
from urllib.error import HTTPError

import pytest

from ansible.errors import AnsibleError
from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import inventory_loader

SERVERS = [
    {"id": 1, "hostname": "web1.example.com", "image": "ubuntu24", "status": "active", "project": "shop",
     "custom_os": False, "networks": {"public": {"ipv4": "192.0.2.10", "ipv6": ""}, "private": []}},
    {"id": 2, "hostname": "db1.example.com", "image": "alma9", "status": "active", "project": "",
     "custom_os": False, "networks": {"public": {"ipv4": "192.0.2.11", "ipv6": ""}, "private": []}},
    {"id": 3, "hostname": "iso.example.com", "image": "debian12", "status": "active", "project": "",
     "custom_os": True, "networks": {"public": {"ipv4": "192.0.2.12", "ipv6": ""}, "private": []}},
    {"id": 4, "hostname": "old.example.com", "image": "ubuntu18", "status": "active", "project": "",
     "custom_os": False, "networks": {"public": {"ipv4": "192.0.2.13", "ipv6": ""}, "private": []}},
]
IMAGES = [
    {"slug": "ubuntu24", "default_username": "phuser"},
    {"slug": "alma9", "default_username": "almalinux"},
    {"slug": "debian12", "default_username": "debian"},
]


def page(results, next_page=None):
    return {"count": len(results), "next": next_page, "previous": None, "results": results}


@pytest.fixture
def plugin():
    return inventory_loader.get("pidginhost.cloud.servers")


@pytest.fixture
def fake_api(monkeypatch, plugin):
    routes = {
        "/api/cloud/servers/": page(SERVERS[:2], "next"),
        "/api/cloud/servers/?page=2": page(SERVERS[2:]),
        "/api/cloud/images/": page(IMAGES),
        "/api/cloud/servers/4/": dict(SERVERS[3], username="legacy"),
    }
    calls = []

    def open_url(url, headers=None, method=None, timeout=None, **kwargs):
        assert headers["Authorization"] == "Token test-token"
        path = url[len("https://www.pidginhost.com"):]
        calls.append(path)
        if path not in routes:
            raise HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail": "Invalid token."}'))
        return io.BytesIO(json.dumps(routes[path]).encode())

    monkeypatch.setattr(sys.modules[type(plugin).__module__], "open_url", open_url)
    return routes, calls


def parse(plugin, tmp_path, config):
    path = tmp_path / "pidginhost.yml"
    path.write_text("plugin: pidginhost.cloud.servers\ntoken: test-token\n" + config)
    inventory = InventoryData()
    plugin.parse(inventory, DataLoader(), str(path), cache=False)
    return inventory


def test_every_page_becomes_a_host_with_its_login_user(plugin, fake_api, tmp_path):
    inventory = parse(plugin, tmp_path, "compose:\n  ansible_host: networks.public.ipv4\n")

    hosts = inventory.hosts
    assert sorted(hosts) == ["db1.example.com", "iso.example.com", "old.example.com", "web1.example.com"]
    assert hosts["web1.example.com"].vars["ansible_user"] == "phuser"
    assert hosts["db1.example.com"].vars["ansible_user"] == "almalinux"
    assert "ansible_user" not in hosts["iso.example.com"].vars
    assert hosts["old.example.com"].vars["ansible_user"] == "legacy"  # image no longer in the catalog
    assert hosts["db1.example.com"].vars["ansible_host"] == "192.0.2.11"
    assert hosts["web1.example.com"].vars["project"] == "shop"


def test_keyed_groups_skip_empty_values(plugin, fake_api, tmp_path):
    inventory = parse(plugin, tmp_path, "keyed_groups:\n  - key: project\n    prefix: project\n")

    assert sorted(inventory.groups["project_shop"].get_hosts(), key=str)[0].name == "web1.example.com"
    assert "project_" not in inventory.groups


def test_api_error_is_reported(plugin, fake_api, tmp_path):
    routes, unused = fake_api
    del routes["/api/cloud/servers/"]

    with pytest.raises(AnsibleError) as exc:
        parse(plugin, tmp_path, "")

    assert "401" in str(exc.value)
