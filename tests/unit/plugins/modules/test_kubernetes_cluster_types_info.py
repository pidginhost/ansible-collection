# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_cluster_types_info as module

TYPES = "/api/kubernetes/cluster-types/"


def test_lists_every_cluster_type(api, run):
    dev = {"type": "dev", "worker_nodes_count_min": 1, "worker_nodes_count_max": 3,
           "worker_node_packages": [{"id": 1, "slug": "k8s-w2", "name": "Worker 2"}]}
    prod = dict(dev, type="prod", worker_nodes_count_min=3)
    api.add("GET", TYPES, {"count": 2, "next": "https://www.pidginhost.com" + TYPES + "?page=2", "previous": None,
                           "results": [dev]})
    api.add("GET", TYPES + "?page=2", {"count": 2, "next": None, "previous": None, "results": [prod]})

    result = run(module)

    assert not result.failed, result.result
    assert not result.changed
    assert [t["type"] for t in result["cluster_types"]] == ["dev", "prod"]
