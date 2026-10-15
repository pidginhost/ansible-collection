# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import ip as ip_module

IPV4 = "/api/cloud/ipv4/"
IPV6 = "/api/cloud/ipv6/"


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def ip(**kw):
    base = {"id": 7, "slug": "192.0.2.10", "address": "192.0.2.10", "gateway": "192.0.2.1", "prefix": 24,
            "attached": False, "server": "", "server_id": None}
    base.update(kw)
    return base


def test_allocates_new_address_and_sets_reverse_dns(api, run):
    api.add("POST", IPV4, ip(), status=201)
    api.add("POST", IPV4 + "7/rdns/", {"reverse_dns": "web1.example.com"})

    result = run(ip_module, version=4, reverse_dns="web1.example.com")

    assert not result.failed, result.result
    assert result.changed
    assert [(c[0], c[1], c[2]) for c in api.writes()] == [
        ("POST", IPV4, {}), ("POST", IPV4 + "7/rdns/", {"reverse_dns": "web1.example.com"})]
    assert result["ip"]["address"] == "192.0.2.10"
    assert result["ip"]["reverse_dns"] == "web1.example.com"


def test_allocate_check_mode_makes_no_writes(api, run):
    result = run(ip_module, check_mode=True, version=6)

    assert result.changed
    assert api.calls == []


def test_existing_address_with_same_reverse_dns_is_unchanged(api, run):
    api.add("GET", IPV4, listing(ip()))
    api.add("GET", IPV4 + "7/rdns/", {"reverse_dns": "web1.example.com"})

    result = run(ip_module, address="192.0.2.10", reverse_dns="web1.example.com")

    assert not result.failed
    assert not result.changed
    assert result["ip"]["reverse_dns"] == "web1.example.com"
    assert api.writes() == []


def test_existing_ipv6_gets_new_reverse_dns(api, run):
    v6 = ip(id=9, slug="2001:db8::10", address="2001:db8::10", prefix=64)
    api.add("GET", IPV6, listing(v6))
    api.add("GET", IPV6 + "9/rdns/", {"reverse_dns": ""})
    api.add("POST", IPV6 + "9/rdns/", {"reverse_dns": "web1.example.com"})

    result = run(ip_module, address="2001:db8:0::10", reverse_dns="web1.example.com")

    assert result.changed
    assert api.writes() == [("POST", IPV6 + "9/rdns/", {"reverse_dns": "web1.example.com"})]


def test_reverse_dns_check_mode_makes_no_writes(api, run):
    api.add("GET", IPV4, listing(ip()))
    api.add("GET", IPV4 + "7/rdns/", {"reverse_dns": "old.example.com"})

    result = run(ip_module, check_mode=True, address="192.0.2.10", reverse_dns="web1.example.com")

    assert result.changed
    assert api.writes() == []


def test_address_not_owned_fails(api, run):
    api.add("GET", IPV4, listing(ip()))

    result = run(ip_module, address="198.51.100.5")

    assert result.failed
    assert "198.51.100.5" in result["msg"]


def test_absent_releases_address(api, run):
    api.add("GET", IPV4, listing(ip()))
    api.add("DELETE", IPV4 + "7/", status=204)

    result = run(ip_module, state="absent", address="192.0.2.10")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", IPV4 + "7/")]
    assert result["ip"]["id"] == 7


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", IPV4, listing(ip()))

    result = run(ip_module, check_mode=True, state="absent", address="192.0.2.10")

    assert result.changed
    assert api.writes() == []


def test_absent_unknown_address_is_unchanged(api, run):
    api.add("GET", IPV4, listing())

    result = run(ip_module, state="absent", address="192.0.2.10")

    assert not result.failed
    assert not result.changed
    assert result["ip"] == {}


def test_requires_version_without_address(api, run):
    result = run(ip_module, reverse_dns="web1.example.com")

    assert result.failed
    assert api.calls == []
