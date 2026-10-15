# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_port_forward as module

CLUSTER = "/api/kubernetes/clusters/7/"
FORWARDS = CLUSTER + "port-forwards/"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def forward(**kw):
    base = {"id": 2, "internal_ip": "192.0.2.20", "port": 8080, "protocol": "tcp"}
    base.update(kw)
    return base


def prepare(api, *forwards):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("GET", FORWARDS, page(*forwards))


def test_creates_forward(api, run):
    prepare(api, forward(protocol="udp"))
    api.add("POST", FORWARDS, forward(id=3), status=201)

    result = run(module, cluster_id=7, port=8080, protocol="tcp", internal_ip="192.0.2.20")

    assert not result.failed, result.result
    assert result.changed
    assert result["port_forward"]["id"] == 3
    assert api.writes() == [("POST", FORWARDS, {"port": 8080, "protocol": "tcp", "internal_ip": "192.0.2.20"})]


def test_matching_forward_is_unchanged(api, run):
    prepare(api, forward())

    result = run(module, cluster_id=7, port=8080, protocol="tcp", internal_ip="192.0.2.20")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_changed_internal_ip_is_patched(api, run):
    prepare(api, forward())
    api.add("PATCH", FORWARDS + "2/", forward(internal_ip="192.0.2.21"))

    result = run(module, cluster_id=7, port=8080, protocol="tcp", internal_ip="192.0.2.21")

    assert not result.failed, result.result
    assert result.changed
    assert result["port_forward"]["internal_ip"] == "192.0.2.21"
    assert api.writes() == [("PATCH", FORWARDS + "2/", {"internal_ip": "192.0.2.21"})]


def test_forward_is_deleted(api, run):
    prepare(api, forward())
    api.add("DELETE", FORWARDS + "2/", None, status=204)

    result = run(module, cluster_id=7, port=8080, protocol="tcp", state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("DELETE", FORWARDS + "2/", None)]


def test_missing_forward_is_unchanged_when_absent(api, run):
    prepare(api, forward(protocol="udp"))

    result = run(module, cluster_id=7, port=8080, protocol="tcp", state="absent")

    assert not result.changed
    assert result["port_forward"] == {}


def test_check_mode_makes_no_writes(api, run):
    prepare(api, forward())

    created = run(module, check_mode=True, cluster_id=7, port=9090, protocol="tcp", internal_ip="192.0.2.20")
    changed = run(module, check_mode=True, cluster_id=7, port=8080, protocol="tcp", internal_ip="192.0.2.21")
    deleted = run(module, check_mode=True, cluster_id=7, port=8080, protocol="tcp", state="absent")

    assert created.changed and changed.changed and deleted.changed
    assert api.writes() == []


def test_create_requires_internal_ip(api, run):
    prepare(api)

    result = run(module, cluster_id=7, port=8080, protocol="tcp")

    assert result.failed
    assert "internal_ip" in result["msg"]
