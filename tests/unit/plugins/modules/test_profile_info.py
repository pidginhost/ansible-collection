# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import profile_info

PROFILE = "/api/account/profile"


def test_returns_profile(api, run):
    profile = {"first_name": "Jane", "last_name": "Doe", "funds": "10.0000", "phone": "+40000000000"}
    api.add("GET", PROFILE, profile)

    result = run(profile_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["account"] == profile


def test_api_error_fails(api, run):
    api.add("GET", PROFILE, {"detail": "Invalid token."}, status=401)

    result = run(profile_info)

    assert result.failed
    assert result["status_code"] == 401
