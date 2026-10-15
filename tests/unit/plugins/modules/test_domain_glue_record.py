# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import domain_glue_record

GLUE = "/api/domain/domain/example.com/dns/"
NS1 = {"name": "ns1", "ip": "192.0.2.53", "ip2": None}


def listing(*records):
    return {"count": len(records), "next": None, "previous": None, "results": list(records)}


def test_creates_missing_glue_record(api, run):
    api.add("GET", GLUE, listing())
    api.add("POST", GLUE, NS1)

    result = run(domain_glue_record, domain="example.com", name="ns1", ip="192.0.2.53")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", GLUE, {"name": "ns1", "ip": "192.0.2.53"})]
    assert result["glue_record"] == NS1


def test_matching_glue_record_is_unchanged(api, run):
    record = {"name": "ns1", "ip": "192.0.2.53", "ip2": "2001:db8::53"}
    api.add("GET", GLUE, listing(record))

    result = run(domain_glue_record, domain="example.com", name="NS1", ip="192.0.2.53", ip2="2001:DB8:0::53")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert result["glue_record"] == record


def test_changed_address_is_upserted(api, run):
    api.add("GET", GLUE, listing(dict(NS1, ip2="198.51.100.53")))
    api.add("POST", GLUE, NS1)

    result = run(domain_glue_record, domain="example.com", name="ns1", ip="192.0.2.53")

    assert result.changed
    assert api.writes() == [("POST", GLUE, {"name": "ns1", "ip": "192.0.2.53"})]


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", GLUE, listing())

    result = run(domain_glue_record, check_mode=True, domain="example.com", name="ns1", ip="192.0.2.53")

    assert result.changed
    assert api.writes() == []


def test_absent_deletes_glue_record(api, run):
    api.add("GET", GLUE, listing(NS1))
    api.add("DELETE", GLUE + "ns1/", status=204)

    result = run(domain_glue_record, domain="example.com", name="ns1", state="absent")

    assert result.changed
    assert api.writes() == [("DELETE", GLUE + "ns1/", None)]
    assert result["glue_record"] == NS1


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", GLUE, listing(NS1))

    result = run(domain_glue_record, check_mode=True, domain="example.com", name="ns1", state="absent")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_glue_record_is_unchanged(api, run):
    api.add("GET", GLUE, listing(dict(NS1, name="ns2")))

    result = run(domain_glue_record, domain="example.com", name="ns1", state="absent")

    assert not result.failed
    assert not result.changed
    assert result["glue_record"] == {}


def test_registrar_error_fails(api, run):
    api.add("GET", GLUE, listing())
    api.add("POST", GLUE, ["API ERROR: registry refused the host"], status=400)

    result = run(domain_glue_record, domain="example.com", name="ns1", ip="192.0.2.53")

    assert result.failed
    assert "registry refused" in result["msg"]
