# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: servers_info

short_description: List cloud servers.

version_added: 0.2.0

description:
  - List every PidginHost cloud server in the account.
  - With O(server_id) or O(server_hostname), return only that server, with its full details and the extra data
    selected by O(include).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  server_id:
    description:
      - ID of the server to return.
    type: int
  server_hostname:
    description:
      - Hostname of the server to return. Must be unique in the account.
    type: str
  include:
    description:
      - Extra data to add to the selected server, each under a key of the same name.
      - V(snapshots) lists the server snapshots.
      - V(usage) is the current CPU and memory usage.
      - V(traffic) is the traffic used this month.
      - V(activity) is the server activity log.
      - V(boot_isos) lists the catalog ISOs and whether the server package can boot them.
      - Requires O(server_id) or O(server_hostname).
    type: list
    elements: str
    choices: [snapshots, usage, traffic, activity, boot_isos]
"""

EXAMPLES = r"""
- name: List every server
  pidginhost.cloud.servers_info:
  register: result

- name: Get one server with its snapshots and traffic
  pidginhost.cloud.servers_info:
    server_hostname: web1.example.com
    include:
      - snapshots
      - traffic
  register: result
"""

RETURN = r"""
servers:
  description:
    - Every server in the account, or a one item list with the details of the selected server.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 12345
      hostname: web1.example.com
      status: active
      package: cloudv-2
      image: ubuntu24
      networks:
        public:
          ipv4: 192.0.2.10
          ipv6: 2001:db8::10
        private: []
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, info_argument_spec


def fetch(api, path, name):
    if name in ("snapshots", "boot_isos"):
        return api.list("%s%s/" % (path, name.replace("_", "-")))
    if name == "activity":
        return api.get(path + "activity/").get("logs", [])
    return api.get("%s%s/" % (path, name))


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            include=dict(
                type="list", elements="str", choices=["snapshots", "usage", "traffic", "activity", "boot_isos"]),
        ),
        mutually_exclusive=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    selected = params["server_id"] or params["server_hostname"]
    if params["include"] and not selected:
        module.fail_json(msg="include requires server_id or server_hostname.")
    api = PidginHostAPI(module)
    if not selected:
        module.exit_json(changed=False, servers=api.list(SERVERS))

    server = api.require_server(params["server_id"], params["server_hostname"])
    path = "%s%s/" % (SERVERS, server["id"])
    for name in params["include"] or []:
        server[name] = fetch(api, path, name)
    module.exit_json(changed=False, servers=[server])


if __name__ == "__main__":
    main()
