# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import dns_record

DOMAIN = "/api/domain/domain/example.com/"
QUERY = "?domain=12&source=internal"
RECORDS = "/api/freedns/dns/records/" + QUERY
ADD = "/api/freedns/dns/add-record/" + QUERY
DELETE = "/api/freedns/dns/delete-record/" + QUERY


def rec(line, address="192.0.2.10", name="www.example.com.", ttl=14400, **kw):
    base = {"Line": line, "name": name, "ttl": ttl, "type": "A", "address": address}
    base.update(kw)
    return base


APEX = rec(1, name="example.com.")
OTHER_TYPE = rec(2, type="AAAA", address="2001:db8::10")


def zone(*records):
    api_records = [APEX, OTHER_TYPE] + list(records)
    return sorted(api_records, key=lambda r: r["Line"])


def writes(api):
    return [(path, body) for method, path, body in api.writes()]


def test_adds_missing_record(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone())
    api.add("GET", RECORDS, zone(rec(5)))
    api.add("POST", ADD, {"message": "Record added successfully."}, status=201)

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10")

    assert not result.failed, result.result
    assert result.changed
    assert writes(api) == [(ADD, {"name": "www.example.com.", "ttl": 14400, "type": "A", "address": "192.0.2.10"})]
    assert result["record"] == rec(5)
    assert result["records"] == [rec(5)]


def test_identical_record_is_unchanged(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(5)))

    for name in ("www", "www.example.com", "WWW.example.com."):
        result = run(dns_record, domain="example.com", name=name, type="A", address="192.0.2.10")

        assert not result.failed, result.result
        assert not result.changed
        assert result["record"] == rec(5)
    assert api.writes() == []


def test_values_compare_as_normalized_strings(api, run):
    mx = {"Line": 7, "name": "example.com.", "ttl": 14400, "type": "MX", "preference": "0",
          "exchange": "Mail.example.com"}
    aaaa = rec(8, type="AAAA", address="2001:db8:0::1")
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(mx, aaaa))

    result = run(dns_record, domain="example.com", name="@", type="MX", preference=0, exchange="mail.example.com.")
    assert not result.changed
    assert result["record"] == mx

    result = run(dns_record, domain="example.com", name="www", type="AAAA", address="2001:DB8::1")
    assert not result.changed
    assert api.writes() == []


def test_changed_ttl_edits_record_in_place(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(5, ttl=300)))
    api.add("GET", RECORDS, zone(rec(5, ttl=3600)))
    api.add("POST", ADD, {"message": "Record saved successfully."})

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10", ttl=3600)

    assert result.changed
    assert writes(api) == [
        (ADD, {"name": "www.example.com.", "ttl": 3600, "type": "A", "address": "192.0.2.10", "line": 5})]
    assert result["record"] == rec(5, ttl=3600)


def test_caa_is_sent_as_type257_and_txt_as_unencoded(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone())
    api.add("POST", ADD, {"message": "Record added successfully."}, status=201)

    run(dns_record, domain="example.com", name="", type="CAA", flag=128, tag="issue", value="ca.external.example.com")
    run(dns_record, domain="example.com", name="_dmarc", type="TXT", txtdata="v=DMARC1; p=none")

    assert writes(api) == [
        (ADD, {"name": "example.com.", "ttl": 14400, "type": "TYPE257", "flag": 128, "tag": "issue",
               "value": "ca.external.example.com"}),
        (ADD, {"name": "_dmarc.example.com.", "ttl": 14400, "type": "TXT", "txtdata": "v=DMARC1; p=none",
               "unencoded": "1"}),
    ]


def test_add_check_mode_makes_no_writes(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone())

    result = run(dns_record, check_mode=True, domain="example.com", name="www", type="A", address="192.0.2.10")

    assert result.changed
    assert api.writes() == []


def test_present_requires_value_fields_before_any_call(api, run):
    result = run(dns_record, domain="example.com", name="@", type="MX", exchange="mail.example.com")

    assert result.failed
    assert "preference" in result["msg"]
    assert api.calls == []


