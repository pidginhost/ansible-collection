# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_action_power

short_description: Manage Servers action power.

version_added: 0.2.0

description:
  - Set power states of a Server.
  - State "start" powers on a Server.
  - |
    State "stop" is a hard shutdown and should only be used if the shutdown
    action is not successful. It is similar to cutting the power on a server and
    could lead to complications.
  - |
    State "shutdown" is an attempt to shut down the Server in a graceful way,
    similar to using the shutdown command from the console. Since a "shutdown"
    command can fail, this action guarantees that the command is issued, not that
    it succeeds. The preferred way to turn off a Server is to attempt a "shutdown",
    with a reasonable timeout, followed by a "stop" state to ensure the
    Server is off.
  - View Power Management API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_power_management_create).

author:
  - Popescu Andrei Cristian (@shbpty)

options:
  server_id:
    description:
      - A unique identifier for a Server instance.
      - If provided, `server_hostname` is ignored.
    type: int
    required: false

  server_hostname:
    description:
      - The hostname of the Server to act on.
      - If provided, must be unique.
    type: str
    required: false

  state:
    description:
      - The power state transition.
    type: str
    choices: [start, stop, shutdown, reboot]
    default: start

  force_power_off:
    description:
      - Force power off if C(shutdown) fails.
    type: bool
    required: false
    default: false
"""

EXAMPLES = r"""
- name: Power off a Cloud Server
 pidginhost.cloud.server_action_power:
   token: "{{ token }}"
   state: stop
   server_id: 1122334455
   server_hostname: hostname

- name: Power on a Cloud Server
 pidginhost.cloud.server_action_power:
   token: "{{ token }}"
   state: start
   server_id: 1122334455
   server_hostname: hostname

- name: Reboot a Cloud Server
 pidginhost.cloud.server_action_power:
   token: "{{ token }}"
   state: reboot
   server_id: 1122334455
   server_hostname: hostname

- name: Shut down a Cloud Server (force if unsuccessful)
 pidginhost.cloud.server_action_power:
   token: "{{ token }}"
   state: shutdown
   force_power_off: true
   server_id: 1122334455
   server_hostname: hostname
"""

RETURN = """
action:
  description: 
    - Manipulate Servers action power.
  type: dict
  returned: always
  sample:
    changed: true
    failed: false
    action:
      status: stopped
    changed: true
    failed: false

