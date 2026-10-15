# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server_snapshot

SERVERS = "/api/cloud/servers/"
SERVER = SERVERS + "42/"
SNAPS = SERVER + "snapshots/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def snap(name="before-upgrade", state=""):
    return {"name": name, "description": "", "state": state, "created_at": None,
            "includes_memory": False, "is_current": False}


def with_server(api, status="active"):
    api.add("GET", SERVER, {"id": 42, "hostname": "web1", "status": status})


def test_present_creates_and_waits_until_ready(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    with_server(api)
    api.add("GET", SNAPS, [])
    api.add("GET", SNAPS, [snap(state="prepare")])
    api.add("GET", SNAPS, [snap(), snap("older")])
    api.add("POST", SNAPS, {"queued": True}, status=202)

    result = run(server_snapshot, server_hostname="web1", name="before-upgrade", description="pre",
                 include_memory=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["snapshot"] == snap()
    assert api.writes() == [("POST", SNAPS, {"name": "before-upgrade", "description": "pre",
                                             "include_memory": True})]


def test_present_existing_snapshot_is_unchanged(api, run):
    with_server(api)
    api.add("GET", SNAPS, [snap()])

    result = run(server_snapshot, server_id=42, name="before-upgrade")

    assert not result.changed
    assert result["snapshot"] == snap()
    assert api.writes() == []


def test_present_check_mode_makes_no_writes(api, run):
    with_server(api)
    api.add("GET", SNAPS, [])

    result = run(server_snapshot, check_mode=True, server_id=42, name="before-upgrade")

    assert result.changed
    assert api.writes() == []


def test_present_without_wait(api, run):
    with_server(api)
    api.add("GET", SNAPS, [])
    api.add("POST", SNAPS, {"queued": True}, status=202)

    result = run(server_snapshot, server_id=42, name="before-upgrade", wait=False)

    assert result.changed
    assert result["snapshot"] == {"name": "before-upgrade"}
    assert len(api.requests("GET", SNAPS)) == 1


def test_present_timeout_fails(api, run):
    with_server(api)
    api.add("GET", SNAPS, [])
    api.add("POST", SNAPS, {"queued": True}, status=202)

    result = run(server_snapshot, server_id=42, name="before-upgrade", timeout=0)

    assert result.failed
    assert result.changed


def test_absent_deletes_and_waits_until_gone(api, run):
    with_server(api)
    api.add("GET", SNAPS, [snap()])
    api.add("GET", SNAPS, [snap(state="delete")])
    api.add("GET", SNAPS, [])
    api.add("DELETE", SNAPS + "before-upgrade/", {"queued": True}, status=202)

    result = run(server_snapshot, server_id=42, name="before-upgrade", state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert result["snapshot"] == {}
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", SNAPS + "before-upgrade/")]


def test_absent_missing_snapshot_is_unchanged(api, run):
    with_server(api)
    api.add("GET", SNAPS, [snap("other")])

    result = run(server_snapshot, server_id=42, name="before-upgrade", state="absent")

    assert not result.changed
    assert result["snapshot"] == {}
    assert api.writes() == []


def test_absent_delete_timeout_fails(api, run):
    with_server(api)
    api.add("GET", SNAPS, [snap()])
    api.add("DELETE", SNAPS + "before-upgrade/", {"queued": True}, status=202)

    result = run(server_snapshot, server_id=42, name="before-upgrade", state="absent", timeout=0)

    assert result.failed
    assert result.changed


def test_rollback_waits_until_server_active(api, run):
    with_server(api)
    with_server(api, status="upgrading")
    with_server(api)
    api.add("GET", SNAPS, [snap()])
    api.add("POST", SNAPS + "before-upgrade/rollback/", {"queued": True}, status=202)

    result = run(server_snapshot, server_id=42, name="before-upgrade", state="rollback")

    assert not result.failed, result.result
    assert result.changed
    assert result["snapshot"] == snap()
    assert [(c[0], c[1]) for c in api.writes()] == [("POST", SNAPS + "before-upgrade/rollback/")]
    assert len(api.requests("GET", SERVER)) == 3


def test_rollback_check_mode_makes_no_writes(api, run):
    with_server(api)
    api.add("GET", SNAPS, [snap()])

    result = run(server_snapshot, check_mode=True, server_id=42, name="before-upgrade", state="rollback")

    assert result.changed
    assert api.writes() == []


def test_rollback_missing_snapshot_fails(api, run):
    with_server(api)
    api.add("GET", SNAPS, [])

    result = run(server_snapshot, server_id=42, name="before-upgrade", state="rollback")

    assert result.failed
    assert api.writes() == []
