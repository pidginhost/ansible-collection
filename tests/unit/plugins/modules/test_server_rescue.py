# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server_rescue

SERVERS = "/api/cloud/servers/"
SERVER = SERVERS + "42/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def detail(rescue_mode=False, **kw):
    base = {"id": 42, "hostname": "web1", "status": "active", "rescue_mode": rescue_mode, "boot_iso": None}
    base.update(kw)
    return base


def test_present_enters_rescue_and_waits(api, run):
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail(True, boot_iso="systemrescue"))
    api.add("POST", SERVER + "rescue/enter/", {"queued": True}, status=202)

    result = run(server_rescue, server_hostname="web1", iso="systemrescue")

    assert not result.failed, result.result
    assert result.changed
    assert result["server"]["rescue_mode"] is True
    assert api.writes() == [("POST", SERVER + "rescue/enter/", {"iso": "systemrescue"})]


def test_present_default_image_sends_empty_body(api, run):
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER, detail())
    api.add("GET", SERVER, detail(True))
    api.add("POST", SERVER + "rescue/enter/", {"queued": True}, status=202)

    result = run(server_rescue, server_id=42)

    assert result.changed
    assert api.writes() == [("POST", SERVER + "rescue/enter/", {})]


def test_present_in_rescue_is_unchanged(api, run):
    api.add("GET", SERVER, detail(True))

    result = run(server_rescue, server_id=42)

    assert not result.changed
    assert api.writes() == []


def test_present_check_mode_makes_no_writes(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_rescue, check_mode=True, server_id=42)

    assert result.changed
    assert api.writes() == []


def test_absent_exits_rescue_and_waits(api, run):
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER, detail(True))
    api.add("GET", SERVER, detail())
    api.add("POST", SERVER + "rescue/exit/", {"queued": True}, status=202)

    result = run(server_rescue, server_id=42, state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert result["server"]["rescue_mode"] is False
    assert [(c[0], c[1]) for c in api.writes()] == [("POST", SERVER + "rescue/exit/")]


def test_absent_not_in_rescue_is_unchanged(api, run):
    api.add("GET", SERVER, detail())

    result = run(server_rescue, server_id=42, state="absent")

    assert not result.changed
    assert api.writes() == []


def test_timeout_fails(api, run):
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER, detail(True))
    api.add("POST", SERVER + "rescue/exit/", {"queued": True}, status=202)

    result = run(server_rescue, server_id=42, state="absent", timeout=0)

    assert result.failed
    assert result.changed


def test_api_error_fails(api, run):
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER, detail())
    api.add("POST", SERVER + "rescue/enter/", {"message": "Unknown ISO."}, status=400)

    result = run(server_rescue, server_id=42, iso="nope")

    assert result.failed
    assert "Unknown ISO" in result["msg"]


def test_refused_exit_fails_at_once(api, run):
    # The API answers 202; the queued task only logs that it could not run.
    api.add("GET", SERVER, detail(True))
    api.add("POST", SERVER + "rescue/exit/", {"queued": True}, status=202)
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER + "activity/", {"logs": [{
        "date": "2026-01-01 12:00",
        "message": "Could not exit ISO boot: the server could not start from its disk."}]})

    result = run(server_rescue, server_id=42, state="absent", timeout=5)

    assert result.failed
    assert result.changed
    assert "could not start from its disk" in result["msg"]
    assert len(api.writes()) == 1


def test_busy_past_the_timeout_fails(api, run):
    busy = {"date": "2026-01-01 12:00", "message": "Could not exit rescue mode: another server operation is in progress."}
    api.add("GET", SERVER, detail(True))
    api.add("POST", SERVER + "rescue/exit/", {"queued": True}, status=202)
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER + "activity/", {"logs": [busy]})

    result = run(server_rescue, server_id=42, state="absent", timeout=0)

    assert result.failed
    assert result.changed


def test_refused_enter_fails_at_once(api, run):
    api.add("GET", SERVER, detail())
    api.add("POST", SERVER + "rescue/enter/", {"queued": True}, status=202)
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER + "activity/", {"logs": [{
        "date": "2026-01-01 12:00", "message": "Could not boot from ISO: that image is no longer available."}]})

    result = run(server_rescue, server_id=42, iso="gone", timeout=5)

    assert result.failed
    assert "no longer available" in result["msg"]


def test_busy_refusal_is_resubmitted(api, run):
    # "Another server operation is in progress" means nothing ran: send the request again.
    busy = {"date": "2026-01-01 12:00", "message": "Could not exit rescue mode: another server operation is in progress."}
    api.add("GET", SERVER, detail(True))
    api.add("GET", SERVER, detail(True))
    api.add("GET", SERVER, detail())
    api.add("POST", SERVER + "rescue/exit/", {"queued": True}, status=202)
    api.add("GET", SERVER + "activity/", {"logs": []})
    api.add("GET", SERVER + "activity/", {"logs": [busy]})
    api.add("GET", SERVER + "activity/", {"logs": [busy]})
    api.add("GET", SERVER + "activity/", {"logs": [busy, {"date": "2026-01-01 12:01", "message": "Server exited ISO boot."}]})

    result = run(server_rescue, server_id=42, state="absent", timeout=120)

    assert not result.failed, result.result
    assert result.changed
    assert result["server"]["rescue_mode"] is False
    assert [c[1] for c in api.writes()] == [SERVER + "rescue/exit/", SERVER + "rescue/exit/"]
