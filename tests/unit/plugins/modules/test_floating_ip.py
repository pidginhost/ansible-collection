# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import floating_ip

SERVERS = "/api/cloud/servers/"
FIP4 = "/api/cloud/floating-ipv4/"
FIP6 = "/api/cloud/floating-ipv6/"


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def fip(**kw):
    base = {"id": 3, "address": "203.0.113.5", "gateway": "203.0.113.1", "prefix": 24, "reverse_dns": "",
            "label": "vip", "authorized_vm_count": 0, "created_at": "2026-01-01T00:00:00Z"}
    base.update(kw)
    return base


def auths(*server_ids):
    return listing(*[{"id": i, "server_id": s, "server_hostname": "web%d" % s} for i, s in enumerate(server_ids)])


def test_creates_by_label_with_reverse_dns_and_authorizations(api, run):
    api.add("GET", FIP4, listing())
    api.add("POST", FIP4, fip(), status=201)
    api.add("POST", FIP4 + "3/rdns/", {"reverse_dns": "vip.example.com"})
    api.add("GET", FIP4 + "3/authorizations/", auths())
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}, {"id": 43, "hostname": "web2"}))
    api.add("POST", FIP4 + "3/authorize/", {"authorized": True})
    api.add("GET", FIP4 + "3/", fip(reverse_dns="vip.example.com", authorized_vm_count=2))

    result = run(floating_ip, label="vip", reverse_dns="vip.example.com", authorized_servers=["web1", "43"])

    assert not result.failed, result.result
    assert result.changed
    assert api.requests("POST", FIP4)[0][2] == {"label": "vip"}
    assert api.requests("POST", FIP4 + "3/rdns/")[0][2] == {"reverse_dns": "vip.example.com"}
    assert sorted(c[2]["server_id"] for c in api.requests("POST", FIP4 + "3/authorize/")) == [42, 43]
    assert result["floating_ip"]["authorized_vm_count"] == 2
    assert result["floating_ip"]["authorized_servers"] == [42, 43]


def test_existing_in_sync_is_unchanged(api, run):
    api.add("GET", FIP4, listing(fip(reverse_dns="vip.example.com")))
    api.add("GET", FIP4 + "3/authorizations/", auths(42))

    result = run(floating_ip, label="vip", reverse_dns="vip.example.com", authorized_servers=["42"])

    assert not result.failed, result.result
    assert not result.changed
    assert result["floating_ip"]["authorized_servers"] == [42]
    assert api.writes() == []


def test_authorizations_become_the_exact_set(api, run):
    api.add("GET", FIP4 + "3/", fip(authorized_vm_count=2))
    api.add("GET", FIP4 + "3/authorizations/", auths(42, 43))
    api.add("POST", FIP4 + "3/authorize/", {"authorized": True})
    api.add("POST", FIP4 + "3/unauthorize/", {"unauthorized": True})

    result = run(floating_ip, floating_ip_id=3, authorized_servers=["43", "44"])

    assert result.changed
    assert api.writes() == [
        ("POST", FIP4 + "3/authorize/", {"server_id": 44}),
        ("POST", FIP4 + "3/unauthorize/", {"server_id": 42}),
    ]
    assert result["floating_ip"]["authorized_servers"] == [43, 44]


def test_create_check_mode_makes_no_writes(api, run):
    api.add("GET", FIP4, listing())

    result = run(floating_ip, check_mode=True, label="vip", reverse_dns="vip.example.com", authorized_servers=["42"])

    assert result.changed
    assert api.writes() == []


def test_change_check_mode_makes_no_writes(api, run):
    api.add("GET", FIP4, listing(fip()))
    api.add("GET", FIP4 + "3/authorizations/", auths(42))

    result = run(floating_ip, check_mode=True, label="vip", reverse_dns="vip.example.com", authorized_servers=[])

    assert result.changed
    assert result["floating_ip"]["authorized_servers"] == []
    assert api.writes() == []


def test_absent_deletes_ipv6_by_address(api, run):
    v6 = fip(id=8, address="2001:db8::5", label="")
    api.add("GET", FIP6, listing(v6))
    api.add("DELETE", FIP6 + "8/", status=204)

    result = run(floating_ip, state="absent", address="2001:DB8::5")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", FIP6 + "8/")]
    assert result["floating_ip"]["id"] == 8


def test_absent_missing_is_unchanged(api, run):
    api.add("GET", FIP4, listing())

    result = run(floating_ip, state="absent", label="vip")

    assert not result.failed
    assert not result.changed
    assert result["floating_ip"] == {}


def test_unknown_id_fails(api, run):
    api.add("GET", FIP4 + "9/", status=404)

    result = run(floating_ip, floating_ip_id=9, label="vip")

    assert result.failed
    assert api.writes() == []


def test_duplicate_label_fails(api, run):
    api.add("GET", FIP4, listing(fip(), fip(id=4)))

    result = run(floating_ip, label="vip")

    assert result.failed
    assert api.writes() == []


def test_unknown_server_hostname_fails(api, run):
    api.add("GET", FIP4, listing(fip()))
    api.add("GET", FIP4 + "3/authorizations/", auths())
    api.add("GET", SERVERS, listing())

    result = run(floating_ip, label="vip", authorized_servers=["web9"])

    assert result.failed
    assert "web9" in result["msg"]
    assert api.writes() == []
