# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import ip_action

SERVERS = "/api/cloud/servers/"
IPV4 = "/api/cloud/ipv4/"
IPV6 = "/api/cloud/ipv6/"


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def ip(**kw):
    base = {"id": 7, "slug": "192.0.2.10", "address": "192.0.2.10", "gateway": "192.0.2.1", "prefix": 24,
            "attached": False, "server": "", "server_id": None}
    base.update(kw)
    return base


def attached(**kw):
    return ip(attached=True, server="web1", server_id=42, **kw)


def test_attaches_ipv4_by_hostname(api, run):
    api.add("GET", IPV4, listing(ip()))
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})
    api.add("POST", SERVERS + "42/attach-ipv4/", {"attached": True, "reboot_required": True, "rebooted": False})
    api.add("GET", IPV4 + "7/", attached())

    result = run(ip_action, ip_address="192.0.2.10", server_hostname="web1")

    assert not result.failed, result.result
    assert result.changed
    assert api.requests("POST")[0][2] == {"ipv4": "192.0.2.10", "reboot": False}
    assert result["ip_result"]["attached"]
    assert result["ip"]["server_id"] == 42


def test_attaches_ipv6_by_id_with_reboot(api, run):
    v6 = ip(id=9, slug="2001:db8::10", address="2001:db8::10", gateway="2001:db8::1", prefix=64)
    api.add("GET", IPV6, listing(v6))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})
    api.add("POST", SERVERS + "42/attach-ipv6/", {"attached": True, "reboot_required": False, "rebooted": True})
    api.add("GET", IPV6 + "9/", dict(v6, attached=True, server_id=42))

    result = run(ip_action, ip_address="2001:DB8:0::10", server_id=42, reboot=True)

    assert result.changed
    assert api.requests("POST")[0][2] == {"ipv6": "2001:db8::10", "reboot": True}


def test_already_attached_to_target_is_unchanged(api, run):
    api.add("GET", IPV4, listing(attached()))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})

    result = run(ip_action, ip_address="192.0.2.10", server_id=42, server_ip="ignored")

    assert not result.failed, result.result
    assert not result.changed
    assert result["ip_result"] == {}
    assert result["ip"]["id"] == 7
    assert api.writes() == []


def test_attached_to_other_server_fails(api, run):
    api.add("GET", IPV4, listing(attached()))
    api.add("GET", SERVERS + "43/", {"id": 43, "hostname": "web2"})

    result = run(ip_action, ip_address="192.0.2.10", server_id=43)

    assert result.failed
    assert "web1" in result["msg"]
    assert api.writes() == []


def test_attach_check_mode_makes_no_writes(api, run):
    api.add("GET", IPV4, listing(ip()))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1"})

    result = run(ip_action, check_mode=True, ip_address="192.0.2.10", server_id=42)

    assert not result.failed
    assert result.changed
    assert api.writes() == []


def test_address_not_owned_fails(api, run):
    api.add("GET", IPV4, listing(ip()))

    result = run(ip_action, ip_address="198.51.100.5", server_id=42)

    assert result.failed
    assert "198.51.100.5" in result["msg"]


def test_present_requires_a_server(api, run):
    result = run(ip_action, ip_address="192.0.2.10")

    assert result.failed
    assert api.calls == []


def test_detaches_without_server(api, run):
    api.add("GET", IPV4, listing(attached()))
    api.add("POST", IPV4 + "7/detach/", {"detached": True})
    api.add("GET", IPV4 + "7/", ip())

    result = run(ip_action, state="absent", ip_address="192.0.2.10")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("POST", IPV4 + "7/detach/")]
    assert result["ip_result"] == {"detached": True}
    assert not result["ip"]["attached"]


def test_detach_check_mode_makes_no_writes(api, run):
    api.add("GET", IPV4, listing(attached()))

    result = run(ip_action, check_mode=True, state="absent", ip_address="192.0.2.10", server_hostname="web1")

    assert result.changed
    assert api.writes() == []


def test_detach_unattached_is_unchanged(api, run):
    api.add("GET", IPV4, listing(ip()))

    result = run(ip_action, state="absent", ip_address="192.0.2.10", server_id=42)

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_detach_from_other_server_is_unchanged(api, run):
    api.add("GET", IPV4, listing(attached()))

    result = run(ip_action, state="absent", ip_address="192.0.2.10", server_hostname="web2")

    assert not result.failed
    assert not result.changed
    assert api.writes() == []
