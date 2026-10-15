# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import buckets_info

BUCKETS = "/api/cloud/buckets/"


def test_lists_buckets(api, run):
    buckets = [{"id": 5, "name": "media", "full_name": "c1-media", "quota_gb": 10, "status": "active"}]
    api.add("GET", BUCKETS, buckets)

    result = run(buckets_info, check_mode=True)

    assert not result.failed, result.result
    assert not result.changed
    assert result["buckets"] == buckets


def test_api_error_fails(api, run):
    api.add("GET", BUCKETS, {"detail": "Invalid token."}, status=401)

    result = run(buckets_info)

    assert result.failed
