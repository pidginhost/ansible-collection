# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_keys_info

short_description: List account SSH keys.

version_added: 0.2.0

description:
  - List every SSH public key of the account.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info
"""

EXAMPLES = r"""
- name: List SSH keys
  pidginhost.cloud.ssh_keys_info:
  register: result
"""

RETURN = r"""
ssh_keys:
  description:
    - SSH keys of the account.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 7
      alias: laptop
      fingerprint: "SHA256:..."
      key: ssh-ed25519 AAAA... user@example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, ssh_keys=PidginHostAPI(module).list("/api/account/ssh-keys/"))


if __name__ == "__main__":
    main()
