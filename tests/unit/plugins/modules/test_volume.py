# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import volume

VOLUMES = "/api/cloud/volumes/"
SERVERS = "/api/cloud/servers/"


def vol(**kw):
    base = {"id": 7, "project": "", "alias": "data", "size": 10, "product": "fast-storage",
            "attached": False, "server": ""}
    base.update(kw)
    return base


def listing(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def test_creates_volume_on_server_found_by_hostname(api, run):
    api.add("GET", VOLUMES, [vol(id=3, alias="other")])
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1", "status": "active"})
    api.add("POST", SERVERS + "42/volumes/", vol(attached=True, server="web1"), status=201)

    result = run(volume, volume_alias="data", hostname="web1", product="fast-storage", size_gigabytes=10)

    assert not result.failed, result.result
    assert result.changed
    assert result["volume"]["id"] == 7
    assert api.writes() == [
        ("POST", SERVERS + "42/volumes/", {"alias": "data", "size": 10, "product": "fast-storage"})]


def test_existing_volume_is_unchanged(api, run):
    api.add("GET", VOLUMES, [vol()])

    result = run(volume, volume_alias="data", hostname="web1", product="fast-storage", size_gigabytes=10)

    assert not result.failed, result.result
    assert not result.changed
    assert result["volume"]["id"] == 7
    assert api.writes() == []


def test_grows_volume_and_changes_project(api, run):
    api.add("GET", VOLUMES, [vol()])
    api.add("PATCH", VOLUMES + "7/", vol(size=20, project="shop"))

    result = run(volume, volume_alias="data", size_gigabytes=20, project="shop")

    assert result.changed
    assert result["volume"]["size"] == 20
    assert api.writes() == [("PATCH", VOLUMES + "7/", {"size": 20, "project": "shop"})]


def test_shrinking_fails(api, run):
    api.add("GET", VOLUMES, [vol(size=50)])

    result = run(volume, volume_alias="data", size_gigabytes=20)

    assert result.failed
    assert "shrink" in result["msg"]
    assert api.writes() == []


def test_create_check_mode_makes_no_writes(api, run):
    api.add("GET", VOLUMES, [])
    api.add("GET", SERVERS + "42/", {"id": 42, "hostname": "web1", "status": "active"})

    result = run(volume, check_mode=True, volume_alias="data", server_id=42, product="fast-storage",
                 size_gigabytes=10)

    assert result.changed
    assert api.writes() == []


def test_resize_check_mode_makes_no_writes(api, run):
    api.add("GET", VOLUMES, [vol()])

    result = run(volume, check_mode=True, volume_alias="data", size_gigabytes=30)

    assert result.changed
    assert api.writes() == []


def test_create_lists_missing_options(api, run):
    api.add("GET", VOLUMES, [])

    result = run(volume, volume_alias="data")

    assert result.failed
    for name in ("hostname", "server_id", "product", "size_gigabytes"):
        assert name in result["msg"]


def test_absent_deletes_detached_volume_without_product_or_size(api, run):
    api.add("GET", VOLUMES, [vol()])
    api.add("DELETE", VOLUMES + "7/", status=204)

    result = run(volume, state="absent", volume_alias="data")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("DELETE", VOLUMES + "7/", None)]


def test_absent_attached_volume_fails(api, run):
    api.add("GET", VOLUMES, [vol(attached=True, server="web1")])

    result = run(volume, state="absent", volume_alias="data")

    assert result.failed
    assert "volume_action" in result["msg"]
    assert api.writes() == []


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", VOLUMES, [vol()])

    result = run(volume, check_mode=True, state="absent", volume_alias="data")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_volume_is_ok(api, run):
    api.add("GET", VOLUMES, [])

    result = run(volume, state="absent", volume_alias="data")

    assert not result.failed
    assert not result.changed


def test_duplicate_alias_fails(api, run):
    api.add("GET", VOLUMES, [vol(id=1), vol(id=2)])

    result = run(volume, state="absent", volume_alias="data")

    assert result.failed
    assert api.writes() == []
