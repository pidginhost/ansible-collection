# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_cluster_vm as module

CLUSTER = "/api/kubernetes/clusters/7/"
CONNECTED = CLUSTER + "connected-vms/"
ELIGIBLE = CLUSTER + "eligible-vms/"

DB = {"id": 42, "hostname": "db1.example.com"}
DB_CONNECTED = dict(DB, ip="192.0.2.100")


def setup(api, *connected):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("GET", CONNECTED, {"vms": list(connected)})


def test_connects_server_by_hostname_and_waits(api, run):
    setup(api)
    api.add("GET", CONNECTED, {"vms": []})
    api.add("GET", CONNECTED, {"vms": [DB_CONNECTED]})
    api.add("GET", ELIGIBLE, {"vms": [{"id": 41, "hostname": "web1.example.com"}, DB]})
    api.add("POST", CLUSTER + "connect-vm/", {"status": "OK", "message": "VM connection initiated."})

    result = run(module, cluster_id=7, server_hostname="db1.example.com")

    assert not result.failed, result.result
    assert result.changed
    assert result["vm"] == DB_CONNECTED
    assert api.writes() == [("POST", CLUSTER + "connect-vm/", {"server": 42})]


def test_connected_server_is_unchanged(api, run):
    setup(api, DB_CONNECTED)

    result = run(module, cluster_id=7, server_id=42)

    assert not result.failed, result.result
    assert not result.changed
    assert result["vm"] == DB_CONNECTED
    assert api.writes() == []


def test_ineligible_server_fails_with_access_hint(api, run):
    setup(api)
    api.add("GET", ELIGIBLE, {"vms": []})

    result = run(module, cluster_id=7, server_id=42)

    assert result.failed
    assert "cloud VM access" in result["msg"]
    assert api.writes() == []


def test_disconnects_server_and_waits(api, run):
    setup(api, DB_CONNECTED)
    api.add("GET", CONNECTED, {"vms": [DB_CONNECTED]})
    api.add("GET", CONNECTED, {"vms": []})
    api.add("POST", CLUSTER + "disconnect-vm/", {"status": "OK", "message": "VM disconnection initiated."})

    result = run(module, cluster_id=7, server_id=42, state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert result["vm"] == DB_CONNECTED
    assert api.writes() == [("POST", CLUSTER + "disconnect-vm/", {"server": 42})]


def test_disconnected_server_is_unchanged_when_absent(api, run):
    setup(api)

    result = run(module, cluster_id=7, server_hostname="db1.example.com", state="absent")

    assert not result.changed
    assert result["vm"] == {}


def test_check_mode_makes_no_writes(api, run):
    setup(api, DB_CONNECTED)
    api.add("GET", ELIGIBLE, {"vms": [{"id": 41, "hostname": "web1.example.com"}]})

    connected = run(module, check_mode=True, cluster_id=7, server_id=41)
    disconnected = run(module, check_mode=True, cluster_id=7, server_id=42, state="absent")

    assert connected.changed and disconnected.changed
    assert api.writes() == []
