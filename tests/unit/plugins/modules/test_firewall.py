# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import firewall

SETS = "/api/cloud/firewall-rules-set/"
RULES = SETS + "5/rules/"


def rule(rule_id, **kw):
    base = {"id": rule_id, "direction": "in", "action": "ACCEPT", "protocol": "tcp", "source": "", "sport": "",
            "destination": "", "dport": "22", "enabled": True, "position": 0, "has_error": False,
            "error_message": ""}
    base.update(kw)
    return base


def rules_set(*rules, **kw):
    base = {"id": 5, "name": "web", "status": "validated", "read_only": False, "rules": list(rules)}
    base.update(kw)
    return base


SSH = {"direction": "in", "action": "ACCEPT", "protocol": "tcp", "dport": 22}


def test_creates_missing_set_and_rules(api, run):
    api.add("GET", SETS, [rules_set(name="other")])
    api.add("POST", SETS, rules_set(), status=201)
    api.add("POST", RULES, rule(1), status=201)
    api.add("GET", SETS + "5/", rules_set(rule(1)))

    result = run(firewall, name="web", rules=[SSH])

    assert not result.failed, result.result
    assert result.changed
    assert api.requests("POST", SETS)[0][2] == {"name": "web"}
    assert api.requests("POST", RULES)[0][2] == {
        "direction": "in", "action": "ACCEPT", "protocol": "tcp", "dport": "22", "enabled": True}
    assert result["firewall"]["rules"][0]["id"] == 1


def test_matching_rules_are_unchanged(api, run):
    api.add("GET", SETS, [rules_set(rule(1), rule(2, direction="out", protocol="", dport=""))])

    result = run(firewall, name="web", rules=[SSH, {"direction": "out", "action": "ACCEPT", "source": None}])

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert result["firewall"]["id"] == 5


def test_changed_enabled_and_position_are_patched(api, run):
    api.add("GET", SETS, [rules_set(rule(1, enabled=False))])
    api.add("PATCH", RULES + "1/", rule(1, position=3))
    api.add("GET", SETS + "5/", rules_set(rule(1, position=3)))

    result = run(firewall, name="web", rules=[dict(SSH, position=3)])

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("PATCH", RULES + "1/")]
    assert api.writes()[0][2] == {"enabled": True, "position": 3}


def test_purge_deletes_extra_and_duplicate_rules(api, run):
    api.add("GET", SETS, [rules_set(rule(1), rule(2), rule(3, dport="80"))])
    api.add("DELETE", RULES + "2/", status=204)
    api.add("DELETE", RULES + "3/", status=204)
    api.add("GET", SETS + "5/", rules_set(rule(1)))

    result = run(firewall, name="web", rules=[SSH], purge_rules=True)

    assert result.changed
    assert sorted(c[1] for c in api.writes()) == [RULES + "2/", RULES + "3/"]


def test_without_purge_extra_rules_stay(api, run):
    api.add("GET", SETS, [rules_set(rule(1), rule(3, dport="80"))])

    result = run(firewall, name="web", rules=[SSH])

    assert not result.changed
    assert api.writes() == []


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", SETS, [rules_set(rule(1, dport="80"))])

    result = run(firewall, check_mode=True, name="web", rules=[SSH], purge_rules=True)

    assert result.changed
    assert api.writes() == []


def test_check_mode_missing_set_makes_no_writes(api, run):
    api.add("GET", SETS, [])

    result = run(firewall, check_mode=True, name="web", rules=[SSH])

    assert result.changed
    assert result["firewall"]["name"] == "web"
    assert api.writes() == []


def test_legacy_flat_options_are_idempotent(api, run):
    api.add("GET", SETS, [rules_set(rule(1))])

    result = run(firewall, rules_set_name="web", create_rules_set=False, direction="in", action="ACCEPT",
                 protocol="tcp", dport="22", enabled=True, position=0)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_legacy_flat_options_add_one_rule_next_to_rules(api, run):
    api.add("GET", SETS, [rules_set(rule(1))])
    api.add("POST", RULES, rule(2, dport="443"), status=201)
    api.add("GET", SETS + "5/", rules_set(rule(1), rule(2, dport="443")))

    result = run(firewall, rules_set_name="web", rules=[SSH], direction="in", action="ACCEPT",
                 protocol="tcp", dport="443")

    assert result.changed
    assert api.requests("POST", RULES)[0][2] == {
        "direction": "in", "action": "ACCEPT", "protocol": "tcp", "dport": "443", "enabled": True}


def test_legacy_create_rules_set_only_creates_once(api, run):
    api.add("GET", SETS, [rules_set()])

    result = run(firewall, rules_set_name="web", create_rules_set=True)

    assert not result.changed
    assert api.writes() == []


def test_legacy_direction_requires_action(api, run):
    result = run(firewall, name="web", direction="in")

    assert result.failed
    assert api.calls == []


def test_port_without_protocol_fails_before_any_call(api, run):
    result = run(firewall, name="web", rules=[{"direction": "in", "action": "ACCEPT", "dport": "22"}])

    assert result.failed
    assert "protocol" in result["msg"]
    assert api.calls == []


def test_absent_deletes_set(api, run):
    api.add("GET", SETS, [rules_set(rule(1))])
    api.add("DELETE", SETS + "5/", status=204)

    result = run(firewall, state="absent", name="web")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", SETS + "5/")]
    assert result["firewall"]["id"] == 5


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", SETS, [rules_set()])

    result = run(firewall, check_mode=True, state="absent", name="web")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_set_is_unchanged(api, run):
    api.add("GET", SETS, [])

    result = run(firewall, state="absent", rules_set_name="web")

    assert not result.failed
    assert not result.changed
    assert result["firewall"] == {}


def test_api_error_fails(api, run):
    api.add("GET", SETS, [])
    api.add("POST", SETS, {"name": ["This name is already used"]}, status=400)

    result = run(firewall, name="web")

    assert result.failed
    assert result["status_code"] == 400
