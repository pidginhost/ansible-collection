# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import bucket_credentials

BUCKETS = "/api/cloud/buckets/"
BUCKET = {"id": 5, "name": "media", "full_name": "c1-media", "status": "active"}
CREDS = {"bucket": "c1-media", "endpoint": "https://s3.example.com", "region": "default",
         "access_key": "AK", "secret_key": "SK"}


def test_reveals_credentials_without_change(api, run):
    api.add("GET", BUCKETS, [BUCKET])
    api.add("POST", BUCKETS + "5/credentials/reveal/", CREDS)

    result = run(bucket_credentials, name="media")

    assert not result.failed, result.result
    assert not result.changed
    assert result["credentials"] == CREDS


def test_reveal_runs_in_check_mode(api, run):
    api.add("GET", BUCKETS, [BUCKET])
    api.add("POST", BUCKETS + "5/credentials/reveal/", CREDS)

    result = run(bucket_credentials, check_mode=True, name="media")

    assert not result.changed
    assert result["credentials"] == CREDS


def test_rotates_credentials(api, run):
    api.add("GET", BUCKETS, [BUCKET])
    api.add("POST", BUCKETS + "5/credentials/rotate/", dict(CREDS, access_key="AK2", secret_key="SK2"))

    result = run(bucket_credentials, name="media", rotate=True)

    assert result.changed
    assert result["credentials"]["access_key"] == "AK2"
    assert [c[1] for c in api.writes()] == [BUCKETS + "5/credentials/rotate/"]


def test_rotate_check_mode_makes_no_calls(api, run):
    api.add("GET", BUCKETS, [BUCKET])

    result = run(bucket_credentials, check_mode=True, name="media", rotate=True)

    assert result.changed
    assert api.writes() == []


def test_missing_bucket_fails(api, run):
    api.add("GET", BUCKETS, [])

    result = run(bucket_credentials, name="media")

    assert result.failed
    assert "media" in result["msg"]
