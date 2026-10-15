# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: buckets_info

short_description: List object storage buckets.

version_added: 0.4.0

description:
  - List the S3 object storage buckets in the account.
  - Buckets being deleted are listed with status C(cancelling) or C(terminating) until the deletion completes.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_buckets_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List buckets
  pidginhost.cloud.buckets_info:
  register: result
"""

RETURN = r"""
buckets:
  description:
    - Buckets.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 5
      name: media
      full_name: c1001-media
      quota_gb: 10
      used_bytes: 1048576
      object_count: 12
      public_read: false
      status: active
      endpoint: https://s3.example.com
      region: default
      created: "2026-01-01T10:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(argument_spec=pidginhost_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, buckets=PidginHostAPI(module).list("/api/cloud/buckets/"))


if __name__ == "__main__":
    main()
