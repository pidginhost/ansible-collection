# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import firewalls_info

SETS = "/api/cloud/firewall-rules-set/"


def test_lists_rules_sets_with_rules(api, run):
    sets = [{"id": 5, "name": "web", "status": "validated", "read_only": False, "rules": [{"id": 1}]}]
    api.add("GET", SETS, sets)

    result = run(firewalls_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["firewalls"] == sets


def test_api_error_fails(api, run):
    api.add("GET", SETS, {"detail": "Invalid token."}, status=401)

    result = run(firewalls_info)

    assert result.failed