error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action information.
  returned: always
  type: str
  sample:
    - Server HOSTNAME (2342) not sent action 'ACTION_TYPE', it is 'ACTION_STATUS'
    - No Server named with hostname HOSTNAME
    - Multiple Servers (232) found, with hostname: (HOSTNAME)
    - Server HOSTNAME (2323) sent action 'ACTION_TYPE' and it has not completed, status is 'ACTION_STATUS'
    - Server HOSTNAME (23423) sent action 'ACTION_TYPE'
    - Server HOSTNAME (234) would be sent action 'ACTION_TYPE', it is 'ACTION_STATUS'
    - Server HOSTNAME (23423) would be sent action 'ACTION_TYPE', it is 'ACTION_STATUS'
    - Server HOSTNAME (2342) would not be sent action 'ACTION_TYPE', it is 'ACTION_STATUS'
    - Server HOSTNAME (32432) not sent action 'ACTION_TYPE', it is 'ACTION_STATUS'
    - Server HOSTNAME (32432) would be sent action 'ACTION_TYPE', it is 'ACTION_STATUS'.
  """

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions
import time


class ServerActionPower(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.timeout = module.params.get("timeout")
        self.server_id = module.params.get("server_id")
        self.hostname = module.params.get("server_hostname")
        if self.server_id:
            self.server = self.find_server_by_id()
        if self.hostname and not self.server_id:
            self.server = self.find_server_by_hostname()
            self.server_id = self.server["id"]
        self.type = self.state
        self.force_power_off = module.params.get("force_power_off")
        self.endpoint = f"{self.CLOUD_SERVERS_ENDPOINT}{self.server_id}{self.POWER_MANAGEMENT}"

        self.body = {
            "action": self.type,
        }

        if self.type == "stop":
            self.power_off()
        elif self.type == "start":
            self.power_on()
        elif self.type == "shutdown":
            self.shutdown()
        elif self.type == "reboot":
            self.reboot()

    def find_server_by_id(self):
        if self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE):
            return self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
        self.module.fail_json(
            changed=False,
            msg=f"No Server with ID {self.server_id}",
            action=[],
        )

    def find_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                action=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                action=[],
            )
        return servers[0]

    def set_power_off(self):
        action = self.post_request(self.endpoint, self.body, self.SUCCESS_CODE)
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time and action["status"] != "stopped":
            time.sleep(self.SLEEP)
            action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)

        if action["status"] != "stopped":
            self.module.fail_json(
                changed=True,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f" sent action '{self.type}' and it has not completed, status is '{action['status']}'"
                ),
                action=action,
            )

        self.module.exit_json(
            changed=True,
            msg=f"Server {self.server['hostname']} ({self.server['id']}) sent action '{self.type}'",
            action=action,
        )

    def set_power_on(self):
        action = self.post_request(self.endpoint, self.body, self.SUCCESS_CODE)
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time and action["status"] != "running":
            time.sleep(self.SLEEP)
            action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)

        if action["status"] != "running":
            self.module.fail_json(
                changed=True,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f" sent action '{self.type}' and it has not completed, status is '{action['status']}'"
                ),
                action=action,
            )

        self.module.exit_json(
            changed=True,
            msg=f"Server {self.server['hostname']} ({self.server['id']}) sent action '{self.type}'",
            action=action,
        )

    def set_shutdown(self):
        action = self.post_request(self.endpoint, self.body, self.SUCCESS_CODE)
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time and action["status"] != "stopped":
            time.sleep(self.SLEEP)
            action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)

        if action["status"] != "stopped":
            if self.force_power_off:
                self.power_off()

            self.module.fail_json(
                changed=True,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f" sent action '{self.type}' and it has not completed, status is '{action['status']}'"
                ),
                action=action,
            )

        self.module.exit_json(
            changed=True,
            msg=f"Server {self.server['hostname']} ({self.server['id']}) sent action '{self.type}'",
            action=action,
        )

    def set_reboot(self):
        action = self.post_request(self.endpoint, self.body, self.SUCCESS_CODE)
        time.sleep(self.SLEEP * 2)
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time and action["status"] != "running":
            time.sleep(self.SLEEP)
            action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)
        if action["status"] != "running":
            self.module.fail_json(
                changed=True,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f" sent action '{self.type}' and it has not completed, status is '{action['status']}'"
                ),
                action=action,
            )

        self.module.exit_json(
            changed=True,
            msg=f"Server {self.server['hostname']} ({self.server['id']}) sent action '{self.type}'",
            action=action,
        )

    def power_off(self):
        action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)
        if self.module.check_mode:
            if action["status"] != "stopped":
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Server {self.server['hostname']} ({self.server['id']})"
                        f"would be sent action '{self.type}', it is '{action['status']}' "
                    ),
                    action=[],
                )
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"would not be sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        if action["status"] == "stopped":
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"not sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        self.set_power_off()

    def power_on(self):
        action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)
        if self.module.check_mode:
            if action["status"] == "stopped":
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Server {self.server['hostname']} ({self.server['id']}) "
                        f"would be sent action '{self.type}', it is '{action['status']}'"
                    ),
                    action=[],
                )
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"would not be sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        if action["status"] != "stopped":
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"not sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        self.set_power_on()

    def shutdown(self):
        action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)
        if self.module.check_mode:
            if action["status"] != "stopped":
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Server {self.server['hostname']} ({self.server['id']})"
                        f"would be sent action '{self.type}', it is '{action['status']} .'"
                    ),
                    action=[],
                )
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']})"
                    f"would not be sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        if action["status"] == "stopped":
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"not sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        self.set_shutdown()

    def reboot(self):
        action = self.get_server_power_management_by_id(self.server_id, self.SUCCESS_CODE)
        if self.module.check_mode:
            if action["status"] != "stopped":
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Server {self.server['hostname']} ({self.server['id']})"
                        f"would be sent action '{self.type}', it is '{action['status']} .'"
                    ),
                    action=[],
                )
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']})"
                    f"would not be sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        if action["status"] == "stopped":
            self.module.exit_json(
                changed=False,
                msg=(
                    f"Server {self.server['hostname']} ({self.server['id']}) "
                    f"not sent action '{self.type}', it is '{action['status']}'"
                ),
                action=[],
            )

        self.set_reboot()


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_id=dict(type="int", required_one_of=["hostname", "server_id"]),
        server_hostname=dict(type="str", required_one_of=["hostname", "server_id"]),
        state=dict(
            type="str",
            choices=["start", "stop", "shutdown", "reboot"],
            default="start", required=False),
        force_power_off=dict(type="bool", required=False, default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "shutdown", ["force_power_off"]),
        ],
    )

    ServerActionPower(module)


if __name__ == '__main__':
    main()
