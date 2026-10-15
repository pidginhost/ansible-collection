# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_action_power

short_description: Start, stop, shut down or reboot cloud servers.

version_added: 0.2.0

description:
  - Change the power state of a PidginHost cloud server.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - V(start) powers on a stopped server. Nothing is done when it is already running.
  - V(stop) cuts the power, like pulling the plug. Use it only when V(shutdown) does not work.
  - V(shutdown) asks the guest OS to shut down. The guest can ignore it, so combine it with O(force_power_off).
  - V(reboot) restarts a running server and always reports a change. Nothing is done when the server is stopped.
  - The API only accepts power actions while the server status is C(active).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_power_management_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  state:
    description:
      - The power action to apply.
    type: str
    choices: [start, stop, shutdown, reboot]
    default: start
  force_power_off:
    description:
      - With O(state=shutdown), cut the power with V(stop) when the server is not stopped after O(timeout) seconds.
      - Only used with O(wait=true).
    type: bool
    default: false
  wait:
    description:
      - Wait until the server is running after V(start) or V(reboot), or stopped after V(stop) or V(shutdown).
      - A reboot must reset uptime or pass through a stopped state before it is reported complete.
      - O(timeout) applies to each wait.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Power on a server
  pidginhost.cloud.server_action_power:
    server_hostname: web1.example.com
    state: start

- name: Shut down a server, cutting the power after two minutes
  pidginhost.cloud.server_action_power:
    server_id: 12345
    state: shutdown
    force_power_off: true
    timeout: 120

- name: Reboot a server without waiting
  pidginhost.cloud.server_action_power:
    server_hostname: web1.example.com
    state: reboot
    wait: false
"""

RETURN = r"""
action:
  description:
    - Power status of the server. After a change with O(wait=true), the status reached.
  returned: success
  type: dict
  sample:
    status: running
"""

import time

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, pidginhost_argument_spec


def wait_reboot(api, path, before, observed_at):
    stopped = [False]

    def fetch():
        started_at = time.monotonic()
        return api.get(path), started_at

    def ready(observation):
        usage, started_at = observation
        if usage["status"] == "stopped":
            stopped[0] = True
        # Allow for integer uptime rounding and request latency. A fast reboot
        # can finish between polls, so observing a stopped state is not required.
        reset = usage["uptime"] < before["uptime"] + started_at - observed_at - 1
        return usage["status"] == "running" and (stopped[0] or reset)

    done = api.wait_for(fetch, ready)
    return {"status": done[0]["status"]} if done is not None else None


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            state=dict(type="str", choices=["start", "stop", "shutdown", "reboot"], default="start"),
            force_power_off=dict(type="bool", default=False),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    state = params["state"]
    api = PidginHostAPI(module)
    server = api.require_server(params["server_id"], params["server_hostname"])
    path = "%s%s/power-management/" % (SERVERS, server["id"])

    target = "stopped" if state in ("stop", "shutdown") else "running"
    power = api.get(path)
    # A stopped server is left alone by reboot, as in earlier releases.
    if power["status"] == ("stopped" if state == "reboot" else target):
        module.exit_json(changed=False, action=power)
    if module.check_mode:
        module.exit_json(changed=True, action=power)

    usage_path = "%s%s/usage/" % (SERVERS, server["id"])
    if state == "reboot" and params["wait"]:
        before = api.get(usage_path)
        observed_at = time.monotonic()
    power = api.post(path, {"action": state})
    if not params["wait"]:
        module.exit_json(changed=True, action=power)

    def reached():
        return api.wait_for(lambda: api.get(path), lambda p: p["status"] == target)

    if state == "reboot":
        done = wait_reboot(api, usage_path, before, observed_at)
    else:
        done = reached()
    if done is None and state == "shutdown" and params["force_power_off"]:
        api.post(path, {"action": "stop"})
        done = reached()
    if done is None:
        module.fail_json(
            changed=True,
            msg="Server %s did not reach status %s in time after %s." % (server["id"], target, state),
            action=power,
        )
    module.exit_json(changed=True, action=done)


if __name__ == "__main__":
    main()
