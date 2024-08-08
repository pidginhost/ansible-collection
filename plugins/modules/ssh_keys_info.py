# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_keys_info

short_description: Print SSH Keys info

version_added: 0.2.0

description:
  - Print SSH Keys info.
  - View the SSH Keys info documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_list).
author:
  - Popescu Andrei Cristian (@shbpty)

"""

EXAMPLES = """
    - name: Print SSH Keys info
      pidginhost.cloud.ssh_keys_info:
        state: present
        token: "{{ pidgin_host_token }}"
      register: result
"""

RETURN = """
ssh_keys:
  changed: false
  failed: false
  ssh_keys:
    - alias: "and.c"
      fingerprint: "ryBS/UY64JDh5k0/6c0gjHyswHaY5Mngq+qBNF1wYdg"
      id: 118
      key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCo3WBKsJb8xE"
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
    - Current SSH keys.
  """

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class SSHKeysInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        ssh_keys = self.get_ssh_keys()
        if ssh_keys:
            self.module.exit_json(
                changed=False,
                msg="Current SSH keys",
                ssh_keys=ssh_keys.get("results"),
            )
        self.module.exit_json(changed=False, msg="No SSH keys", ssh_keys=[])


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    SSHKeysInformation(module)


if __name__ == '__main__':
    main()
