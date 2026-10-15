# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import ssh_key

KEYS = "/api/account/ssh-keys/"
KEY_A = "ssh-ed25519 AAAAkeyA alice@example.com"
KEY_B = "ssh-ed25519 AAAAkeyB bob@example.com"
KEY_C = "ssh-rsa AAAAkeyC"


def stored(key_id, key, alias=""):
    return {"id": key_id, "alias": alias, "fingerprint": "SHA256:%s" % key_id, "key": key}


def listing(*keys):
    return {"count": len(keys), "next": None, "previous": None, "results": list(keys)}


def test_adds_missing_key(api, run):
    api.add("GET", KEYS, listing(stored(1, KEY_B)))
    api.add("POST", KEYS, stored(2, KEY_A, "laptop"), status=201)

    result = run(ssh_key, ssh_pub_key=KEY_A, alias="laptop")

    assert not result.failed, result.result
    assert result.changed
    assert api.requests("POST")[0][2] == {"key": KEY_A, "alias": "laptop"}
    assert result["added_keys"] == [KEY_A]
    assert result["deleted_keys"] == []
    assert result["ssh_key"]["id"] == 2


def test_existing_key_with_other_comment_is_unchanged(api, run):
    api.add("GET", KEYS, {"count": 2, "next": "x", "previous": None, "results": [stored(1, KEY_B)]})
    api.add("GET", KEYS + "?page=2", {"count": 2, "next": None, "previous": "x",
                                      "results": [stored(2, "ssh-ed25519 AAAAkeyA old-comment")]})

    result = run(ssh_key, ssh_pub_key=KEY_A)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert result["ssh_key"]["id"] == 2
    assert result["added_keys"] == []


def test_alias_change_is_patched(api, run):
    api.add("GET", KEYS, listing(stored(1, KEY_A, "old")))
    api.add("PATCH", KEYS + "1/", stored(1, KEY_A, "laptop"))

    result = run(ssh_key, ssh_pub_key=KEY_A, alias="laptop")

    assert result.changed
    assert api.writes() == [("PATCH", KEYS + "1/", {"alias": "laptop"})]
    assert result["ssh_key"]["alias"] == "laptop"


def test_delete_others_keeps_only_listed_keys(api, run):
    api.add("GET", KEYS, listing(stored(1, KEY_A), stored(2, KEY_C)))
    api.add("POST", KEYS, stored(3, KEY_B), status=201)
    api.add("DELETE", KEYS + "2/", status=204)

    result = run(ssh_key, ssh_pub_keys=[KEY_A, KEY_B], delete_others=True)

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("POST", KEYS), ("DELETE", KEYS + "2/")]
    assert result["added_keys"] == [KEY_B]
    assert result["deleted_keys"] == [KEY_C]
    assert result["ssh_key"] == {}


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", KEYS, listing(stored(2, KEY_C)))

    result = run(ssh_key, check_mode=True, ssh_pub_keys=[KEY_A], delete_others=True)

    assert result.changed
    assert result["added_keys"] == [KEY_A]
    assert result["deleted_keys"] == [KEY_C]
    assert api.writes() == []


def test_absent_deletes_existing_key(api, run):
    api.add("GET", KEYS, listing(stored(1, KEY_A), stored(2, KEY_B)))
    api.add("DELETE", KEYS + "1/", status=204)

    result = run(ssh_key, state="absent", ssh_pub_key="ssh-ed25519 AAAAkeyA")

    assert result.changed
    assert [(c[0], c[1]) for c in api.writes()] == [("DELETE", KEYS + "1/")]
    assert result["deleted_keys"] == [KEY_A]
    assert result["ssh_key"]["id"] == 1


def test_absent_missing_key_is_unchanged(api, run):
    api.add("GET", KEYS, listing(stored(2, KEY_B)))

    result = run(ssh_key, state="absent", ssh_pub_key=KEY_A)

    assert not result.failed
    assert not result.changed
    assert result["ssh_key"] == {}


def test_delete_others_with_absent_fails(api, run):
    result = run(ssh_key, state="absent", ssh_pub_keys=[KEY_A], delete_others=True)

    assert result.failed
    assert api.calls == []


def test_single_and_list_are_mutually_exclusive(api, run):
    result = run(ssh_key, ssh_pub_key=KEY_A, ssh_pub_keys=[KEY_B])

    assert result.failed
    assert api.calls == []
