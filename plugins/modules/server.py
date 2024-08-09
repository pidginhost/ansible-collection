# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume

short_description: Create or delete Servers

version_added: 0.2.0

description:
  - Creates or deletes Servers.
  - View the create API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_create).
  - View the delete API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_destroy).
  - Run package_info module to check the available packages.

author:
  - Popescu Andrei Cristian (@shbpty)
  
options:
  hostname:
    description:
      - The human-readable string you wish to use when displaying the Server hostname.
    type: str
    required: false
  image:
    description:
      - Specifies the image or template to be used for the server.
    type: str
    required: false
  package:
    description:
      - Specifies the server's package.
    type: str
    required: false
  project:
    description:
      - The project or group the server will be associated with.
    type: str
    required: false
  password:
    description:
      - The password to be used for server authentication.
    type: str
    required: false
  ssh_pub_key:
    description:
      - The SSH public key for server access.
    type: str
    required: false
  ssh_pub_key_id:
    description:
      - An identifier for the SSH public key.
    type: str
    required: false
  public_ip:
    description:
      - The public IPv4 address to be assigned to the server.
    type: str
    required: false
  new_ipv4:
    description:
      - A boolean to indicate whether a new IPv4 address should be assigned.
    type: bool
    required: false
  public_ipv6:
    description:
      - The public IPv6 address to be assigned to the server.
    type: str
    required: false
  new_ipv6:
    description:
      - A boolean to indicate whether a new IPv6 address should be assigned.
    type: bool
    required: false
  fw_rules_set:
    description:
      - The firewall rules set to be applied to the server.
    type: str
  fw_policy_in:
    description:
      - The firewall policy for incoming traffic (default is "ACCEPT").
    type: str
    required: false 
  fw_policy_out:
    description:
      - The firewall policy for outgoing traffic (default is "ACCEPT").
    type: str
    required: false
  private_network:
    description:
      - The private network the server should be connected to.
    type: str
    required: false
  private_address:
    description:
      - The private IPv4 address for the server.
    type: str
    required: false
  extra_volume_product:
    description:
      - Additional volume type for the server.
    type: str
    required: false
  extra_volume_size:
    description:
      - Size of the additional volume.
    type: str
    required: false
  no_network_acknowledged:
    description:
      - A boolean confirming network settings.
    type: bool
    required: false                               
  unique_hostname:
    description:
      - |
        When C(true) for C(state=present) the Server will only be created if it has uniq hostname.
      - |
        When C(true) for C(state=absent) the Server will only be destroyed if it has uniq hostname.
    type: bool
    required: false
    default: false
"""

EXAMPLES = r"""
- name: Create Server
pidginhost.cloud.server:
  token: "{{ pidgin_host_token }}"
  state: present
  unique_hostname: true
  image: string
  package: string
  hostname: string
  project: string
  password: string
  ssh_pub_key: string
  ssh_pub_key_id: string
  public_ip: string
  new_ipv4: true
  public_ipv6: string
  new_ipv6: true
  fw_rules_set: string
  fw_policy_in: ACCEPT
  fw_policy_out: ACCEPT
  private_network: string
  private_address: 198.51.100.42
  extra_volume_product: string
  extra_volume_size: 0
  no_network_acknowledged: true

- name: Delete Server by server hostname
pidginhost.cloud.server:
  token: "{{ pidgin_host_token }}"
  state: absent
  unique_hostname: true
  hostname: string

- name: Delete Server by server id
pidginhost.cloud.server:
  token: "{{ pidgin_host_token }}"
  state: absent
  server_id: true
