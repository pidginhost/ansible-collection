# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server_action_power

SERVERS = "/api/cloud/servers/"
POWER = SERVERS + "42/power-management/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def with_server(api):
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1", "status": "active"})


def test_start_powers_on_and_waits_until_running(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    with_server(api)
    api.add("GET", POWER, {"status": "stopped"})
    api.add("GET", POWER, {"status": "stopped"})
    api.add("GET", POWER, {"status": "running"})
    api.add("POST", POWER, {"status": "stopped"})

    result = run(server_action_power, server_hostname="web1", state="start")

    assert not result.failed, result.result
    assert result.changed
    assert result["action"] == {"status": "running"}
    assert api.writes() == [("POST", POWER, {"action": "start"})]


def test_start_running_server_is_unchanged(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})

    result = run(server_action_power, server_id=42)

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_stop_check_mode_makes_no_writes(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})

    result = run(server_action_power, check_mode=True, server_id=42, state="stop")

    assert result.changed
    assert api.writes() == []


def test_reboot_stopped_server_is_unchanged(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "stopped"})

    result = run(server_action_power, server_id=42, state="reboot")

    assert not result.changed
    assert api.writes() == []


def test_reboot_running_server_is_changed(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})
    api.add("POST", POWER, {"status": "running"})

    result = run(server_action_power, server_id=42, state="reboot")

    assert result.changed
    assert api.writes() == [("POST", POWER, {"action": "reboot"})]


def test_shutdown_without_force_does_not_need_force_option(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})
    api.add("GET", POWER, {"status": "stopped"})
    api.add("POST", POWER, {"status": "running"})

    result = run(server_action_power, server_id=42, state="shutdown")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", POWER, {"action": "shutdown"})]


def test_shutdown_timeout_forces_power_off(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})
    api.add("POST", POWER, {"status": "running"})
    api.add("GET", POWER, {"status": "running"})
    api.add("GET", POWER, {"status": "stopped"})

    result = run(server_action_power, server_id=42, state="shutdown", force_power_off=True, timeout=0)

    assert not result.failed, result.result
    assert result.changed
    assert [c[2] for c in api.writes()] == [{"action": "shutdown"}, {"action": "stop"}]


def test_shutdown_timeout_without_force_fails(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})
    api.add("POST", POWER, {"status": "running"})

    result = run(server_action_power, server_id=42, state="shutdown", timeout=0)

    assert result.failed
    assert result.changed
    assert [c[2] for c in api.writes()] == [{"action": "shutdown"}]


def test_no_wait_returns_after_post(api, run):
    with_server(api)
    api.add("GET", POWER, {"status": "running"})
    api.add("POST", POWER, {"status": "running"})

    result = run(server_action_power, server_id=42, state="stop", wait=False)

    assert result.changed
    assert result["action"] == {"status": "running"}
    assert len(api.requests("GET", POWER)) == 1


def test_unknown_server_fails(api, run):
    api.add("GET", SERVERS + "9/", status=404)

    result = run(server_action_power, server_id=9)

    assert result.failed
    assert api.writes() == []
