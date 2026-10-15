# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import generations_info

GENERATIONS = "/api/cloud/generations/"


def test_lists_generations(api, run):
    gens = [{"slug": "gen1", "name": "Gen 1", "is_default": True}, {"slug": "gen2", "name": "Gen 2"}]
    api.add("GET", GENERATIONS, gens)

    result = run(generations_info, check_mode=True)

    assert not result.failed, result.result
    assert not result.changed
    assert result["generations"] == gens


def test_api_error_fails(api, run):
    api.add("GET", GENERATIONS, {"detail": "Invalid token."}, status=401)

    result = run(generations_info)

    assert result.failed
