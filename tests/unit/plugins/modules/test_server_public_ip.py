# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server_public_ip

SERVERS = "/api/cloud/servers/"

NETWORKS = {
    "public": {"interface": "net0", "ipv4": "192.0.2.10", "ipv6": "2001:db8::10", "interfaces": []},
    "private": [],
}


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def test_returns_public_addresses_by_hostname(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1", "networks": NETWORKS})

    result = run(server_public_ip, server_hostname="web1", state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["server"] == "192.0.2.10"
    assert result["ipv4"] == "192.0.2.10"
    assert result["ipv6"] == "2001:db8::10"
    assert result["networks"] == NETWORKS
    assert api.writes() == []


def test_server_without_public_network(api, run):
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1", "networks": {"public": {}, "private": []}})

    result = run(server_public_ip, check_mode=True, server_id=42)

    assert not result.failed
    assert result["server"] is None
    assert result["ipv6"] is None


def test_missing_server_fails(api, run):
    api.add("GET", SERVERS, listing())

    result = run(server_public_ip, server_hostname="web1")

    assert result.failed


def test_requires_a_server(api, run):
    result = run(server_public_ip)

    assert result.failed
