# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import ssh_keys_info

KEYS = "/api/account/ssh-keys/"


def test_lists_every_page(api, run):
    api.add("GET", KEYS, {"count": 2, "next": "x", "previous": None, "results": [{"id": 1}]})
    api.add("GET", KEYS + "?page=2", {"count": 2, "next": None, "previous": "x", "results": [{"id": 2}]})

    result = run(ssh_keys_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["ssh_keys"] == [{"id": 1}, {"id": 2}]


def test_api_error_fails(api, run):
    api.add("GET", KEYS, status=-1)

    result = run(ssh_keys_info)

    assert result.failed
