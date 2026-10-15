# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import volumes_products_info

PRODUCTS = "/api/cloud/storage-products/"


def test_lists_every_page_of_products(api, run):
    api.add("GET", PRODUCTS, {"count": 2, "next": "x", "previous": None, "results": [{"slug": "fast-storage"}]})
    api.add("GET", PRODUCTS + "?page=2", {"count": 2, "next": None, "previous": "x", "results": [{"slug": "hdd"}]})

    result = run(volumes_products_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["volumes"] == [{"slug": "fast-storage"}, {"slug": "hdd"}]


def test_api_error_fails(api, run):
    api.add("GET", PRODUCTS, {"detail": "Invalid token."}, status=401)

    result = run(volumes_products_info)

    assert result.failed
