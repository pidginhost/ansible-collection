# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import servers_info

SERVERS = "/api/cloud/servers/"
SERVER = SERVERS + "42/"


def page(results, next_page=None):
    return {"count": len(results), "next": next_page, "previous": None, "results": results}


def test_lists_every_server(api, run):
    api.add("GET", SERVERS, page([{"id": 1}], "x"))
    api.add("GET", SERVERS + "?page=2", page([{"id": 2}]))

    result = run(servers_info, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["servers"] == [{"id": 1}, {"id": 2}]


def test_empty_account_returns_empty_list(api, run):
    api.add("GET", SERVERS, page([]))

    result = run(servers_info)

    assert not result.failed
    assert result["servers"] == []


def test_selects_one_server_by_hostname(api, run):
    api.add("GET", SERVERS, page([{"id": 42, "hostname": "web1"}, {"id": 43, "hostname": "web2"}]))
    api.add("GET", SERVER, {"id": 42, "hostname": "web1", "status": "active"})

    result = run(servers_info, server_hostname="web1")

    assert result["servers"] == [{"id": 42, "hostname": "web1", "status": "active"}]


def test_include_adds_extra_keys(api, run):
    api.add("GET", SERVER, {"id": 42, "hostname": "web1"})
    api.add("GET", SERVER + "snapshots/", [])
    api.add("GET", SERVER + "usage/", {"status": "running", "uptime": 10})
    api.add("GET", SERVER + "traffic/", {"bytes_total": 5})
    api.add("GET", SERVER + "activity/", {"logs": [{"message": "Started", "date": "2026-01-01"}]})
    api.add("GET", SERVER + "boot-isos/", [{"slug": "systemrescue", "compatible": True}])

    result = run(servers_info, check_mode=True, server_id=42,
                 include=["snapshots", "usage", "traffic", "activity", "boot_isos"])

    assert not result.failed, result.result
    server = result["servers"][0]
    assert server["snapshots"] == []
    assert server["usage"] == {"status": "running", "uptime": 10}
    assert server["traffic"] == {"bytes_total": 5}
    assert server["activity"] == [{"message": "Started", "date": "2026-01-01"}]
    assert server["boot_isos"] == [{"slug": "systemrescue", "compatible": True}]
    assert api.writes() == []


def test_include_requires_a_server(api, run):
    result = run(servers_info, include=["usage"])

    assert result.failed
    assert api.calls == []


def test_missing_server_fails(api, run):
    api.add("GET", SERVERS + "9/", status=404)

    result = run(servers_info, server_id=9)

    assert result.failed


def test_server_id_and_hostname_are_exclusive(api, run):
    result = run(servers_info, server_id=42, server_hostname="web1")

    assert result.failed
