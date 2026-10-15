# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import private_networks_info

NETS = "/api/cloud/private-networks/"


def page(items, more=False):
    return {"count": 2, "next": "next-page" if more else None, "previous": None, "results": items}


def test_returns_every_page(api, run):
    api.add("GET", NETS, page([{"id": 1}], more=True))
    api.add("GET", NETS + "?page=2", page([{"id": 2}]))

    result = run(private_networks_info, check_mode=True)

    assert not result.failed, result.result
    assert not result.changed
    assert result["private_networks"] == [{"id": 1}, {"id": 2}]


def test_api_error_fails(api, run):
    api.add("GET", NETS, {"detail": "Invalid token."}, status=401)

    result = run(private_networks_info)

    assert result.failed
