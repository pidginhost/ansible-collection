# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import volumes_info

VOLUMES = [{"id": 7, "alias": "data", "size": 10, "attached": True, "server": "web1"}]


def test_lists_all_volumes(api, run):
    api.add("GET", "/api/cloud/volumes/", VOLUMES)

    result = run(volumes_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["volumes"] == VOLUMES


def test_lists_volumes_of_one_server(api, run):
    api.add("GET", "/api/cloud/servers/42/volumes/", VOLUMES)

    result = run(volumes_info, server_id=42)

    assert result["volumes"] == VOLUMES


def test_unknown_server_fails(api, run):
    api.add("GET", "/api/cloud/servers/9/volumes/", {"detail": "Not found."}, status=404)

    result = run(volumes_info, server_id=9)

    assert result.failed
