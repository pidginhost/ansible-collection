# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import json
import time
from urllib.parse import urlencode

from ansible.module_utils.basic import env_fallback
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import fetch_url

BASE_URL = "https://www.pidginhost.com"
TOKEN_ENV_VARS = ["PIDGINHOST_ACCESS_TOKEN", "PIDGINHOST_TOKEN"]
POLL_INTERVAL = 5
SERVERS = "/api/cloud/servers/"
CLUSTERS = "/api/kubernetes/clusters/"


def pidginhost_argument_spec(**options):
    spec = dict(
        token=dict(type="str", required=True, no_log=True, fallback=(env_fallback, TOKEN_ENV_VARS)),
        timeout=dict(type="int", default=300),
    )
    spec.update(options)
    return spec


def info_argument_spec(**options):
    # Info modules accepted a meaningless state option before 0.4.0.
    return pidginhost_argument_spec(
        state=dict(type="str", removed_in_version="1.0.0", removed_from_collection="pidginhost.cloud"),
        **options
    )


def drop_none(params):
    return dict((k, v) for k, v in params.items() if v is not None)


def ip_version(address):
    """Return 4 or 6 for a valid IP address, None otherwise."""
    try:
        return ipaddress.ip_address(to_text(address)).version
    except ValueError:
        return None


def plan_rules(existing, desired, match_fields, update_fields, purge):
    """Diff firewall-style rules.

    Rules match one to one on match_fields, compared as strings with None equal to "".
    Returns (rules to create, (rule id, changed fields) to patch, rules to delete).
    """
    def identity(rule):
        return tuple("" if rule.get(k) is None else str(rule[k]) for k in match_fields)

    unmatched = list(existing)
    create, patch = [], []
    for rule in desired:
        match = next((r for r in unmatched if identity(r) == identity(rule)), None)
        if match is None:
            create.append(drop_none(rule))
            continue
        unmatched.remove(match)
        changes = dict(
            (k, rule[k]) for k in update_fields if rule.get(k) is not None and rule[k] != match.get(k))
        if changes:
            patch.append((match["id"], changes))
    return create, patch, unmatched if purge else []


def _decode(raw):
    if not raw:
        return None
    text = to_text(raw, errors="surrogate_or_strict")
    try:
        return json.loads(text)
    except ValueError:
        return text


class PidginHostAPI(object):
    def __init__(self, module):
        self.module = module
        self.timeout = module.params["timeout"]
        self.changed = False
        self.headers = {
            "Authorization": "Token %s" % module.params["token"],
            "Accept": "application/json",
        }

    def request(self, method, path, body=None, query=None, allow_404=False, accept=None):
        url = BASE_URL + path
        if query:
            url += "?" + urlencode(query)
        headers = dict(self.headers)
        if accept:
            headers["Accept"] = accept
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"

        resp, info = fetch_url(self.module, url, data=data, headers=headers, method=method, timeout=self.timeout,
                               unredirected_headers=["Authorization"])
        status = info.get("status", -1)
        if status == -1:
            self.module.fail_json(changed=self.changed,
                                  msg="PidginHost API %s %s failed: %s" % (method, path, info.get("msg")))
        if allow_404 and status == 404:
            return None
        if 200 <= status < 300:
            if method in ("POST", "PATCH", "DELETE"):
                self.changed = True
            body = _decode(resp.read() if resp else None)
            return {} if body is None else body
        response = _decode(info.get("body"))
        self.module.fail_json(
            changed=self.changed,
            msg="PidginHost API %s %s returned HTTP %s: %s" % (method, path, status, response or info.get("msg")),
            status_code=status,
            response=response,
        )

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, body=None, **kwargs):
        return self.request("POST", path, body={} if body is None else body, **kwargs)

    def patch(self, path, body, **kwargs):
        return self.request("PATCH", path, body=body, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def list(self, path, **query):
        """Return every item of a list endpoint, following pagination."""
        data = self.get(path, query=query)
        if isinstance(data, list):
            return data
        items = list(data.get("results", []))
        page = 1
        while data.get("next"):
            page += 1
            # Page numbers instead of the absolute "next" URL keep the token on BASE_URL.
            data = self.get(path, query=dict(query, page=page))
            items.extend(data.get("results", []))
        return items

    def wait_for(self, fetch, ready):
        """Poll fetch() until ready(result) holds. Returns the result, or None on timeout."""
        deadline = time.monotonic() + self.timeout
        while True:
            obj = fetch()
            if ready(obj):
                return obj
            if time.monotonic() >= deadline:
                return None
            time.sleep(POLL_INTERVAL)

    def find_one(self, items, kind, **match):
        found = [i for i in items if all(i.get(k) == v for k, v in match.items())]
        if len(found) > 1:
            self.module.fail_json(
                msg="Found %d %s matching %s (ids: %s); use an id instead."
                    % (len(found), kind, match, ", ".join(str(i.get("id")) for i in found))
            )
        return found[0] if found else None

    def find_ip(self, address):
        """Return (version, owned public IP or None) for an address."""
        version = ip_version(address)
        if not version:
            self.module.fail_json(msg="%s is not a valid IP address." % address)
        wanted = ipaddress.ip_address(to_text(address))
        for item in self.list("/api/cloud/ipv%d/" % version):
            if ipaddress.ip_address(to_text(item["address"])) == wanted:
                return version, item
        return version, None

    def find_server(self, server_id=None, hostname=None):
        """Return the server detail by id or unique hostname, or None if absent."""
        if not server_id:
            match = self.find_one(self.list(SERVERS), "servers", hostname=hostname)
            if not match:
                return None
            server_id = match["id"]
        return self.get("%s%s/" % (SERVERS, server_id), allow_404=True)

    def require_server(self, server_id=None, hostname=None):
        server = self.find_server(server_id, hostname)
        if not server:
            self.module.fail_json(msg="Server %s not found." % (server_id or hostname))
        return server

    def find_cluster(self, cluster_id=None, name=None):
        """Return a Kubernetes cluster by id or unique name, or None if absent."""
        if cluster_id:
            return self.get("%s%s/" % (CLUSTERS, cluster_id), allow_404=True)
        return self.find_one(self.list(CLUSTERS), "Kubernetes clusters", name=name)

    def require_cluster(self, cluster_id=None, name=None):
        cluster = self.find_cluster(cluster_id, name)
        if not cluster:
            self.module.fail_json(msg="Kubernetes cluster %s not found." % (cluster_id or name))
        return cluster
