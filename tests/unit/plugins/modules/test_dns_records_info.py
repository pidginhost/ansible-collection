# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import dns_records_info

DOMAIN = "/api/domain/domain/example.com/"
RECORDS = "/api/freedns/dns/records/?domain=12&source=internal"
APEX_A = {"Line": 13, "name": "example.com.", "ttl": 14400, "type": "A", "address": "192.0.2.10"}
WWW_A = {"Line": 14, "name": "www.example.com.", "ttl": 14400, "type": "A", "address": "192.0.2.10"}
WWW_CAA = {"Line": 15, "name": "www.example.com.", "ttl": 14400, "type": "TYPE257", "flag": 0, "tag": "issue",
           "value": "ca.external.example.com"}


def test_lists_internal_zone_records_by_domain_id(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, [APEX_A, WWW_A, WWW_CAA])

    result = run(dns_records_info, check_mode=True, domain="example.com")

    assert not result.failed, result.result
    assert not result.changed
    assert result["records"] == [APEX_A, WWW_A, WWW_CAA]


def test_filters_by_name_and_type(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, [APEX_A, WWW_A, WWW_CAA])

    assert run(dns_records_info, domain="example.com", name="www", type="CAA")["records"] == [WWW_CAA]
    assert run(dns_records_info, domain="example.com", name="@")["records"] == [APEX_A]
    assert run(dns_records_info, domain="example.com", type="A")["records"] == [APEX_A, WWW_A]


def test_external_zone_uses_domain_name(api, run):
    api.add("GET", "/api/freedns/dns/records/?domain=external.example.com&source=external", [])

    result = run(dns_records_info, domain="external.example.com", source="external")

    assert not result.failed, result.result
    assert result["records"] == []


def test_inactive_zone_fails(api, run):
    api.add("GET", DOMAIN, {"id": 12})
    api.add("GET", RECORDS, {"message": "Free DNS is not activated for this domain."}, status=400)

    result = run(dns_records_info, domain="example.com")

    assert result.failed
    assert "not activated" in result["msg"]
