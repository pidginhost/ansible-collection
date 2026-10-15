# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.pidginhost.cloud.plugins.module_utils.common import PidginHostAPI

SERVERS = "/api/cloud/servers/"


def page(results, next_page=None):
    return {"count": len(results), "next": next_page, "previous": None, "results": results}


def test_list_follows_every_page(api, make_module):
    api.add("GET", SERVERS, page([{"id": 1}], "https://www.pidginhost.com/api/cloud/servers/?page=2"))
    api.add("GET", SERVERS + "?page=2", page([{"id": 2}], "https://www.pidginhost.com/api/cloud/servers/?page=3"))
    api.add("GET", SERVERS + "?page=3", page([{"id": 3}]))

    assert PidginHostAPI(make_module()).list(SERVERS) == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_list_keeps_filters_on_later_pages(api, make_module):
    path = "/api/cloud/server-packages/"
    api.add("GET", path + "?generation=gp", page([{"id": 1}], "x"))
    api.add("GET", path + "?generation=gp&page=2", page([{"id": 2}]))

    assert PidginHostAPI(make_module()).list(path, generation="gp") == [{"id": 1}, {"id": 2}]


def test_list_accepts_plain_arrays(api, make_module):
    api.add("GET", "/api/cloud/volumes/", [{"id": 7}])

    assert PidginHostAPI(make_module()).list("/api/cloud/volumes/") == [{"id": 7}]


def test_request_failure_reports_status_and_api_message(api, make_module):
    api.add("POST", SERVERS, {"package": ["Invalid package."]}, status=400)

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module()).post(SERVERS, {"package": "nope"})

    assert exc.value.failed
    assert exc.value["status_code"] == 400
    assert exc.value["response"] == {"package": ["Invalid package."]}
    assert "Invalid package." in exc.value["msg"]


def test_connection_error_fails_with_reason(api, make_module):
    api.add("GET", SERVERS, status=-1)

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module()).get(SERVERS)

    assert "Connection refused" in exc.value["msg"]


def test_allow_404_returns_none(api, make_module):
    api.add("GET", SERVERS + "9/", {"detail": "Not found."}, status=404)

    assert PidginHostAPI(make_module()).get(SERVERS + "9/", allow_404=True) is None


def test_delete_without_body_returns_empty_dict(api, make_module):
    api.add("DELETE", SERVERS + "9/", status=204)

    assert PidginHostAPI(make_module()).delete(SERVERS + "9/") == {}


def test_find_one_fails_on_duplicates(api, make_module):
    client = PidginHostAPI(make_module())

    with pytest.raises(Exception) as exc:
        client.find_one([{"id": 1, "hostname": "a"}, {"id": 2, "hostname": "a"}], "server", hostname="a")

    assert "1, 2" in exc.value["msg"]


def test_find_server_by_hostname_returns_detail(api, make_module):
    api.add("GET", SERVERS, page([{"id": 5, "hostname": "web"}]))
    api.add("GET", SERVERS + "5/", {"id": 5, "hostname": "web", "volumes": []})

    assert PidginHostAPI(make_module()).find_server(hostname="web") == {"id": 5, "hostname": "web", "volumes": []}


def test_wait_for_gives_up_at_timeout(api, make_module):
    calls = []

    def fetch():
        calls.append(1)
        return {"status": "provisioning"}

    obj = PidginHostAPI(make_module(timeout=0)).wait_for(fetch, lambda s: s["status"] == "active")

    assert obj is None
    assert len(calls) == 1


def test_empty_array_stays_a_list(api, make_module):
    api.add("GET", SERVERS + "9/snapshots/", [])

    assert PidginHostAPI(make_module()).get(SERVERS + "9/snapshots/") == []


def test_read_failure_after_mutation_reports_change(api, make_module):
    api.add("POST", SERVERS, {"id": 5}, status=201)
    api.add("GET", SERVERS + "5/", status=-1)
    client = PidginHostAPI(make_module())
    client.post(SERVERS, {"hostname": "web1.example.com"})

    with pytest.raises(Exception) as exc:
        client.get(SERVERS + "5/")

    assert exc.value.failed
    assert exc.value.changed


def test_first_request_failure_does_not_claim_change(api, make_module):
    api.add("POST", SERVERS, {"detail": "Invalid request."}, status=400)

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module()).post(SERVERS, {})

    assert exc.value.failed
    assert not exc.value.changed


def test_custom_accept_returns_text(api, make_module):
    api.add("GET", "/api/kubernetes/clusters/7/kubeconfig/", "apiVersion: v1\n")

    client = PidginHostAPI(make_module())
    assert client.get("/api/kubernetes/clusters/7/kubeconfig/", accept="text/plain") == "apiVersion: v1\n"
    assert api.headers[-1]["Accept"] == "text/plain"
