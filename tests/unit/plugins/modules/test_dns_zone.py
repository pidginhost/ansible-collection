# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import dns_zone

ZONES = "/api/freedns/dns/"
ACTIVATE = ZONES + "activate/"
DEACTIVATE = ZONES + "deactivate/"
DOMAIN = "/api/domain/domain/example.com/"
ZONE = {"domain": "example.com", "active": True, "source": "internal"}


def test_activates_internal_zone_by_domain_id(api, run):
    api.add("GET", ZONES, [])
    api.add("GET", DOMAIN, {"id": 12, "domain": "example", "idna_name": "example.com"})
    api.add("POST", ACTIVATE, {"message": "ok", "domain": "example.com", "source": "internal"})

    result = run(dns_zone, domain="example.com", ip="192.0.2.10")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", ACTIVATE, {"domain": 12, "source": "internal", "ip": "192.0.2.10"})]
    assert result["zone"] == ZONE


def test_activates_external_zone_by_name(api, run):
    api.add("GET", ZONES, [])
    api.add("POST", ACTIVATE, {"message": "ok", "domain": "example.net", "source": "external"})

    result = run(dns_zone, domain="example.net.", source="external", ip="192.0.2.10")

    assert result.changed
    assert api.writes() == [("POST", ACTIVATE, {"domain": "example.net", "source": "external", "ip": "192.0.2.10"})]


def test_active_zone_is_unchanged(api, run):
    api.add("GET", ZONES, [ZONE])

    result = run(dns_zone, domain="Example.com.", ip="192.0.2.10")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert result["zone"] == ZONE


def test_listed_idn_zone_matches_ascii_name(api, run):
    zone = {"domain": u"b\u00fccher.example.com", "active": True, "source": "internal"}
    api.add("GET", ZONES, [zone])

    result = run(dns_zone, domain="xn--bcher-kva.example.com", ip="192.0.2.10")

    assert not result.changed
    assert result["zone"] == zone


def test_activation_check_mode_makes_no_writes(api, run):
    api.add("GET", ZONES, [])
    api.add("GET", DOMAIN, {"id": 12})

    result = run(dns_zone, check_mode=True, domain="example.com", ip="192.0.2.10")

    assert result.changed
    assert api.writes() == []


def test_activation_requires_ip(api, run):
    api.add("GET", ZONES, [])

    result = run(dns_zone, domain="example.com")

    assert result.failed
    assert "ip" in result["msg"]
    assert api.writes() == []


def test_unknown_internal_domain_fails(api, run):
    api.add("GET", ZONES, [])
    api.add("GET", DOMAIN, {"detail": "Not found."}, status=404)

    result = run(dns_zone, domain="example.com", ip="192.0.2.10")

    assert result.failed
    assert "not found" in result["msg"]
    assert api.writes() == []


def test_absent_deactivates_listed_zone(api, run):
    api.add("GET", ZONES, [ZONE])
    api.add("GET", DOMAIN, {"id": 12})
    api.add("POST", DEACTIVATE, {"message": "ok"})

    result = run(dns_zone, domain="example.com", state="absent")

    assert result.changed
    assert api.writes() == [("POST", DEACTIVATE, {"domain": 12, "source": "internal"})]
    assert result["zone"] == ZONE


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", ZONES, [ZONE])
    api.add("GET", DOMAIN, {"id": 12})

    result = run(dns_zone, check_mode=True, domain="example.com", state="absent")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_zone_is_unchanged(api, run):
    api.add("GET", ZONES, [dict(ZONE, source="external")])

    result = run(dns_zone, domain="example.com", state="absent")

    assert not result.failed
    assert not result.changed
    assert result["zone"] == {}
