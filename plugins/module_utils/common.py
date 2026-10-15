# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import json
import time
from collections import Counter
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

from ansible.module_utils.basic import env_fallback
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import fetch_url

BASE_URL = "https://www.pidginhost.com"
TOKEN_ENV_VARS = ["PIDGINHOST_ACCESS_TOKEN", "PIDGINHOST_TOKEN"]
POLL_INTERVAL = 5
RESUBMIT_DELAY = 30
# How the API words a refusal that ran nothing because another operation held the server.
BUSY = "another server operation is in progress"
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


def fqdn(name):
    """Lower case ASCII form of a domain name, without the trailing dot."""
    name = name.strip().rstrip(".").lower()
    try:
        return name.encode("idna").decode("ascii")
    except UnicodeError:
        return name


def dns_record_name(name, zone):
    """Fully qualified record name with a trailing dot, as the API returns it."""
    name = name.strip().lower()
    if name in ("", "@"):
        return zone + "."
    if name.endswith("."):
        return fqdn(name) + "."
    name = fqdn(name)
    if name == zone or name.endswith("." + zone):
        return name + "."
    return "%s.%s." % (name, zone)


def _retry_after(info):
    """Seconds to wait before retrying a throttled request, from the Retry-After header."""
    value = info.get("retry-after", POLL_INTERVAL)
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(date.timestamp() - time.time(), 1)
        except (TypeError, ValueError, OverflowError):
            return POLL_INTERVAL


def _decode(raw):
    if not raw:
        return None
    text = to_text(raw, errors="surrogate_or_strict")
    try:
        return json.loads(text)
    except ValueError:
        return text


class PidginHostAPI(object):
    def __init__(self, module, sensitive=False):
        self.module = module
        self.sensitive = sensitive
        self.timeout = module.params["timeout"]
        self.changed = False
        self.status = None
        self._wait_deadline = None
        self.headers = {
            "Authorization": "Token %s" % module.params["token"],
            "Accept": "application/json",
        }

    def request(self, method, path, body=None, query=None, allow_404=False, accept=None, allow_status=(),
                sensitive=False, read_only=False):
        """Send one API request and return the decoded body.

        A status in allow_status returns the decoded error body instead of failing; self.status holds the
        status of the last response either way.
        """
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

        deadline = time.monotonic() + self.timeout
        if self._wait_deadline is not None:
            deadline = min(deadline, self._wait_deadline)
        while True:
            resp, info = fetch_url(self.module, url, data=data, headers=headers, method=method,
                                   timeout=max(0, deadline - time.monotonic()), unredirected_headers=["Authorization"])
            status = self.status = info.get("status", -1)
            if status != 429:
                break
            # A throttled request was not processed, so any method can be sent again once the API allows it.
            delay = _retry_after(info)
            if delay >= deadline - time.monotonic():
                break
            time.sleep(delay)
            if time.monotonic() >= deadline:
                break
        sensitive = sensitive or self.sensitive
        if status == -1:
            self.module.fail_json(changed=self.changed,
                                  msg="PidginHost API %s %s failed: %s" % (
                                      method, path, "transport error" if sensitive else info.get("msg")))
        if allow_404 and status == 404:
            return None
        if 200 <= status < 300:
            if method in ("POST", "PATCH", "DELETE") and not read_only:
                self.changed = True
            body = _decode(resp.read() if resp else None)
            return {} if body is None else body
        if sensitive:
            self.module.fail_json(
                changed=self.changed,
                msg="PidginHost API %s %s returned HTTP %s; response omitted because it may contain sensitive data."
                    % (method, path, status),
                status_code=status,
            )
        response = _decode(info.get("body"))
        if status in allow_status:
            return {} if response is None else response
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
        previous = self._wait_deadline
        deadline = time.monotonic() + self.timeout
        self._wait_deadline = min(deadline, previous) if previous is not None else deadline
        try:
            while True:
                obj = fetch()
                if ready(obj):
                    return obj
                remaining = self._wait_deadline - time.monotonic()
                if remaining <= 0:
                    return None
                time.sleep(min(POLL_INTERVAL, remaining))
                if time.monotonic() >= self._wait_deadline:
                    return None
        finally:
            self._wait_deadline = previous

    def find_one(self, items, kind, **match):
        found = [i for i in items if all(i.get(k) == v for k, v in match.items())]
        if len(found) > 1:
            self.module.fail_json(
                msg="Found %d %s matching %s (ids: %s); use an id instead."
                    % (len(found), kind, match, ", ".join(str(i.get("id")) for i in found))
            )
        return found[0] if found else None

    def activity(self, server_id):
        """Count the entries in a server's activity log, so that later ones can be told apart."""
        logs = self.get("%s%s/activity/" % (SERVERS, server_id))["logs"]
        return Counter((entry["date"], entry["message"]) for entry in logs)

    def wait_activity(self, server_id, before, refusals, finished, what, resubmit=None, **failure):
        """Wait until finished(new activity messages) returns a value, and return it.

        The API queues server operations and accepts them with 202 before they run, so a refusal only
        shows up in the activity log: fail as soon as a new entry starts with one of refusals. A refusal
        because another operation was still running means nothing ran; with resubmit, the request is
        sent again, at most every RESUBMIT_DELAY seconds, until it runs or the timeout passes.
        """
        state = {"before": before, "next_try": 0}

        def outcome():
            logs = self.get("%s%s/activity/" % (SERVERS, server_id))["logs"]
            current = Counter((entry["date"], entry["message"]) for entry in logs)
            counts = current - state["before"]
            fresh = [entry["message"] for entry in logs if counts[(entry["date"], entry["message"])]]
            refused = [m for m in fresh if m.startswith(tuple(refusals))]
            terminal = next((m for m in refused if not resubmit or BUSY not in m), None)
            if terminal:
                return False, terminal
            if refused:
                now = time.monotonic()
                if state["next_try"] <= now < self._wait_deadline:
                    state["before"] = current
                    state["next_try"] = now + RESUBMIT_DELAY
                    resubmit()
                return None
            value = finished(fresh)
            return None if value is None else (True, value)

        result = self.wait_for(outcome, lambda value: value is not None)
        if result is None:
            self.module.fail_json(changed=True, msg="%s was not confirmed in time." % what, **failure)
        if not result[0]:
            self.module.fail_json(changed=True, msg="%s failed: %s" % (what, result[1]), **failure)
        return result[1]

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

    def freedns_domain(self, domain, source):
        """FreeDNS finds internal domains by their PidginHost ID and external domains by name."""
        if source == "external":
            return domain
        found = self.get("/api/domain/domain/%s/" % domain, allow_404=True, sensitive=True)
        if not found:
            self.module.fail_json(msg="Domain %s not found in the account." % domain)
        return found["id"]
