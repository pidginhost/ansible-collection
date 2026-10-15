# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server

short_description: Create, update or delete cloud servers.

version_added: 0.2.0

description:
  - Create, update or delete PidginHost cloud servers.
  - The server is identified by O(server_id) or by its unique O(hostname).
  - An existing server is updated in place for O(project) and O(destroy_protection). Other creation options only apply
    when the server is created.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the server should exist.
    type: str
    choices: [present, absent]
    default: present
  server_id:
    description:
      - ID of an existing server.
    type: int
  hostname:
    description:
      - Server hostname. Used to find the server when O(server_id) is not set, so it must be unique in the account.
    type: str
  image:
    description:
      - Image ID or slug. Required to create a server. See M(pidginhost.cloud.images_info).
    type: str
  package:
    description:
      - Package ID or slug. Required to create a server. See M(pidginhost.cloud.packages_info).
      - Use M(pidginhost.cloud.server_action_resize) to change the package of an existing server.
    type: str
  generation:
    description:
      - Hardware generation slug. See M(pidginhost.cloud.generations_info).
    type: str
  project:
    description:
      - Project name.
    type: str
  password:
    description:
      - Password for the default user. Only used on creation.
    type: str
  ssh_pub_key:
    description:
      - New SSH public key to install. Only used on creation.
    type: str
  ssh_pub_key_id:
    description:
      - ID or fingerprint of an SSH key already in the account. Only used on creation.
    type: str
  user_data:
    description:
      - Startup script run on first boot. Must start with a shebang. Stored in cleartext.
    type: str
  public_ip:
    description:
      - ID or address of an IPv4 address you own to attach on creation.
    type: str
  new_ipv4:
    description:
      - Allocate a new IPv4 address on creation.
    type: bool
  public_ipv6:
    description:
      - ID or address of an IPv6 address you own to attach on creation.
    type: str
  new_ipv6:
    description:
      - Allocate a new IPv6 address on creation.
    type: bool
  no_network_acknowledged:
    description:
      - Confirm creating a server without a public IP address.
    type: bool
  fw_rules_set:
    description:
      - Firewall rules set ID or name to apply on creation.
    type: str
  fw_policy_in:
    description:
      - Default policy for incoming traffic on creation.
    type: str
    choices: [ACCEPT, DROP, REJECT]
  fw_policy_out:
    description:
      - Default policy for outgoing traffic on creation.
    type: str
    choices: [ACCEPT, DROP, REJECT]
  private_network:
    description:
      - Private network ID or CIDR to join on creation.
    type: str
  private_address:
    description:
      - IPv4 address in O(private_network). Assigned automatically when not set.
    type: str
  extra_volume_product:
    description:
      - Storage product ID or slug for an extra volume created with the server.
    type: str
  extra_volume_size:
    description:
      - Size in GB of the extra volume.
    type: int
  enable_ha:
    description:
      - Enable high availability (automatic restart and migration on host failure). Only used on creation.
    type: bool
  destroy_protection:
    description:
      - Protect the server from deletion.
      - Enabling protection on a new server requires O(wait=true).
      - With O(state=absent), V(false) turns protection off before deleting the server.
    type: bool
  wait:
    description:
      - Wait until the server is active after creation, or gone after deletion.
      - Also wait for an earlier deletion that is still in progress, without requesting deletion again.
    type: bool
    default: true
  unique_hostname:
    description:
      - Ignored. The hostname is always used as the server identity when O(server_id) is not set.
    type: bool
"""

EXAMPLES = r"""
- name: Create a server
  pidginhost.cloud.server:
    hostname: web1.example.com
    image: ubuntu24
    package: cloudv-2
    ssh_pub_key_id: "123"
    new_ipv4: true
    destroy_protection: true
  register: web1

- name: Delete a server by hostname, turning protection off first
  pidginhost.cloud.server:
    state: absent
    hostname: web1.example.com
    destroy_protection: false

- name: Delete a server by id
  pidginhost.cloud.server:
    state: absent
    server_id: 12345
"""

RETURN = r"""
server:
  description:
    - Server details. After deletion, the details before deletion.
    - With O(wait=false), only the ID of a newly created server.
  returned: success
  type: dict
  sample:
    id: 12345
    hostname: web1.example.com
    status: active
    package: cloudv-2
    image: ubuntu24
    destroy_protection: true
    networks:
      public:
        ipv4: 192.0.2.10
        ipv6: 2001:db8::10
      private: []
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec

CREATE_FIELDS = (
    "hostname", "image", "package", "generation", "project", "password", "ssh_pub_key", "ssh_pub_key_id",
    "user_data", "public_ip", "new_ipv4", "public_ipv6", "new_ipv6", "no_network_acknowledged", "fw_rules_set",
    "fw_policy_in", "fw_policy_out", "private_network", "private_address", "extra_volume_product",
    "extra_volume_size", "enable_ha",
)


def server_path(server_id, suffix=""):
    return "%s%s/%s" % (SERVERS, server_id, suffix)


def set_destroy_protection(api, server_id, enabled):
    api.post(server_path(server_id, "destroy-protection/"), {"destroy_protection": enabled})


def create(api, module):
    params = module.params
    missing = [name for name in ("image", "package") if not params[name]]
    if missing:
        module.fail_json(msg="Creating a server requires: %s" % ", ".join(missing))
    if params["destroy_protection"] and not params["wait"]:
        module.fail_json(msg="Creating a server with destroy_protection=true requires wait=true.")
    if module.check_mode:
        module.exit_json(changed=True, server={})

    server_id = api.post(SERVERS, drop_none(dict((k, params[k]) for k in CREATE_FIELDS)))["id"]
    if not params["wait"]:
        module.exit_json(changed=True, server={"id": server_id})

    # New servers return 404 while pending, then move through provisioning to active or failed.
    server = api.wait_for(
        lambda: api.get(server_path(server_id), allow_404=True),
        lambda s: s is not None and s["status"] in ("active", "failed"),
    )
    if not server or server["status"] != "active":
        module.fail_json(
            changed=True,
            msg="Server %s %s." % (server_id, "failed to provision" if server else "did not become active in time"),
            server=server or {"id": server_id},
        )
    if params["destroy_protection"]:
        set_destroy_protection(api, server_id, True)
        server["destroy_protection"] = True
    module.exit_json(changed=True, server=server)


def update(api, module, server):
    params = module.params
    project_changed = params["project"] is not None and params["project"] != server.get("project")
    protection_changed = (
        params["destroy_protection"] is not None and params["destroy_protection"] != server["destroy_protection"]
    )
    if not (project_changed or protection_changed):
        module.exit_json(changed=False, server=server)
    if module.check_mode:
        module.exit_json(changed=True, server=server)

    if project_changed:
        api.patch(server_path(server["id"]), {"project": params["project"]})
    if protection_changed:
        set_destroy_protection(api, server["id"], params["destroy_protection"])
    module.exit_json(changed=True, server=api.get(server_path(server["id"])))


def delete(api, module, server):
    changed = server["status"] not in ("cancelling", "terminating")
    if module.check_mode:
        module.exit_json(changed=changed, server=server)
    if changed:
        if server["destroy_protection"] and module.params["destroy_protection"] is False:
            set_destroy_protection(api, server["id"], False)
        api.delete(server_path(server["id"]))
    if module.params["wait"]:
        gone = api.wait_for(lambda: api.get(server_path(server["id"]), allow_404=True) is None, bool)
        if not gone:
            module.fail_json(changed=changed, msg="Server %s was not deleted in time." % server["id"], server=server)
    module.exit_json(changed=changed, server=server)


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            server_id=dict(type="int"),
            hostname=dict(type="str"),
            image=dict(type="str"),
            package=dict(type="str"),
            generation=dict(type="str"),
            project=dict(type="str"),
            password=dict(type="str", no_log=True),
            ssh_pub_key=dict(type="str", no_log=False),
            ssh_pub_key_id=dict(type="str", no_log=False),
            user_data=dict(type="str"),
            public_ip=dict(type="str"),
            new_ipv4=dict(type="bool"),
            public_ipv6=dict(type="str"),
            new_ipv6=dict(type="bool"),
            no_network_acknowledged=dict(type="bool"),
            fw_rules_set=dict(type="str"),
            fw_policy_in=dict(type="str", choices=["ACCEPT", "DROP", "REJECT"]),
            fw_policy_out=dict(type="str", choices=["ACCEPT", "DROP", "REJECT"]),
            private_network=dict(type="str"),
            private_address=dict(type="str"),
            extra_volume_product=dict(type="str"),
            extra_volume_size=dict(type="int"),
            enable_ha=dict(type="bool"),
            destroy_protection=dict(type="bool"),
            wait=dict(type="bool", default=True),
            unique_hostname=dict(
                type="bool", removed_in_version="1.0.0", removed_from_collection="pidginhost.cloud"),
        ),
        required_one_of=[("server_id", "hostname")],
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    server = api.find_server(module.params["server_id"], module.params["hostname"])

    if module.params["state"] == "absent":
        if not server:
            module.exit_json(changed=False, server={})
        delete(api, module, server)
    elif server:
        update(api, module, server)
    elif module.params["server_id"]:
        module.fail_json(msg="Server %s not found." % module.params["server_id"])
    else:
        create(api, module)


if __name__ == "__main__":
    main()
