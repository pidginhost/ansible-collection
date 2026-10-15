# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import domain_nameservers

DOMAIN = "/api/domain/domain/example.com/"
NAMESERVERS = DOMAIN + "nameservers/"


def detail(nameservers="ns1.example.net,ns2.example.net"):
    return {"id": 12, "domain": "example", "tld": {"tld": "com"}, "idna_name": "example.com",
            "nameservers": nameservers, "contacts": {"Registrant": {"email": "owner@example.com"}}}


def test_sets_different_nameservers(api, run):
    api.add("GET", DOMAIN, detail())
    api.add("POST", NAMESERVERS, {"message": "Nameservers updated successfully."})

    result = run(domain_nameservers, domain="example.com", nameservers=["ns3.example.net", "ns4.example.net."])

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", NAMESERVERS, {"nameservers": ["ns3.example.net", "ns4.example.net"]})]
    assert result["domain"]["nameservers"] == ["ns3.example.net", "ns4.example.net"]
    assert "contacts" not in result["domain"]


def test_same_nameservers_in_any_order_and_case_are_unchanged(api, run):
    api.add("GET", DOMAIN, detail())

    result = run(domain_nameservers, domain="Example.com.", nameservers=["NS2.example.net.", "ns1.example.net"])

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert result["domain"]["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert "contacts" not in result["domain"]


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", DOMAIN, detail())

    result = run(domain_nameservers, check_mode=True, domain="example.com",
                 nameservers=["ns3.example.net", "ns4.example.net"])

    assert result.changed
    assert api.writes() == []
    assert "contacts" not in result["domain"]


def test_nameserver_count_is_checked_before_any_call(api, run):
    for nameservers in (["ns1.example.net"], ["ns%d.example.net" % i for i in range(6)]):
        result = run(domain_nameservers, domain="example.com", nameservers=nameservers)

        assert result.failed
        assert "2 to 5" in result["msg"]
    assert api.calls == []


def test_unknown_domain_fails(api, run):
    api.add("GET", DOMAIN, {"detail": "Not found."}, status=404)

    result = run(domain_nameservers, domain="example.com", nameservers=["ns1.example.net", "ns2.example.net"])

    assert result.failed
    assert "not found" in result["msg"]