def test_solo_keeps_one_record_and_deletes_from_the_highest_line_down(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3"), rec(5, ttl=300), rec(8, address="192.0.2.8"),
                                 rec(9, ttl=300)))
    api.add("GET", RECORDS, zone(rec(3)))
    api.add("POST", ADD, {"message": "Record saved successfully."})
    api.add("POST", DELETE, {"message": "Record removed successfully."})

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10", solo=True)

    assert result.changed
    assert writes(api) == [
        (DELETE, {"line": 9}),
        (DELETE, {"line": 8}),
        (ADD, {"name": "www.example.com.", "ttl": 14400, "type": "A", "address": "192.0.2.10", "line": 5}),
        (DELETE, {"line": 3}),
    ]
    assert result["records"] == [rec(3)]


def test_absent_without_values_deletes_every_record_from_the_highest_line_down(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3"), rec(9), rec(6, name="mail.example.com.")))
    api.add("GET", RECORDS, zone(rec(5, name="mail.example.com.")))
    api.add("POST", DELETE, {"message": "Record removed successfully."})

    result = run(dns_record, domain="example.com", name="www", type="A", state="absent")

    assert result.changed
    assert writes(api) == [(DELETE, {"line": 9}), (DELETE, {"line": 3})]
    assert result["record"] == {}
    assert result["records"] == []


def test_absent_with_values_deletes_only_matching_records(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3"), rec(9)))
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3")))
    api.add("POST", DELETE, {"message": "Record removed successfully."})

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10", state="absent")

    assert writes(api) == [(DELETE, {"line": 9})]
    assert result["records"] == [rec(3, address="192.0.2.3")]


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(9)))

    result = run(dns_record, check_mode=True, domain="example.com", name="www", type="A", state="absent")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_record_is_unchanged(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(9, address="192.0.2.9")))

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10", state="absent")

    assert not result.failed
    assert not result.changed
    assert result["records"] == [rec(9, address="192.0.2.9")]


def test_external_zone_uses_domain_name(api, run):
    query = "?domain=external.example.com&source=external"
    api.add("GET", "/api/freedns/dns/records/" + query, [rec(4, name="www.external.example.com.")])

    result = run(dns_record, domain="external.example.com", source="external", name="www", type="A", address="192.0.2.10")

    assert not result.changed


def test_api_error_on_add_fails(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone())
    api.add("POST", ADD, {"message": "Error saving the record."}, status=502)

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10")

    assert result.failed
    assert "Error saving the record" in result["msg"]


def test_internationalized_record_name_matches_ascii_form(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(4, name="xn--bcher-kva.example.com.")))

    for name in (u"b\u00fccher", u"b\u00fccher.example.com", u"b\u00fccher.example.com."):
        result = run(dns_record, domain="example.com", name=name, type="A", address="192.0.2.10")

        assert not result.failed, result.result
        assert not result.changed
    assert api.writes() == []


def test_internal_domain_lookup_does_not_leak_contact_errors(api, run):
    api.add("GET", DOMAIN, {"contacts": {"Registrant": {"email": "private-owner@example.com"}}}, status=500)

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10")

    assert result.failed
    assert "private-owner" not in str(result.result)
    assert "response" not in result.result


def test_solo_replaces_last_record_before_deleting_others(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3"), rec(8, address="192.0.2.8")))
    api.add("GET", RECORDS, zone(rec(7)))
    api.add("POST", ADD, {"message": "Record saved successfully."})
    api.add("POST", DELETE, {"message": "Record removed successfully."})

    result = run(dns_record, domain="example.com", name="www", type="A", address="192.0.2.10", solo=True)

    assert not result.failed, result.result
    assert result.changed
    assert writes(api) == [
        (ADD, {"name": "www.example.com.", "ttl": 14400, "type": "A", "address": "192.0.2.10", "line": 8}),
        (DELETE, {"line": 3}),
    ]
    assert result["record"] == rec(7)


def test_solo_rejected_replacement_does_not_delete_existing_records(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3"), rec(8, address="192.0.2.8")))
    api.add("POST", ADD, {"message": "Invalid address."}, status=400)

    result = run(dns_record, domain="example.com", name="www", type="A", address="invalid", solo=True)

    assert result.failed
    assert not result.changed
    assert api.requests("POST", DELETE) == []


def test_solo_replacement_check_mode_does_not_write(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, zone(rec(3, address="192.0.2.3")))

    result = run(dns_record, check_mode=True, domain="example.com", name="www", type="A",
                 address="192.0.2.10", solo=True)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == []
