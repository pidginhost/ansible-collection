# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import images_info

IMAGES = "/api/cloud/images/"


def test_lists_every_page_of_images(api, run):
    api.add("GET", IMAGES, {"count": 2, "next": "x", "previous": None, "results": [{"slug": "ubuntu24"}]})
    api.add("GET", IMAGES + "?page=2", {"count": 2, "next": None, "previous": "x", "results": [{"slug": "debian12"}]})

    result = run(images_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["images"] == [{"slug": "ubuntu24"}, {"slug": "debian12"}]


def test_empty_catalog_is_not_an_error(api, run):
    api.add("GET", IMAGES, {"count": 0, "next": None, "previous": None, "results": []})

    result = run(images_info)

    assert not result.failed
    assert result["images"] == []


def test_api_error_fails(api, run):
    api.add("GET", IMAGES, {"detail": "Invalid token."}, status=401)

    result = run(images_info)

    assert result.failed
