# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import private_network

NETS = "/api/cloud/private-networks/"


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def net(**kw):
    base = {"id": 5, "slug": "198.51.100.0/24", "address": "198.51.100.0/24", "gateway": None, "provisioned": True,
            "servers": []}
    base.update(kw)
    return base


def test_creates_missing_network(api, run):
    api.add("GET", NETS, listing())
    api.add("POST", NETS, net(gateway="198.51.100.1"), status=201)

    result = run(private_network, address="198.51.100.0/24", gateway="198.51.100.1")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", NETS, {"address": "198.51.100.0/24", "gateway": "198.51.100.1"})]
    assert result["private_network"]["id"] == 5


def test_existing_network_is_unchanged(api, run):
    api.add("GET", NETS, listing(net(gateway="198.51.100.1")))

    result = run(private_network, address="198.51.100.0/24", gateway="198.51.100.1")

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_updates_gateway(api, run):
    api.add("GET", NETS, listing(net()))
    api.add("PATCH", NETS + "5/", net(gateway="198.51.100.254"))

    result = run(private_network, address="198.51.100.0/24", gateway="198.51.100.254")

    assert result.changed
    assert api.writes() == [("PATCH", NETS + "5/", {"gateway": "198.51.100.254"})]
    assert result["private_network"]["gateway"] == "198.51.100.254"


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", NETS, listing(net()))

    result = run(private_network, check_mode=True, address="198.51.100.0/24", gateway="198.51.100.254")

    assert result.changed
    assert api.writes() == []


def test_absent_deletes_network(api, run):
    api.add("GET", NETS, listing(net()))
    api.add("DELETE", NETS + "5/", status=204)

    result = run(private_network, state="absent", address="198.51.100.0/24")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", NETS + "5/")]


def test_absent_missing_network_is_unchanged(api, run):
    api.add("GET", NETS, listing())

    result = run(private_network, state="absent", address="198.51.100.0/24")

    assert not result.failed
    assert not result.changed
    assert result["private_network"] == {}


def test_create_error_fails(api, run):
    api.add("GET", NETS, listing())
    api.add("POST", NETS, {"address": ["Invalid network."]}, status=400)

    result = run(private_network, address="192.0.2.0/24")

    assert result.failed
    assert "400" in result["msg"]
