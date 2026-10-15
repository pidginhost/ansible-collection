# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import firewall_action

SERVERS = "/api/cloud/servers/"
IFACE = SERVERS + "42/public-interface/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def interface(**kw):
    base = {"interface": "net0", "ipv4": "192.0.2.10", "ipv6": "", "fw_rules_set": None,
            "fw_policy_in": "ACCEPT", "fw_policy_out": "ACCEPT"}
    base.update(kw)
    return base


def by_hostname(api):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1.example.com"}))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1.example.com", "status": "active"})


def test_applies_rules_set_and_keeps_other_values(api, run):
    by_hostname(api)
    api.add("GET", IFACE, interface())
    api.add("POST", IFACE, interface(fw_rules_set="web"))

    result = run(firewall_action, server_hostname="web1.example.com", rules_set_name="web")

    assert not result.failed, result.result
    assert result.changed
    assert api.requests("POST")[0][2] == {"fw_rules_set": "web", "fw_policy_in": "ACCEPT", "fw_policy_out": "ACCEPT"}
    assert result["firewall"]["fw_rules_set"] == "web"


def test_changes_policy_by_server_id(api, run):
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1.example.com"})
    api.add("GET", IFACE, interface(fw_rules_set="web"))
    api.add("POST", IFACE, interface(fw_rules_set="web", fw_policy_in="DROP"))

    result = run(firewall_action, server_id=42, policy_in="DROP")

    assert result.changed
    assert api.requests("POST")[0][2] == {"fw_rules_set": "web", "fw_policy_in": "DROP", "fw_policy_out": "ACCEPT"}


def test_matching_values_are_unchanged(api, run):
    by_hostname(api)
    api.add("GET", IFACE, interface(fw_rules_set="web", fw_policy_in="DROP"))

    result = run(firewall_action, state="present", server_hostname="web1.example.com", rules_set_name="web",
                 policy_in="DROP", policy_out="ACCEPT")

    assert not result.changed
    assert api.writes() == []
    assert result["firewall"]["fw_rules_set"] == "web"


def test_check_mode_makes_no_writes(api, run):
    by_hostname(api)
    api.add("GET", IFACE, interface())

    result = run(firewall_action, check_mode=True, server_hostname="web1.example.com", policy_in="DROP")

    assert result.changed
    assert result["firewall"]["fw_policy_in"] == "DROP"
    assert api.writes() == []


def test_missing_server_fails(api, run):
    api.add("GET", SERVERS, listing())

    result = run(firewall_action, server_hostname="web1.example.com", rules_set_name="web")

    assert result.failed
    assert api.writes() == []


def test_requires_a_server(api, run):
    result = run(firewall_action, rules_set_name="web")

    assert result.failed
    assert api.calls == []


def test_locked_firewall_fails_instead_of_reporting_a_change(api, run):
    # Free tier servers keep the platform rules set whatever the request says.
    by_hostname(api)
    api.add("GET", IFACE, interface(fw_rules_set="free tier fw"))
    api.add("POST", IFACE, interface(fw_rules_set="free tier fw"))

    result = run(firewall_action, server_hostname="web1.example.com", rules_set_name="web")

    assert result.failed
    assert not result.changed
    assert "free tier fw" in result["msg"]
