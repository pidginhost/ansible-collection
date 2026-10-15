# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import ips_info

IPV4 = "/api/cloud/ipv4/"
IPV6 = "/api/cloud/ipv6/"


def page(items, more=False):
    return {"count": 3, "next": "https://www.pidginhost.com/api/cloud/ipv4/?page=2" if more else None,
            "previous": None, "results": items}


def test_returns_every_ipv4_page(api, run):
    api.add("GET", IPV4, page([{"id": 1}, {"id": 2}], more=True))
    api.add("GET", IPV4 + "?page=2", page([{"id": 3}]))

    result = run(ips_info, ip_type="ipv4", state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert [i["id"] for i in result["ips"]] == [1, 2, 3]


def test_returns_ipv6_in_check_mode(api, run):
    api.add("GET", IPV6, page([{"id": 9}]))

    result = run(ips_info, check_mode=True, ip_type="ipv6")

    assert not result.changed
    assert result["ips"] == [{"id": 9}]


def test_api_error_fails(api, run):
    api.add("GET", IPV4, {"detail": "Invalid token."}, status=401)

    result = run(ips_info, ip_type="ipv4")

    assert result.failed
    assert "401" in result["msg"]
