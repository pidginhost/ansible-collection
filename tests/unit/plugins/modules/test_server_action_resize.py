# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server_action_resize

SERVERS = "/api/cloud/servers/"
SERVER = SERVERS + "42/"
VOLUME = "/api/cloud/volumes/7/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def detail(**kw):
    base = {
        "id": 42, "hostname": "web1", "status": "active", "package": "cloudv-1",
        "volumes": [{"id": 7, "alias": "data", "size": 20, "product": "fast-storage", "attached": True}],
    }
    base.update(kw)
    return base


def test_package_change_waits_until_active(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail(status="upgrading", package="cloudv-3"))
    api.add("GET", SERVER, detail(package="cloudv-3"))
    api.add("POST", SERVER + "modify-package/", {"upgrading": True})

    result = run(server_action_resize, server_hostname="web1", package="cloudv-3")

    assert not result.failed, result.result
    assert result.changed
    assert result["action"]["package"] == "cloudv-3"
    assert api.writes() == [("POST", SERVER + "modify-package/", {"package": "cloudv-3"})]


def test_same_package_is_unchanged(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, server_id=42, disk=False, package_name="cloudv-1", state="present")

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_package_change_check_mode_makes_no_writes(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, check_mode=True, server_id=42, package_name="cloudv-3")

    assert result.changed
    assert api.writes() == []


def test_package_change_timeout_fails(api, run):
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail(status="upgrading", package="cloudv-3"))
    api.add("POST", SERVER + "modify-package/", {"upgrading": True})

    result = run(server_action_resize, server_id=42, package_name="cloudv-3", timeout=0)

    assert result.failed
    assert result.changed


def test_package_is_required_without_disk(api, run):
    result = run(server_action_resize, server_id=42)

    assert result.failed
    assert "package_name" in result["msg"]


def test_disk_grows_volume(api, run):
    api.add("GET", SERVER, detail())
    api.add("PATCH", VOLUME, {"id": 7, "alias": "data", "size": 40})

    result = run(server_action_resize, server_id=42, disk=True, volume_alias="data", size_gigabytes=40,
                 project="shop", product="ignored")

    assert not result.failed, result.result
    assert result.changed
    assert result["action"]["size"] == 40
    assert api.writes() == [("PATCH", VOLUME, {"size": 40, "project": "shop"})]


def test_disk_same_size_is_unchanged(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, server_id=42, disk=True, volume_alias="data", size_gigabytes=20)

    assert not result.changed
    assert api.writes() == []


def test_disk_check_mode_makes_no_writes(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, check_mode=True, server_id=42, disk=True, volume_alias="data",
                 size_gigabytes=40)

    assert result.changed
    assert api.writes() == []


def test_disk_cannot_shrink(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, server_id=42, disk=True, volume_alias="data", size_gigabytes=10)

    assert result.failed
    assert api.writes() == []


def test_disk_missing_volume_fails(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_action_resize, server_id=42, disk=True, volume_alias="other", size_gigabytes=40)

    assert result.failed
    assert "other" in result["msg"]


def test_active_old_package_does_not_finish_resize(api, run):
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail(status="upgrading", package="cloudv-3"))
    api.add("GET", SERVER, detail(package="cloudv-3"))
    api.add("POST", SERVER + "modify-package/", {"upgrading": True})

    result = run(server_action_resize, server_id=42, package="cloudv-3")

    assert not result.failed
    assert result["action"]["package"] == "cloudv-3"
    assert len(api.requests("GET", SERVER)) == 4


def test_package_id_of_current_package_is_unchanged(api, run):
    api.add("GET", SERVER, detail())
    api.add("GET", "/api/cloud/server-packages/7/", {"id": 7, "slug": "cloudv-1"})

    for check_mode in (False, True):
        result = run(server_action_resize, server_id=42, package="7", check_mode=check_mode)

        assert not result.failed
        assert not result.changed
        assert api.writes() == []
