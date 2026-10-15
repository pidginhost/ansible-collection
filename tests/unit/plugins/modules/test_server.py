# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import server

SERVERS = "/api/cloud/servers/"


def listing(*servers):
    return {"count": len(servers), "next": None, "previous": None, "results": list(servers)}


def detail(**kw):
    base = {"id": 42, "hostname": "web1", "project": "", "status": "active", "destroy_protection": False}
    base.update(kw)
    return base


def test_creates_missing_server_and_waits_until_active(api, run):
    api.add("GET", SERVERS, listing())
    api.add("POST", SERVERS, {"id": 42}, status=201)
    api.add("GET", SERVERS + "42/", status=404)  # pending servers are hidden
    api.add("GET", SERVERS + "42/", detail(status="provisioning"))
    api.add("GET", SERVERS + "42/", detail())

    result = run(server, hostname="web1", image="ubuntu24", package="cloudv-1",
                 ssh_pub_key_id="7", new_ipv4=True, extra_volume_size=20, user_data="#!/bin/sh\ntrue\n")

    assert not result.failed, result.result
    assert result.changed
    assert result["server"]["id"] == 42
    assert api.requests("POST", SERVERS)[0][2] == {
        "hostname": "web1", "image": "ubuntu24", "package": "cloudv-1", "ssh_pub_key_id": "7",
        "new_ipv4": True, "extra_volume_size": 20, "user_data": "#!/bin/sh\ntrue\n",
    }


def test_existing_server_is_unchanged(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", detail())

    result = run(server, hostname="web1", image="ubuntu24", package="cloudv-1")

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_existing_server_gets_project_and_destroy_protection(api, run):
    api.add("GET", SERVERS + "42/", detail())
    api.add("PATCH", SERVERS + "42/", detail(project="shop"))
    api.add("POST", SERVERS + "42/destroy-protection/", {"destroy_protection": True})

    result = run(server, server_id=42, project="shop", destroy_protection=True)

    assert result.changed
    assert api.requests("PATCH")[0][2] == {"project": "shop"}
    assert api.requests("POST")[0][2] == {"destroy_protection": True}


def test_create_check_mode_makes_no_writes(api, run):
    api.add("GET", SERVERS, listing())

    result = run(server, check_mode=True, hostname="web1", image="ubuntu24", package="cloudv-1")

    assert result.changed
    assert api.writes() == []


def test_create_requires_image_and_package(api, run):
    api.add("GET", SERVERS, listing())

    result = run(server, hostname="web1")

    assert result.failed
    assert "image" in result["msg"] and "package" in result["msg"]


def test_create_fails_when_provisioning_fails(api, run):
    api.add("GET", SERVERS, listing())
    api.add("POST", SERVERS, {"id": 42}, status=201)
    api.add("GET", SERVERS + "42/", detail(status="failed"))

    result = run(server, hostname="web1", image="ubuntu24", package="cloudv-1")

    assert result.failed
    assert result.changed
    assert "failed" in result["msg"]


def test_create_without_wait_returns_id(api, run):
    api.add("GET", SERVERS, listing())
    api.add("POST", SERVERS, {"id": 42}, status=201)

    result = run(server, hostname="web1", image="ubuntu24", package="cloudv-1", wait=False)

    assert result.changed
    assert result["server"] == {"id": 42}


def test_unknown_server_id_fails(api, run):
    api.add("GET", SERVERS + "9/", status=404)

    result = run(server, server_id=9, project="x")

    assert result.failed


def test_absent_deletes_and_waits_until_gone(api, run):
    api.add("GET", SERVERS, listing({"id": 42, "hostname": "web1"}))
    api.add("GET", SERVERS + "42/", detail())
    api.add("GET", SERVERS + "42/", detail(status="terminating"))
    api.add("GET", SERVERS + "42/", status=404)
    api.add("DELETE", SERVERS + "42/", status=204)

    result = run(server, state="absent", hostname="web1")

    assert result.changed
    assert [c[0] for c in api.writes()] == ["DELETE"]


def test_absent_disables_destroy_protection_when_asked(api, run):
    api.add("GET", SERVERS + "42/", detail(destroy_protection=True))
    api.add("GET", SERVERS + "42/", status=404)
    api.add("POST", SERVERS + "42/destroy-protection/", {"destroy_protection": False})
    api.add("DELETE", SERVERS + "42/", status=204)

    result = run(server, state="absent", server_id=42, destroy_protection=False)

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [
        ("POST", SERVERS + "42/destroy-protection/"), ("DELETE", SERVERS + "42/")]


def test_absent_missing_server_is_ok(api, run):
    api.add("GET", SERVERS, listing())

    result = run(server, state="absent", hostname="web1")

    assert not result.failed
    assert not result.changed


def test_absent_fails_when_server_outlives_timeout(api, run):
    api.add("GET", SERVERS + "42/", detail())
    api.add("DELETE", SERVERS + "42/", status=204)

    result = run(server, state="absent", server_id=42, timeout=0)

    assert result.failed
    assert result.changed
    assert "not deleted in time" in result["msg"]


def test_protected_create_requires_wait_before_writes(api, run):
    api.add("GET", SERVERS, listing())

    for check_mode in (False, True):
        result = run(server, check_mode=check_mode, hostname="web1.example.com", image="ubuntu24",
                     package="cloudv-1", wait=False, destroy_protection=True)

        assert result.failed
        assert "requires wait=true" in result["msg"]
        assert api.writes() == []


def test_protected_create_enables_protection_after_provisioning(api, run):
    api.add("GET", SERVERS, listing())
    api.add("POST", SERVERS, {"id": 42}, status=201)
    api.add("GET", SERVERS + "42/", detail())
    api.add("POST", SERVERS + "42/destroy-protection/", {"destroy_protection": True})

    result = run(server, hostname="web1.example.com", image="ubuntu24", package="cloudv-1", destroy_protection=True)

    assert not result.failed
    assert result["server"]["destroy_protection"] is True
    assert api.writes()[-1] == ("POST", SERVERS + "42/destroy-protection/", {"destroy_protection": True})


def test_already_deleting_server_waits_without_writes(api, run):
    api.add("GET", SERVERS + "42/", detail(status="cancelling"))
    api.add("GET", SERVERS + "42/", status=404)

    result = run(server, server_id=42, state="absent")

    assert not result.failed
    assert not result.changed
    assert api.writes() == []


def test_already_deleting_server_timeout_does_not_claim_change(api, run):
    api.add("GET", SERVERS + "42/", detail(status="terminating"))

    result = run(server, server_id=42, state="absent", timeout=0)

    assert result.failed
    assert not result.changed
    assert api.writes() == []


def test_error_after_create_reports_change(api, run):
    api.add("GET", SERVERS, listing())
    api.add("POST", SERVERS, {"id": 42}, status=201)
    api.add("GET", SERVERS + "42/", detail())
    api.add("POST", SERVERS + "42/destroy-protection/", {"detail": "Could not enable protection."}, status=400)

    result = run(server, hostname="web1.example.com", image="ubuntu24", package="cloudv-1", destroy_protection=True)

    assert result.failed
    assert result.changed
    assert result["status_code"] == 400
