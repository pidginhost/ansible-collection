# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.pidginhost.cloud.plugins.module_utils import common
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


CLUSTERS = "/api/kubernetes/clusters/"


def test_require_cluster_by_name(api, make_module):
    api.add("GET", CLUSTERS, page([{"id": 3, "name": "prod"}, {"id": 4, "name": "dev"}]))

    assert PidginHostAPI(make_module()).require_cluster(name="dev") == {"id": 4, "name": "dev"}


def test_require_cluster_by_id_fails_when_missing(api, make_module):
    api.add("GET", CLUSTERS + "9/", status=404)

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module()).require_cluster(cluster_id=9)

    assert "not found" in exc.value["msg"]


def test_allowed_error_status_returns_body_without_failing(api, make_module):
    refusal = {"message": "Validation error", "extra": {"fields": {"non_field_errors": ["latest"]}}}
    api.add("POST", CLUSTERS + "4/kube-version-upgrade/", refusal, status=400)

    client = PidginHostAPI(make_module())
    assert client.post(CLUSTERS + "4/kube-version-upgrade/", allow_status=(400,)) == refusal
    assert client.status == 400
    assert client.changed is False


def test_read_only_post_preserves_prior_change_tracking(api, make_module):
    path = CLUSTERS + "4/upgrade-lb/"
    api.add("POST", path, {})
    client = PidginHostAPI(make_module())

    client.post(path, {"dry_run": True}, read_only=True)
    assert not client.changed
    client.post(path, {"inspection_id": "test"})
    client.post(path, {"dry_run": True}, read_only=True)
    assert client.changed


def test_sensitive_transport_errors_are_redacted(monkeypatch, make_module):
    monkeypatch.setattr("ansible_collections.pidginhost.cloud.plugins.module_utils.common.fetch_url",
                        lambda *args, **kwargs: (None, {"status": -1, "msg": "private-key-sentinel"}))

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module(), sensitive=True).get("/api/kubernetes/clusters/7/kubeconfig/")

    assert exc.value.failed
    assert "private-key-sentinel" not in str(exc.value.result)


def test_throttled_request_waits_and_retries(api, make_module, monkeypatch):
    slept = []
    monkeypatch.setattr("ansible_collections.pidginhost.cloud.plugins.module_utils.common.time.sleep", slept.append)
    throttled = {"message": "Request was throttled. Expected available in 3 seconds."}
    api.add("GET", SERVERS + "9/", throttled, status=429, headers={"retry-after": "3"})
    api.add("GET", SERVERS + "9/", {"id": 9})

    assert PidginHostAPI(make_module()).get(SERVERS + "9/") == {"id": 9}
    assert slept == [3]


def test_throttling_past_the_timeout_fails(api, make_module):
    api.add("GET", SERVERS + "9/", {"message": "throttled"}, status=429, headers={"retry-after": "3"})

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module(timeout=0)).get(SERVERS + "9/")

    assert exc.value["status_code"] == 429


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        now = 0.0

        def sleep(self, seconds):
            self.now += seconds

    value = Clock()
    monkeypatch.setattr(common.time, "monotonic", lambda: value.now)
    monkeypatch.setattr(common.time, "sleep", value.sleep)
    return value


def test_retry_after_is_not_shortened(api, make_module, clock):
    api.add("GET", SERVERS, status=429, headers={"retry-after": "120"})
    api.add("GET", SERVERS, [])

    assert PidginHostAPI(make_module()).get(SERVERS) == []
    assert clock.now == 120


def test_retry_after_accepts_http_date(api, make_module, clock, monkeypatch):
    monkeypatch.setattr(common.time, "time", lambda: 1767225600 + clock.now)
    api.add("GET", SERVERS, status=429, headers={"retry-after": "Thu, 01 Jan 2026 00:02:00 GMT"})
    api.add("GET", SERVERS, [])

    assert PidginHostAPI(make_module()).get(SERVERS) == []
    assert clock.now == 120


@pytest.mark.parametrize("delay", ["120", "9" * 400], ids=["long", "huge"])
def test_retry_after_beyond_budget_does_not_resubmit(api, make_module, clock, delay):
    api.add("POST", SERVERS, status=429, headers={"retry-after": delay})
    api.add("POST", SERVERS, {"id": 9})

    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module(timeout=90)).post(SERVERS)

    assert exc.value["status_code"] == 429
    assert len(api.writes()) == 1


def test_retry_budget_includes_request_time(api, make_module, clock, monkeypatch):
    api.add("POST", SERVERS, status=429, headers={"retry-after": "3"})
    api.add("POST", SERVERS, {"id": 9})

    def slow_request(*args, **kwargs):
        clock.now += 8
        return api(*args, **kwargs)

    monkeypatch.setattr(common, "fetch_url", slow_request)
    with pytest.raises(Exception) as exc:
        PidginHostAPI(make_module(timeout=10)).post(SERVERS)

    assert exc.value["status_code"] == 429
    assert len(api.writes()) == 1


