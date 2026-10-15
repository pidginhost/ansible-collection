# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import dns_zones_info

ZONES = "/api/freedns/dns/"


def test_lists_zones(api, run):
    zones = [{"domain": "example.com", "active": True, "source": "internal"}]
    api.add("GET", ZONES, zones)

    result = run(dns_zones_info, check_mode=True)

    assert not result.failed, result.result
    assert not result.changed
    assert result["zones"] == zones


def test_api_error_fails(api, run):
    api.add("GET", ZONES, {"detail": "Invalid token."}, status=401)

    result = run(dns_zones_info)

    assert result.failed
