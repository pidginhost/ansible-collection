# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import sys
from contextlib import contextmanager

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from ansible.plugins.loader import init_plugin_loader

# Plain pytest runs need the collection loader before anything imports ansible_collections;
# ansible-test units installs it already.
if not any(type(f).__name__ == "_AnsibleCollectionFinder" for f in sys.meta_path):
    init_plugin_loader([os.path.abspath(os.path.join(os.path.dirname(__file__), *[os.pardir] * 5))])

try:
    from ansible.module_utils.testing import patch_module_args
except ImportError:  # ansible-core < 2.19
    @contextmanager
    def patch_module_args(args):
        old = basic._ANSIBLE_ARGS
        basic._ANSIBLE_ARGS = to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args}))
        try:
            yield
        finally:
            basic._ANSIBLE_ARGS = old

COMMON = "ansible_collections.pidginhost.cloud.plugins.module_utils.common"


class ModuleExit(Exception):
    def __init__(self, failed, result):
        super(ModuleExit, self).__init__(result.get("msg"))
        self.failed = failed
        self.result = result

    def __getitem__(self, key):
        return self.result[key]

    @property
    def changed(self):
        return self.result.get("changed", False)


class FakeResponse:
    def __init__(self, raw):
        self.raw = raw

    def read(self):
        return self.raw


class FakeAPI:
    """Scripted PidginHost API.

    Responses for a route are served in the order they were added; the last
    one repeats. Any call without a route fails the test.
    """

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, method, path, body=None, status=200):
        self.routes.setdefault((method, path), []).append((status, body))
        return self

    def __call__(self, module, url, data=None, headers=None, method=None, timeout=None, **kwargs):
        assert url.startswith("https://www.pidginhost.com/"), url
        assert headers["Authorization"] == "Token test-token"
        path = url[len("https://www.pidginhost.com"):]
        self.calls.append((method, path, json.loads(data) if data else None))
        queue = self.routes.get((method, path))
        if not queue:
            raise AssertionError("unexpected API call: %s %s" % (method, path))
        status, body = queue.pop(0) if len(queue) > 1 else queue[0]
        if status == -1:
            return None, {"status": -1, "msg": "Connection refused"}
        raw = b"" if body is None else to_bytes(json.dumps(body))
        if 200 <= status < 300:
            return FakeResponse(raw), {"status": status}
        return None, {"status": status, "body": raw, "msg": "HTTP Error %s" % status}

    def requests(self, method=None, path=None):
        return [
            (m, p, d) for m, p, d in self.calls
            if (method is None or m == method) and (path is None or p == path)
        ]

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(COMMON + ".fetch_url", fake)
    monkeypatch.setattr(COMMON + ".time.sleep", lambda seconds: None)
    return fake


@pytest.fixture
def run(monkeypatch):
    def exit_json(self, **kwargs):
        raise ModuleExit(False, kwargs)

    def fail_json(self, msg, **kwargs):
        kwargs["msg"] = msg
        raise ModuleExit(True, kwargs)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)

    def _run(module, check_mode=False, **args):
        args.setdefault("token", "test-token")
        if check_mode:
            args["_ansible_check_mode"] = True
        with patch_module_args(args):
            with pytest.raises(ModuleExit) as exc:
                module.main()
        return exc.value

    return _run


@pytest.fixture
def make_module(run):
    """Build a bare AnsibleModule with the common PidginHost options."""
    from ansible_collections.pidginhost.cloud.plugins.module_utils.common import pidginhost_argument_spec

    def _make(**args):
        args.setdefault("token", "test-token")
        with patch_module_args(args):
            return basic.AnsibleModule(argument_spec=pidginhost_argument_spec())

    return _make