"""

RETURN = """
server:
  description: 
    - Indicates the result of creating the server.
  type: dict
  returned: always
  sample:
    changed: true
    failed: false
    server:
      cpus: 2
      disk_size: 64
      hostname: hhtest22332.com
      id: 707
      image: ubuntu22
      machine:
        cpu:
          cores: 2
          usage: 29.88
        memory:
          maxmem: 4294967296
          mem: 30352674
          usage: 0.71
        status: running
        uptime: 1
        uptime_text: "0:00:01"
      memory: 4
      networks:
        private: []
        public:
          interface: eth0
          ipv4: 176.124.106.104
          ipv6: 2001:67c:744:1::22
      package: cloudv-3
      project: z5
      status: provisioning
      username: phuser
      volumes: []
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
    - Package you have chosen is PACKAGE value of package must be one of: PACKAGE_LIST
    - Deleted Cloud Server HOSTNAME (2342) has succeeded.
    - Cloud server with hostname (HOSTNAME) id (23423) exists
    - There are currently (234) Servers hostname named (HOSTNAME) : (23,234,234)
    - Cloud server with hostname (HOSTNAME) would be created.
    - Cloud server HOSTNAME not found
    - Cloud server HOSTNAME (2343432) would be deleted
    - There are currently 2342 Cloud Servers named HOSTNAME : 23,234,234
    - Must provide server_id when deleting Cloud Server without unique_hostname
    - Cloud Server with ID 3242 not found
    - Cloud Server with ID 23423 would be deleted
  """

import time
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class PidginHostCloud(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.server_id = module.params.get('server_id')
        self.token = module.params.get("token")
        self.unique_hostname = module.params.get("unique_hostname")
        self.image = module.params.get("image")
        self.package = module.params.get("package")
        self.hostname = module.params.get("hostname")
        self.project = module.params.get("project")
        self.password = module.params.get("password")
        self.ssh_pub_key = module.params.get("ssh_pub_key")
        self.ssh_pub_key_id = module.params.get("ssh_pub_key_id")
        self.public_ip = module.params.get("public_ip")
        self.new_ipv4 = module.params.get("new_ipv4")
        self.public_ipv6 = module.params.get("public_ipv6")
        self.new_ipv6 = module.params.get("new_ipv6")
        self.fw_rules_set = module.params.get("fw_rules_set")
        self.fw_policy_in = module.params.get("fw_policy_in")
        self.fw_policy_out = module.params.get("fw_policy_out")
        self.private_network = module.params.get("private_network")
        self.private_address = module.params.get("private_address")
        self.extra_volume_product = module.params.get("extra_volume_product")
        self.extra_volume_size = module.params.get("extra_volume_size")
        self.no_network_acknowledged = module.params.get("no_network_acknowledged")
        self.timeout = module.params.get("timeout")

        # Dynamic max length checker
        self.arguments_max_length(hostname=self.hostname, project=self.project,
                                  password=self.password, ssh_pub_key=self.ssh_pub_key,
                                  ssh_pub_key_id=self.ssh_pub_key_id)

        if self.state == "present":
            # Dynamic package choices checker
            package_choices = self.return_packages_choices()
            if self.package not in package_choices:
                self.module.fail_json(
                    changed=False,
                    msg=f"Package you have chosen is {self.package} value of package must be one of: {package_choices}",
                    server=[],
                )
            self.present()
        elif self.state == "absent":
            self.absent()

    def present(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if self.unique_hostname:
            if len(servers) == 0:
                if self.module.check_mode:
                    self.module.exit_json(
                        changed=True,
                        msg=f"Cloud server with hostname ({self.hostname}) would be created",
                        server=[],
                    )
                else:
                    self.create_cloud_server()

            elif len(servers) == 1:
                self.module.fail_json(
                    changed=False,
                    msg=f"Cloud server with hostname ({self.hostname}) id ({servers[0]['id']}) exists",
                    server=servers[0],
                )
            elif len(servers) > 1:
                servers_ids = ", ".join([str(server["id"]) for server in servers])
                self.module.fail_json(
                    changed=False,
                    msg=f"There are currently ({len(servers)}) Servers hostname named "
                        f"({self.hostname}) : ({servers_ids})",
                    server=[],
                )
        if self.module.check_mode:
            self.module.exit_json(
                changed=True,
                msg=f"Cloud server with hostname ({self.hostname}) would be created",
                server=[],
            )
        else:
            self.create_cloud_server()

    def absent(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if self.unique_hostname:
            if len(servers) == 0:
                if self.module.check_mode:
                    self.module.exit_json(
                        changed=False,
                        msg=f"Cloud server {self.hostname} not found",
                        server=[],
                    )
                else:
                    self.module.exit_json(
                        changed=False,
                        msg=f"Cloud server {self.hostname} not found",
                        server=[],
                    )
            elif len(servers) == 1:
                if self.module.check_mode:
                    self.module.exit_json(
                        changed=True,
                        msg=f"Cloud server {self.hostname} ({servers[0]['id']}) would be deleted",
                        server=servers[0],
                    )
                else:
                    self.delete_cloud_server(servers[0])
            elif len(servers) > 1:
                servers_ids = ", ".join([str(server["id"]) for server in servers])
                self.module.fail_json(
                    changed=False,
                    msg=f"There are currently {len(servers)} Cloud Servers named {self.hostname} : {servers_ids}",
                    server=[],
                )

        if not self.server_id:
            self.module.fail_json(
                changed=False,
                msg="Must provide server_id when deleting Cloud Server without unique_hostname",
                server=[],
            )

        server = self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
        if not server:
            self.module.exit_json(
                changed=False,
                msg=f"Cloud Server with ID {self.server_id} not found",
                server=[],
            )
        if self.module.check_mode:
            self.module.exit_json(
                changed=True,
                msg=f"Cloud Server with ID {self.server_id} would be deleted",
                server=server[0],
            )
        else:
            self.delete_cloud_server(servers[0])

    def create_cloud_server(self):
        body = {
            "image": self.image,
            "package": self.package,
            "hostname": self.hostname,
            "project": self.project,
            "password": self.password,
            "ssh_pub_key": self.ssh_pub_key,
            "ssh_pub_key_id": self.ssh_pub_key_id,
            "public_ip": self.public_ip,
            "new_ipv4": self.new_ipv4,
            "public_ipv6": self.public_ipv6,
            "new_ipv6": self.new_ipv6,
            "fw_rules_set": self.fw_rules_set,
            "fw_policy_in": self.fw_policy_in,
            "fw_policy_out": self.fw_policy_out,
            "private_network": self.private_network,
            "private_address": self.private_address,
            "extra_volume_product": self.extra_volume_product,
            "extra_volume_size": self.extra_volume_size,
            "no_network_acknowledged": self.no_network_acknowledged
        }
        server = self.post_request(self.CLOUD_SERVERS_ENDPOINT, body, self.CREATE_SERVER_SUCCESS_CODE)
        if server:
            cloud_server = self.check_if_machine_exist(server)

            if cloud_server:
                machine = cloud_server.get("machine", [])
                if machine["status"] != "running":
                    self.module.fail_json(
                        changed=True,
                        msg=(
                            f"Created Cloud {cloud_server['hostname']} "
                            f"({cloud_server['id']}) is not 'active', it is '{machine['status']}'"
                        ),
                        server=server,
                    )
                server = self.get_cloud_server_by_id(server['id'])
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f'You successfully create a new cloud server with hostname'
                        f' {cloud_server["hostname"]} and id : {cloud_server["id"]}'
                    ),
                    server=server,
                )

    def delete_cloud_server(self, server_data):
        server_id = server_data["id"]
        server_hostname = server_data["hostname"]
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}"
        self.delete_request(url, self.DELETE_SUCCESS_CODE)

        server_still_exists = self.get_cloud_server_data_by_id(server_id, self.ERROR_CODES)
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time and server_still_exists:
            time.sleep(self.SLEEP)
            server_still_exists = self.get_cloud_server_data_by_id(server_id,
                                                                   self.ERROR_CODES)
        if server_still_exists:
            self.module.fail_json(
                changed=False,
                msg=f"Deleting Cloud Server {server_hostname} ({server_id}) has failed",
                server=server_data,
            )
        self.module.exit_json(
            changed=True,
            msg=f"Deleted Cloud Server {server_hostname} ({server_id}) has succeeded",
            server=server_data,
        )

    def check_if_machine_exist(self, server):
        end_time = time.monotonic() + self.timeout
        while time.monotonic() < end_time:
            time.sleep(self.SLEEP)
            cloud_server = self.get_cloud_server_data_by_id(server["id"], self.SUCCESS_CODE)
            if cloud_server.get("machine")["status"] == "running":
                return cloud_server
        return None


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(ssh_pub_key=dict(type='str', required=False),
                         unique_hostname=dict(
                             type=bool,
                             choices=[True, False],
                             default=False,
                         ),
                         server_id=dict(type='str', required=False),
                         image=dict(type='str', required=False),
                         package=dict(type='str', required=False),
                         hostname=dict(type='str', required=False),
                         project=dict(type='str', required=False),
                         password=dict(type='str', required=False, no_log=True),
                         ssh_pub_key_id=dict(type='str', required=False, no_log=True),
                         public_ip=dict(type='str', required=False),
                         new_ipv4=dict(type=bool, required=False),
                         public_ipv6=dict(type='str', required=False),
                         new_ipv6=dict(type=bool, required=False),
                         fw_rules_set=dict(type="str", required=False),
                         fw_policy_in=dict(type="str", required=False),
                         fw_policy_out=dict(type="str", required=False),
                         private_network=dict(type="str", required=False),
                         private_address=dict(type="str", required=False),
                         extra_volume_product=dict(type="str", required=False),
                         extra_volume_size=dict(type="str", required=False),
                         no_network_acknowledged=dict(type="str", required=False))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["image"]),
            ("state", "present", ["package"]),
            ("state", "present", ["hostname"]),
            ("state", "present", ["password"]),
            ("state", "present", ["new_ipv4"]),
            ("state", "present", ["new_ipv6"]),
        ],
    )
    PidginHostCloud(module)


if __name__ == '__main__':
    main()
