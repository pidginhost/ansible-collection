# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: bucket_credentials

short_description: Read or rotate object storage bucket credentials.

version_added: 0.4.0

description:
  - Read the S3 access key and secret key of a bucket, or rotate them.
  - The secret key is returned in clear text. Set C(no_log=true) on the task that registers the result.
  - The API records every read and rotation in an audit trail.
  - Check mode returns no credentials and makes no audit entry.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_buckets_credentials_reveal_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  name:
    description:
      - Bucket name, without the account prefix.
    type: str
    required: true
  rotate:
    description:
      - Issue a new key pair and revoke the old one. Always reports a change.
      - When V(false), the current keys are read without changing anything.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Read the bucket keys
  pidginhost.cloud.bucket_credentials:
    name: media
  register: s3
  no_log: true

- name: Rotate the bucket keys
  pidginhost.cloud.bucket_credentials:
    name: media
    rotate: true
  register: s3
  no_log: true
"""

RETURN = r"""
credentials:
  description:
    - S3 connection details. Empty in check mode.
  returned: success
  type: dict
  contains:
    bucket:
      description: Full bucket name to use with S3 clients.
      type: str
      sample: c1001-media
    endpoint:
      description: S3 endpoint URL.
      type: str
      sample: https://s3.example.com
    region:
      description: S3 region.
      type: str
      sample: default
    access_key:
      description: S3 access key.
      type: str
    secret_key:
      description: S3 secret key, in clear text.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec

BUCKETS = "/api/cloud/buckets/"


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            name=dict(type="str", required=True),
            rotate=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    rotate = module.params["rotate"]
    bucket = api.find_one(api.list(BUCKETS), "buckets", name=module.params["name"])
    if not bucket:
        module.fail_json(msg="Bucket %s not found." % module.params["name"])
    if module.check_mode:
        module.exit_json(changed=rotate, credentials={})
    path = "%s%s/credentials/%s/" % (BUCKETS, bucket["id"], "rotate" if rotate else "reveal")
    module.exit_json(changed=rotate, credentials=api.post(path))


if __name__ == "__main__":
    main()
