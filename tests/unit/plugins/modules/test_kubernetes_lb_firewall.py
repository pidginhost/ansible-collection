# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_lb_firewall as module

CLUSTER = "/api/kubernetes/clusters/7/"
RULES = CLUSTER + "lb-firewall/"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def rule(rule_id, **kw):
    base = {"id": rule_id, "direction": "in", "action": "ACCEPT", "protocol": "tcp", "source": "", "sport": "",
            "destination": "", "dport": "443", "comment": "", "enabled": True, "position": 100}
    base.update(kw)
    return base


HTTPS = {"direction": "in", "action": "ACCEPT", "protocol": "tcp", "dport": "443"}


def setup(api, *rules):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("GET", RULES, page(*rules))


def test_creates_missing_rule(api, run):
    setup(api)
    api.add("POST", RULES, rule(1, comment="web"), status=201)
    api.add("GET", RULES, page(rule(1, comment="web")))

    result = run(module, cluster_id=7, rules=[dict(HTTPS, comment="web")])

    assert not result.failed, result.result
    assert result.changed
    assert result["rules"][0]["id"] == 1
    assert api.writes() == [("POST", RULES, {
        "direction": "in", "action": "ACCEPT", "protocol": "tcp", "dport": "443", "comment": "web",
        "enabled": True})]


def test_matching_rules_are_unchanged(api, run):
    setup(api, rule(1), rule(2, dport="22", source="203.0.113.0/24"))

    result = run(module, cluster_id=7, rules=[HTTPS])

    assert not result.failed, result.result
    assert not result.changed
    assert len(result["rules"]) == 2
    assert api.writes() == []


def test_changed_comment_enabled_and_position_are_patched(api, run):
    setup(api, rule(1))
    api.add("PATCH", RULES + "1/", rule(1, comment="web", enabled=False, position=5))
    api.add("GET", RULES, page(rule(1, comment="web", enabled=False, position=5)))

    result = run(module, cluster_id=7, rules=[dict(HTTPS, comment="web", enabled=False, position=5)])

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("PATCH", RULES + "1/", {"comment": "web", "enabled": False, "position": 5})]


def test_purge_deletes_unlisted_rules(api, run):
    setup(api, rule(1), rule(2, dport="22"))
    api.add("DELETE", RULES + "2/", None, status=204)
    api.add("GET", RULES, page(rule(1)))

    result = run(module, cluster_id=7, rules=[HTTPS], purge_rules=True)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("DELETE", RULES + "2/", None)]
    assert [r["id"] for r in result["rules"]] == [1]


def test_check_mode_makes_no_writes(api, run):
    setup(api, rule(2, dport="22"))

    result = run(module, check_mode=True, cluster_id=7, rules=[HTTPS], purge_rules=True)

    assert result.changed
    assert api.writes() == []


def test_port_without_protocol_fails(api, run):
    result = run(module, cluster_id=7, rules=[{"direction": "in", "action": "ACCEPT", "dport": "443"}])

    assert result.failed
    assert "protocol" in result["msg"]
    assert api.calls == []
