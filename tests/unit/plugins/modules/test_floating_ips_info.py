# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import floating_ips_info

FIP4 = "/api/cloud/floating-ipv4/"
FIP6 = "/api/cloud/floating-ipv6/"


def page(items, more=False):
    return {"count": 9, "next": "next-page" if more else None, "previous": None, "results": items}


def test_returns_every_page_of_both_versions(api, run):
    api.add("GET", FIP4, page([{"id": 1}], more=True))
    api.add("GET", FIP4 + "?page=2", page([{"id": 2}]))
    api.add("GET", FIP6, page([{"id": 3}]))

    result = run(floating_ips_info)

    assert not result.failed, result.result
    assert not result.changed
    assert result["floating_ips"] == [{"id": 1, "version": 4}, {"id": 2, "version": 4}, {"id": 3, "version": 6}]


def test_filters_by_version_in_check_mode(api, run):
    api.add("GET", FIP6, page([{"id": 3}]))

    result = run(floating_ips_info, check_mode=True, version=6)

    assert result["floating_ips"] == [{"id": 3, "version": 6}]
    assert api.requests("GET", FIP4) == []


def test_api_error_fails(api, run):
    api.add("GET", FIP4, status=500)

    result = run(floating_ips_info, version=4)

    assert result.failed
