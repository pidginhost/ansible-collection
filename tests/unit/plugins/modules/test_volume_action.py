# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import volume_action

VOLUMES = "/api/cloud/volumes/"
SERVERS = "/api/cloud/servers/"


def vol(**kw):
    base = {"id": 7, "project": "", "alias": "data", "size": 10, "product": "fast-storage",
            "attached": False, "server": ""}
    base.update(kw)
    return base


def server(*volumes):
    return {"id": 42, "hostname": "web1", "status": "active", "volumes": list(volumes)}


def test_attaches_volume_to_server_by_hostname(api, run):
    api.add("GET", VOLUMES, [vol()])
    api.add("GET", SERVERS, {"count": 1, "next": None, "previous": None,
                             "results": [{"id": 42, "hostname": "web1"}]})
    api.add("GET", SERVERS + "42/", server())
    api.add("POST", VOLUMES + "7/attach/", {"attached": True})
    api.add("GET", VOLUMES + "7/", vol(attached=True, server="web1"))

    result = run(volume_action, volume_alias="data", server_hostname="web1")

    assert not result.failed, result.result
    assert result.changed
    assert result["action"]["server"] == "web1"
    assert api.writes() == [("POST", VOLUMES + "7/attach/", {"vm": 42})]


def test_attached_volume_is_unchanged(api, run):
    attached = vol(attached=True, server="web1")
    api.add("GET", VOLUMES, [attached])
    api.add("GET", SERVERS + "42/", server(attached))

    result = run(volume_action, volume_alias="data", server_id=42)

    assert not result.failed, result.result
    assert not result.changed
    assert result["action"] == attached
    assert api.writes() == []


def test_volume_attached_elsewhere_fails(api, run):
    api.add("GET", VOLUMES, [vol(attached=True, server="db1")])
    api.add("GET", SERVERS + "42/", server())

    result = run(volume_action, volume_alias="data", server_id=42)

    assert result.failed
    assert "db1" in result["msg"]
    assert api.writes() == []


def test_attach_check_mode_makes_no_writes(api, run):
    api.add("GET", VOLUMES, [vol()])
    api.add("GET", SERVERS + "42/", server())

    result = run(volume_action, check_mode=True, volume_alias="data", server_id=42)

    assert result.changed
    assert api.writes() == []


def test_detaches_volume(api, run):
    attached = vol(attached=True, server="web1")
    api.add("GET", VOLUMES, [attached])
    api.add("GET", SERVERS + "42/", server(attached))
    api.add("POST", VOLUMES + "7/detach/", {"detached": True})
    api.add("GET", VOLUMES + "7/", vol(server="web1"))

    result = run(volume_action, state="absent", volume_alias="data", server_id=42)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", VOLUMES + "7/detach/", {})]


def test_detach_from_other_server_is_unchanged(api, run):
    api.add("GET", VOLUMES, [vol(attached=True, server="db1")])
    api.add("GET", SERVERS + "42/", server())

    result = run(volume_action, state="absent", volume_alias="data", server_id=42)

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_detach_in_progress_is_unchanged(api, run):
    detaching = vol(attached=False, server="web1")
    api.add("GET", VOLUMES, [detaching])
    api.add("GET", SERVERS + "42/", server(detaching))

    result = run(volume_action, state="absent", volume_alias="data", server_id=42)

    assert not result.changed
    assert api.writes() == []


def test_missing_volume_fails(api, run):
    api.add("GET", VOLUMES, [])

    result = run(volume_action, volume_alias="data", server_id=42)

    assert result.failed
    assert "data" in result["msg"]
