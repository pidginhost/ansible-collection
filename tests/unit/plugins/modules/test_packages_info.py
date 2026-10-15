# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import packages_info

PACKAGES = "/api/cloud/server-packages/"


def test_lists_every_page_of_packages(api, run):
    api.add("GET", PACKAGES, {"count": 2, "next": "x", "previous": None, "results": [{"slug": "cloudv-1"}]})
    api.add("GET", PACKAGES + "?page=2", {"count": 2, "next": None, "previous": "x", "results": [{"slug": "cloudv-2"}]})

    result = run(packages_info, check_mode=True, state="present")

    assert not result.failed, result.result
    assert not result.changed
    assert result["packages"] == [{"slug": "cloudv-1"}, {"slug": "cloudv-2"}]


def test_filters_by_generation(api, run):
    api.add("GET", PACKAGES + "?generation=gen2", {"count": 2, "next": "x", "previous": None,
                                                   "results": [{"slug": "cloudv-1"}]})
    api.add("GET", PACKAGES + "?generation=gen2&page=2", {"count": 2, "next": None, "previous": "x",
                                                          "results": [{"slug": "cloudv-2"}]})

    result = run(packages_info, generation="gen2")

    assert not result.failed, result.result
    assert [p["slug"] for p in result["packages"]] == ["cloudv-1", "cloudv-2"]


def test_api_error_fails(api, run):
    api.add("GET", PACKAGES + "?generation=nope", {"generation": ["Unknown generation."]}, status=400)

    result = run(packages_info, generation="nope")

    assert result.failed