def test_retried_request_uses_remaining_timeout(api, make_module, clock, monkeypatch):
    api.add("GET", SERVERS, status=429, headers={"retry-after": "3"})
    api.add("GET", SERVERS, [])
    timeouts = []

    def request(*args, **kwargs):
        timeouts.append(kwargs["timeout"])
        return api(*args, **kwargs)

    monkeypatch.setattr(common, "fetch_url", request)
    assert PidginHostAPI(make_module(timeout=30)).get(SERVERS) == []
    assert timeouts == [30, 27]


@pytest.mark.parametrize("timeout", [0, 5])
def test_busy_activity_never_resubmits_after_timeout(api, make_module, clock, timeout):
    busy = {"date": "2026-01-01 12:00", "message": "Could not exit rescue mode: another server operation is in progress."}
    if timeout:
        api.add("GET", SERVERS + "9/activity/", {"logs": []})
    api.add("GET", SERVERS + "9/activity/", {"logs": [busy]})
    submits = []
    client = PidginHostAPI(make_module(timeout=timeout))

    with pytest.raises(Exception) as exc:
        client.wait_activity(9, common.Counter(), ("Could not exit rescue mode",), lambda fresh: None,
                             "Leaving rescue", resubmit=lambda: submits.append(clock.now))

    assert exc.value.failed
    assert submits == []


def test_throttled_poll_cannot_extend_operation_timeout(api, make_module, clock):
    api.add("GET", SERVERS, [])
    api.add("GET", SERVERS, status=429, headers={"retry-after": "3"})
    client = PidginHostAPI(make_module(timeout=7))

    with pytest.raises(Exception) as exc:
        client.wait_for(lambda: client.get(SERVERS), bool)

    assert exc.value["status_code"] == 429
    assert clock.now <= 7


@pytest.mark.parametrize("reverse", [False, True])
def test_terminal_activity_failure_wins_over_busy(api, make_module, clock, reverse):
    messages = ["Could not exit rescue mode: another server operation is in progress.",
                "Could not exit rescue mode: the disk could not start."]
    logs = [{"date": "2026-01-01 12:00", "message": message} for message in messages]
    api.add("GET", SERVERS + "9/activity/", {"logs": logs[::-1] if reverse else logs})
    submits = []
    client = PidginHostAPI(make_module(timeout=5))

    with pytest.raises(Exception) as exc:
        client.wait_activity(9, common.Counter(), ("Could not exit rescue mode",), lambda fresh: None,
                             "Leaving rescue", resubmit=lambda: submits.append(clock.now))

    assert exc.value.failed
    assert "disk could not start" in exc.value["msg"]
    assert submits == []


def test_repeated_busy_refusals_are_resubmitted_at_intervals(api, make_module, clock):
    busy = {"date": "2026-01-01 12:00", "message": "Could not exit rescue mode: another server operation is in progress."}
    api.add("GET", SERVERS + "9/activity/", {"logs": [busy]})
    # The API's timestamps can repeat, but each refusal must still be counted.
    api.add("GET", SERVERS + "9/activity/", {"logs": [busy, busy]})
    submits = []
    client = PidginHostAPI(make_module(timeout=60))

    result = client.wait_activity(
        9, common.Counter(), ("Could not exit rescue mode",),
        lambda fresh: "done" if len(submits) == 2 else None, "Leaving rescue",
        resubmit=lambda: submits.append(clock.now))

    assert result == "done"
    assert submits == [0, 30]


def test_busy_log_read_exhausting_timeout_does_not_resubmit(api, make_module, clock, monkeypatch):
    busy = {"date": "2026-01-01 12:00", "message": "Could not exit rescue mode: another server operation is in progress."}
    api.add("GET", SERVERS + "9/activity/", {"logs": [busy]})
    submits = []

    def slow_request(*args, **kwargs):
        clock.now += 5
        return api(*args, **kwargs)

    monkeypatch.setattr(common, "fetch_url", slow_request)
    client = PidginHostAPI(make_module(timeout=5))
    with pytest.raises(Exception) as exc:
        client.wait_activity(9, common.Counter(), ("Could not exit rescue mode",), lambda fresh: None,
                             "Leaving rescue", resubmit=lambda: submits.append(clock.now))

    assert exc.value.failed
    assert submits == []


def test_finished_wait_does_not_limit_later_requests(api, make_module, clock):
    client = PidginHostAPI(make_module(timeout=10))
    assert client.wait_for(lambda: None, bool) is None
    assert clock.now == 10
    api.add("GET", SERVERS, status=429, headers={"retry-after": "3"})
    api.add("GET", SERVERS, [])

    assert client.get(SERVERS) == []
    assert clock.now == 13


def test_requests_near_the_end_of_a_wait_keep_a_usable_timeout(api, make_module, monkeypatch):
    # The last poll of a wait can start with well under a second left; a request that short fails on a real network.
    monkeypatch.setattr("ansible_collections.pidginhost.cloud.plugins.module_utils.common.time.monotonic",
                        lambda: 299.5)
    api.add("GET", SERVERS + "9/", {"status": "provisioning"})
    client = PidginHostAPI(make_module(timeout=300))
    client._wait_deadline = 300

    client.get(SERVERS + "9/")

    assert api.timeouts == [10]
