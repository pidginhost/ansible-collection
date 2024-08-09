# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ips_info

short_description: Print IPS info

version_added: 0.2.0

description:
  - Print IPS info
  - View IPV4 documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_ipv4_list).
  - View IPV6 documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_ipv6_list).

author:
  - Popescu Andrei Cristian (@shbpty)

options:
  ip_type:
    description:
      - The IP type.
    type: str
    required: true
    choices:
      - ipv4
      - ipv6
"""

EXAMPLES = r"""
- name: Print all ipv4 info
  pidginhost.cloud.ips_info:
    state: present
    token: "{{ pidgin_host_token }}"
    ip_type: ipv4

- name: Print all ipv6 info
  pidginhost.cloud.ips_info:
    state: present
    token: "{{ pidgin_host_token }}"
    ip_type: ipv6
"""

RETURN = r"""
ips:
  description: 
    - IPS info.
  type: list
  returned: always
  sample:
    changed: false
    failed: false
    results:
    - address: "176.124.106.79"
      attached: false
      gateway: "176.124.106.1"
      id: 599
      prefix: 24
      server: null
      slug: "176.124.106.79"
    - address: "176.124.106.105"
      attached: false
      gateway: "176.124.106.1"
      id: 601
      prefix: 24
      server: null
      slug: "176.124.106.105"
    - address: "176.124.106.104"
      attached: true
      gateway: "176.124.106.1"
      id: 685
      prefix: 24
      server: "hhtest22332.com"
      slug: "176.124.106.104"
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action result information.
  returned: always
  type: str
  sample:
    - All IPV4 addresses info
    - All IPV6 addresses info
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class IpsInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.ip_type = module.params.get('ip_type')
        if self.state == "present":
            self.present()

    def present(self):
        if self.ip_type == "ipv4":
            ips = self.get_ipv4_address_info()
            self.module.exit_json(
                changed=False,
                msg=f"All IPV4 addresses info",
                ips=ips.get('results'),
            )

        if self.ip_type == "ipv6":
            ips = self.get_ipv6_address_info()
            self.module.exit_json(
                changed=False,
                msg=f"All IPV6 addresses info",
                ips=ips.get('results'),
            )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        ip_type=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    IpsInformation(module)


if __name__ == '__main__':
    main()
