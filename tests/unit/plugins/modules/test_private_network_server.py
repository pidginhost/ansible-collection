# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import private_network_server

SERVERS = "/api/cloud/servers/"
NETS = "/api/cloud/private-networks/"
NET = {"id": 5, "slug": "198.51.100.0/24", "address": "198.51.100.0/24", "gateway": None, "provisioned": True,
       "servers": []}
MEMBER = {"interface": "eth1", "address": "198.51.100.10", "network": "198.51.100.0/24"}


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def detail(*private):
    other = {"interface": "eth2", "address": "203.0.113.10", "network": "203.0.113.0/24"}
    return {"id": 42, "hostname": "web1", "status": "active",
            "networks": {"public": {}, "private": [other] + list(private)}}


def test_adds_server_by_hostname_to_network_by_cidr(api, run):
    api.add("GET", NETS, listing(NET))
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", detail())
    api.add("GET", SERVERS + "42/", detail(MEMBER))
    api.add("POST", NETS + "5/add-server/", {"created": True})

    result = run(private_network_server, network="198.51.100.0/24", server_hostname="web1", address="198.51.100.10")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", NETS + "5/add-server/", {"server": "42", "address": "198.51.100.10"})]
    assert result["server"] == MEMBER


def test_member_is_unchanged(api, run):
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", detail(MEMBER))

    result = run(private_network_server, network="5", server_id=42)

    assert not result.failed, result.result
    assert not result.changed
    assert result["server"] == MEMBER
    assert api.writes() == []


def test_member_with_other_address_is_moved(api, run):
    moved = dict(MEMBER, address="198.51.100.20")
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", detail(MEMBER))
    api.add("GET", SERVERS + "42/", detail(moved))
    api.add("POST", NETS + "5/remove-server/", {"removed": True})
    api.add("POST", NETS + "5/add-server/", {"created": True})

    result = run(private_network_server, network="5", server_id=42, address="198.51.100.20")

    assert result.changed
    assert api.writes() == [
        ("POST", NETS + "5/remove-server/", {"server": "198.51.100.10"}),
        ("POST", NETS + "5/add-server/", {"server": "42", "address": "198.51.100.20"}),
    ]
    assert result["server"] == moved


def test_add_check_mode_makes_no_writes(api, run):
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", detail())

    result = run(private_network_server, check_mode=True, network="5", server_id=42)

    assert result.changed
    assert api.writes() == []


def test_absent_removes_member(api, run):
    api.add("GET", NETS, listing(NET))
    api.add("GET", SERVERS + "42/", detail(MEMBER))
    api.add("POST", NETS + "5/remove-server/", {"removed": True})

    result = run(private_network_server, state="absent", network="198.51.100.0/24", server_id=42)

    assert result.changed
    assert api.writes() == [("POST", NETS + "5/remove-server/", {"server": "198.51.100.10"})]
    assert result["server"] == MEMBER


def test_absent_non_member_is_unchanged(api, run):
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", detail())

    result = run(private_network_server, state="absent", network="5", server_id=42)

    assert not result.failed
    assert not result.changed
    assert result["server"] == {}


def test_absent_missing_network_is_unchanged(api, run):
    api.add("GET", NETS, listing())

    result = run(private_network_server, state="absent", network="198.51.100.0/24", server_id=42)

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_present_missing_network_fails(api, run):
    api.add("GET", NETS + "9/", status=404)

    result = run(private_network_server, network="9", server_id=42)

    assert result.failed
    assert "9" in result["msg"]


def test_invalid_replacement_keeps_existing_membership(api, run):
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", detail(MEMBER))

    for address in ("invalid", "203.0.113.10", "198.51.100.0", "198.51.100.255", "2001:db8::1"):
        result = run(private_network_server, network="5", server_id=42, address=address)

        assert result.failed
        assert api.writes() == []


def test_occupied_replacement_keeps_existing_membership(api, run):
    api.add("GET", NETS + "5/", dict(NET, servers=[{"server": "other.example.com", "address": "198.51.100.20"}]))
    api.add("GET", SERVERS + "42/", detail(MEMBER))

    result = run(private_network_server, network="5", server_id=42, address="198.51.100.20")

    assert result.failed
    assert "already in use" in result["msg"]
    assert api.writes() == []


def test_inactive_server_keeps_existing_membership(api, run):
    api.add("GET", NETS + "5/", NET)
    api.add("GET", SERVERS + "42/", dict(detail(MEMBER), status="upgrading"))

    result = run(private_network_server, network="5", server_id=42, address="198.51.100.20")

    assert result.failed
    assert api.writes() == []
