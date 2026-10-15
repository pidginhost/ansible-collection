# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

# Only this stub collection is visible to the subprocess. No real module or API client is copied.
ACTION = '''
import json
import os
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        name = self._task.action.rsplit(".", 1)[-1]
        args = dict(self._task.args)
        args.pop("token", None)
        with open(os.environ["CLEANUP_CALLS"], "a") as stream:
            stream.write(json.dumps([name, args]) + "\\n")
        with open(os.environ["CLEANUP_FIXTURES"]) as stream:
            fixtures = json.load(stream)
        if name in fixtures["failures"]:
            return {"failed": True, "msg": "Injected offline failure"}
        if name == "ips_info":
            return {"changed": False, "ips": fixtures["ips"].get(args["ip_type"], [])}
        fields = {"kubernetes_clusters_info": "clusters", "floating_ips_info": "floating_ips",
                  "servers_info": "servers", "volumes_info": "volumes", "buckets_info": "buckets",
                  "firewalls_info": "firewalls", "private_networks_info": "private_networks",
                  "ssh_keys_info": "ssh_keys", "dns_records_info": "records"}
        if name in fields:
            field = fields[name]
            return {"changed": False, field: fixtures.get(field, [])}
        return {"changed": True}
'''


@pytest.fixture
def cleanup_run(tmp_path):
    collection_root = tmp_path / "collections"
    collection = collection_root / "ansible_collections" / "pidginhost" / "cloud"
    actions = collection / "plugins" / "action"
    modules = collection / "plugins" / "modules"
    actions.mkdir(parents=True)
    modules.mkdir(parents=True)
    (collection / "meta").mkdir()
    shutil.copyfile(str(ROOT / "meta/runtime.yml"), str(collection / "meta/runtime.yml"))
    names = yaml.safe_load((ROOT / "meta/runtime.yml").read_text())["action_groups"]["all"]
    for name in names:
        (actions / (name + ".py")).write_text(ACTION)
        (modules / (name + ".py")).write_text("# Offline placeholder.\n")
    config = tmp_path / "ansible.cfg"
    config.write_text("[defaults]\nretry_files_enabled = False\n")
    calls_path = tmp_path / "calls.jsonl"
    fixtures_path = tmp_path / "fixtures.json"
    playbook = tmp_path / "cleanup.yml"
    shutil.copyfile(str(ROOT / "tests/integration/cleanup.yml"), str(playbook))

    def run(fixtures, domain=""):
        fixtures = dict({"failures": [], "ips": {}}, **fixtures)
        fixtures_path.write_text(json.dumps(fixtures))
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(tmp_path),
            "LC_ALL": "C.UTF-8",
            "PYTHONPATH": os.pathsep.join(sys.path),
            "ANSIBLE_CONFIG": str(config),
            "ANSIBLE_COLLECTIONS_PATH": str(collection_root),
            "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH": "false",
            "ANSIBLE_NOCOLOR": "1",
            "CLEANUP_CALLS": str(calls_path),
            "CLEANUP_FIXTURES": str(fixtures_path),
        }
        variables = {"pidginhost_token": "test-token", "pidginhost_dns_domain": domain}
        command = [sys.executable, "-m", "ansible.cli.playbook", str(playbook), "-i", "localhost,",
                   "-e", json.dumps(variables)]
        result = subprocess.run(command, cwd=str(tmp_path), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True, timeout=60, check=False)
        calls = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
        return result, calls

    return run


def test_cleanup_releases_unbound_ips_but_keeps_pending_attachments(cleanup_run):
    result, calls = cleanup_run({"ips": {
        "ipv4": [{"address": "192.0.2.10", "attached": False, "server_id": None},
                 {"address": "192.0.2.11", "attached": False, "server_id": 42},
                 {"address": "192.0.2.12", "attached": True, "server_id": 43}],
        "ipv6": [{"address": "2001:db8::10", "attached": False, "server_id": None}],
    }})

    assert result.returncode == 0, result.stdout
    assert {args["address"] for name, args in calls if name == "ip"} == {"192.0.2.10", "2001:db8::10"}


@pytest.mark.parametrize("failed_module", ["kubernetes_clusters_info", "kubernetes_cluster"])
def test_cleanup_continues_after_failure_and_still_fails(cleanup_run, failed_module):
    result, calls = cleanup_run({
        "failures": [failed_module],
        "clusters": [{"id": 1, "name": "ansible-ci-cluster"}],
        "buckets": [{"name": "ansible-ci-bucket"}, {"name": "keep-bucket"}],
    })

    assert result.returncode != 0
    assert "Cleanup failed for: clusters" in result.stdout
    assert [args["name"] for name, args in calls if name == "bucket"] == ["ansible-ci-bucket"]


def test_cleanup_removes_only_test_dns_records_and_normalizes_caa(cleanup_run):
    result, calls = cleanup_run({"records": [
        {"name": "ansible-ci-test.example.com.", "type": "A"},
        {"name": "ansible-ci-test.example.com.", "type": "TYPE257"},
        {"name": "www.example.com.", "type": "A"},
    ]}, domain="example.com")

    assert result.returncode == 0, result.stdout
    assert {(args["name"], args["type"]) for name, args in calls if name == "dns_record"} == {
        ("ansible-ci-test.example.com.", "A"), ("ansible-ci-test.example.com.", "CAA")}


def test_cleanup_skips_dns_without_a_zone(cleanup_run):
    result, calls = cleanup_run({})

    assert result.returncode == 0, result.stdout
    assert not any(name.startswith("dns_") for name, args in calls)
