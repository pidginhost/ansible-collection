# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import bucket

BUCKETS = "/api/cloud/buckets/"


def bkt(**kw):
    base = {"id": 5, "name": "media", "full_name": "c1-media", "quota_gb": 10, "public_read": False,
            "status": "active", "used_bytes": 0, "object_count": 0}
    base.update(kw)
    return base


def test_creates_bucket_and_waits_until_active(api, run):
    api.add("GET", BUCKETS, [bkt(id=4, name="logs", full_name="c1-logs")])
    api.add("POST", BUCKETS, bkt(status="pending"), status=202)
    api.add("GET", BUCKETS + "5/", bkt(status="provisioning"))
    api.add("GET", BUCKETS + "5/", bkt())

    result = run(bucket, name="media", quota_gb=10, public_read=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["bucket"]["status"] == "active"
    assert api.writes() == [("POST", BUCKETS, {"name": "media", "quota_gb": 10, "public_read": True})]


def test_create_without_wait_returns_pending_bucket(api, run):
    api.add("GET", BUCKETS, [])
    api.add("POST", BUCKETS, bkt(status="pending"), status=202)

    result = run(bucket, name="media", quota_gb=10, wait=False)

    assert result.changed
    assert result["bucket"]["status"] == "pending"
    assert api.writes() == [("POST", BUCKETS, {"name": "media", "quota_gb": 10})]


def test_existing_bucket_matched_by_name_is_unchanged(api, run):
    api.add("GET", BUCKETS, [bkt()])

    result = run(bucket, name="media", quota_gb=10, public_read=False)

    assert not result.failed, result.result
    assert not result.changed
    assert result["bucket"]["id"] == 5
    assert api.writes() == []


def test_resizes_and_changes_visibility(api, run):
    api.add("GET", BUCKETS, [bkt()])
    api.add("POST", BUCKETS + "5/resize/", bkt(quota_gb=20, status="upgrading"))
    api.add("POST", BUCKETS + "5/visibility/", bkt(quota_gb=20, public_read=True, status="upgrading"))
    api.add("GET", BUCKETS + "5/", bkt(quota_gb=20, public_read=True))

    result = run(bucket, name="media", quota_gb=20, public_read=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["bucket"]["status"] == "active"
    assert api.writes() == [
        ("POST", BUCKETS + "5/resize/", {"quota_gb": 20}),
        ("POST", BUCKETS + "5/visibility/", {"public_read": True}),
    ]


def test_create_check_mode_makes_no_writes(api, run):
    api.add("GET", BUCKETS, [])

    result = run(bucket, check_mode=True, name="media", quota_gb=10)

    assert result.changed
    assert api.writes() == []


def test_update_check_mode_makes_no_writes(api, run):
    api.add("GET", BUCKETS, [bkt()])

    result = run(bucket, check_mode=True, name="media", public_read=True)

    assert result.changed
    assert api.writes() == []


def test_create_requires_quota(api, run):
    api.add("GET", BUCKETS, [])

    result = run(bucket, name="media")

    assert result.failed
    assert "quota_gb" in result["msg"]


def test_create_fails_when_provisioning_fails(api, run):
    api.add("GET", BUCKETS, [])
    api.add("POST", BUCKETS, bkt(status="pending"), status=202)
    api.add("GET", BUCKETS + "5/", bkt(status="failed"))

    result = run(bucket, name="media", quota_gb=10)

    assert result.failed
    assert result.changed
    assert "failed" in result["msg"]


def test_bucket_being_deleted_cannot_be_reused(api, run):
    api.add("GET", BUCKETS, [bkt(status="cancelling")])

    result = run(bucket, name="media", quota_gb=10)

    assert result.failed
    assert api.writes() == []


def test_absent_deletes_and_waits_until_gone(api, run):
    api.add("GET", BUCKETS, [bkt()])
    api.add("GET", BUCKETS, [bkt(status="cancelling")])
    api.add("GET", BUCKETS, [])
    api.add("DELETE", BUCKETS + "5/", {"id": 5, "status": "cancelling"}, status=202)

    result = run(bucket, state="absent", name="media")

    assert not result.failed, result.result
    assert result.changed
    assert result["bucket"]["id"] == 5
    assert api.writes() == [("DELETE", BUCKETS + "5/", None)]


def test_absent_fails_when_delete_fails(api, run):
    api.add("GET", BUCKETS, [bkt()])
    api.add("GET", BUCKETS, [bkt(status="failed")])
    api.add("DELETE", BUCKETS + "5/", {"id": 5, "status": "cancelling"}, status=202)

    result = run(bucket, state="absent", name="media")

    assert result.failed
    assert result.changed


def test_absent_bucket_already_cancelling_is_unchanged(api, run):
    api.add("GET", BUCKETS, [bkt(status="cancelling")])

    result = run(bucket, state="absent", name="media", wait=False)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", BUCKETS, [bkt()])

    result = run(bucket, check_mode=True, state="absent", name="media")

    assert result.changed
    assert api.writes() == []


def test_absent_missing_bucket_is_ok(api, run):
    api.add("GET", BUCKETS, [bkt(name="logs", full_name="c1-logs")])

    result = run(bucket, state="absent", name="media")

    assert not result.failed
    assert not result.changed


def test_waits_for_existing_provisioning_bucket_without_writes(api, run):
    api.add("GET", BUCKETS, [bkt(status="provisioning")])
    api.add("GET", BUCKETS + "5/", bkt())

    result = run(bucket, name="media", quota_gb=10)

    assert not result.failed
    assert not result.changed
    assert result["bucket"]["status"] == "active"
    assert api.writes() == []


def test_existing_bucket_wait_timeout_does_not_claim_change(api, run):
    api.add("GET", BUCKETS, [bkt(status="upgrading")])
    api.add("GET", BUCKETS + "5/", bkt(status="upgrading"))

    result = run(bucket, name="media", quota_gb=10, timeout=0)

    assert result.failed
    assert not result.changed
    assert api.writes() == []


def test_failed_existing_bucket_is_not_reported_ready(api, run):
    api.add("GET", BUCKETS, [bkt(status="failed")])
    api.add("GET", BUCKETS + "5/", bkt(status="failed"))

    result = run(bucket, name="media")

    assert result.failed
    assert not result.changed


def test_deletion_timeout_fails(api, run):
    api.add("GET", BUCKETS, [bkt(status="cancelling")])

    result = run(bucket, name="media", state="absent", timeout=0)

    assert result.failed
    assert not result.changed
    assert "not deleted in time" in result["msg"]


def test_waits_for_provisioning_before_resizing_existing_bucket(api, run):
    api.add("GET", BUCKETS, [bkt(status="provisioning")])
    api.add("GET", BUCKETS + "5/", bkt(status="provisioning"))
    api.add("GET", BUCKETS + "5/", bkt())
    api.add("POST", BUCKETS + "5/resize/", bkt(quota_gb=20))

    result = run(bucket, name="media", quota_gb=20)

    assert not result.failed
    assert result.changed
    assert api.calls[-1] == ("POST", BUCKETS + "5/resize/", {"quota_gb": 20})
    assert len(api.requests("GET", BUCKETS + "5/")) == 2
