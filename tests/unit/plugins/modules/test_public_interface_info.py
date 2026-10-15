# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import public_interface_info

SERVERS = "/api/cloud/servers/"
INTERFACE = SERVERS + "42/public-interface/"

PUBLIC = {"interface": "net0", "ipv4": "192.0.2.10", "ipv6": "", "fw_rules_set": None,
          "fw_policy_in": "ACCEPT", "fw_policy_out": "ACCEPT"}


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def test_returns_interface_by_id(api, run):
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})
    api.add("GET", INTERFACE, PUBLIC)

    result = run(public_interface_info, server_id=42, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["interfaces"] == PUBLIC


def test_returns_interface_by_hostname(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})
    api.add("GET", INTERFACE, PUBLIC)

    result = run(public_interface_info, check_mode=True, server_hostname="web1")

    assert result["interfaces"] == PUBLIC
    assert api.writes() == []


def test_server_without_public_interface_returns_empty(api, run):
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})
    api.add("GET", INTERFACE, {"message": "Server doesn't have any public IP addresses attached."}, status=404)

    result = run(public_interface_info, server_id=42)

    assert not result.failed
    assert result["interfaces"] == {}


def test_missing_server_fails(api, run):
    api.add("GET", SERVERS + "9/", status=404)

    result = run(public_interface_info, server_id=9)

    assert result.failed
