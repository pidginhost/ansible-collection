# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_kubeconfig as module

CLUSTERS = "/api/kubernetes/clusters/"
CLUSTER = CLUSTERS + "7/"
KUBECONFIG = CLUSTER + "kubeconfig/"
CONFIG = "apiVersion: v1\nkind: Config\n"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def test_reads_kubeconfig_as_text(api, run):
    api.add("GET", CLUSTERS, page({"id": 7, "name": "prod", "status": "active"}))
    api.add("GET", KUBECONFIG, CONFIG)

    result = run(module, cluster_name="prod")

    assert not result.failed, result.result
    assert not result.changed
    assert result["kubeconfig"] == CONFIG
    assert api.headers[-1]["Accept"] == "text/plain"
    assert api.writes() == []


def test_regenerate_posts_and_returns_new_config(api, run):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("POST", KUBECONFIG, "apiVersion: v1\nkind: Config\n# new\n")

    result = run(module, cluster_id=7, regenerate=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["kubeconfig"].endswith("# new\n")
    assert api.headers[-1]["Accept"] == "text/plain"
    assert api.writes() == [("POST", KUBECONFIG, {})]


def test_regenerate_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("GET", KUBECONFIG, CONFIG)

    result = run(module, check_mode=True, cluster_id=7, regenerate=True)

    assert result.changed
    assert result["kubeconfig"] == CONFIG
    assert api.writes() == []


def test_missing_cluster_fails(api, run):
    api.add("GET", CLUSTERS, page())

    result = run(module, cluster_name="prod")

    assert result.failed
    assert "not found" in result["msg"]


@pytest.mark.parametrize("regenerate", [False, True])
@pytest.mark.parametrize("body", ["client-key-data: private-key-sentinel", {"config": "private-key-sentinel"}])
def test_error_never_returns_credential_body(api, run, regenerate, body):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("POST" if regenerate else "GET", KUBECONFIG, body, status=502)

    result = run(module, cluster_id=7, regenerate=regenerate)

    assert result.failed
    assert result["status_code"] == 502
    assert "private-key-sentinel" not in str(result.result)
    assert "response" not in result.result
