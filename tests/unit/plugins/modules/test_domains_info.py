# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import domains_info

DOMAINS = "/api/domain/domain/"


def domain(label, tld="com"):
    return {"id": len(label), "domain": label, "tld": {"tld": tld}, "idna_name": "%s.%s" % (label, tld),
            "nameservers": "ns1.external.example.com,ns2.external.example.com", "contacts": {"Registrant": {"email": "x@example.com"}}}


def page(next_page, *items):
    return {"count": 2, "next": next_page, "previous": None, "results": list(items)}


def without_contacts(item):
    return dict((k, v) for k, v in item.items() if k != "contacts")


def test_lists_every_page_without_contacts(api, run):
    api.add("GET", DOMAINS + "?status_group=current", page("https://example.com/next", domain("example")))
    api.add("GET", DOMAINS + "?status_group=current&page=2", page(None, domain("external.example")))

    result = run(domains_info, check_mode=True, status_group="current")

    assert not result.failed, result.result
    assert not result.changed
    assert result["domains"] == [without_contacts(domain("example")), without_contacts(domain("external.example"))]


def test_filters_by_domain(api, run):
    api.add("GET", DOMAINS, page(None, domain("example"), domain("external.example")))

    result = run(domains_info, domain="External.example.com.")

    assert result["domains"] == [without_contacts(domain("external.example"))]


def test_api_error_fails(api, run):
    api.add("GET", DOMAINS, {"detail": "Invalid token."}, status=401)

    result = run(domains_info)

    assert result.failed


def test_error_response_never_returns_contact_data(api, run):
    api.add("GET", DOMAINS, {"contacts": {"Registrant": {"email": "private-owner@example.com"}}}, status=500)

    result = run(domains_info)

    assert result.failed
    assert result["status_code"] == 500
    assert "private-owner" not in str(result.result)
    assert "response" not in result.result
