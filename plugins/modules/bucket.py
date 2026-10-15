# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: bucket

short_description: Create, update or delete object storage buckets.

version_added: 0.4.0

description:
  - Create, update or delete PidginHost S3 object storage buckets.
  - The bucket is identified by its O(name), without the account prefix the API adds to C(full_name).
  - An existing bucket is updated in place for O(quota_gb) and O(public_read).
  - A deleted bucket keeps its name until the deletion completes. The module fails if asked to create it again
    before that.
  - Use M(pidginhost.cloud.bucket_credentials) to read the access keys.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_buckets_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the bucket should exist.
    type: str
    choices: [present, absent]
    default: present
  name:
    description:
      - Bucket name, without the account prefix.
    type: str
    required: true
  quota_gb:
    description:
      - Bucket quota in GB. Required to create a bucket.
    type: int
  public_read:
    description:
      - Allow anonymous read access to the objects in the bucket.
      - New buckets are private when not set.
    type: bool
  wait:
    description:
      - Wait until the bucket is active after creation or resize, or gone after deletion.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Create a private 10 GB bucket
  pidginhost.cloud.bucket:
    name: media
    quota_gb: 10

- name: Grow the bucket and make it public
  pidginhost.cloud.bucket:
    name: media
    quota_gb: 20
    public_read: true

- name: Delete the bucket
  pidginhost.cloud.bucket:
    name: media
    state: absent
"""

RETURN = r"""
bucket:
  description:
    - Bucket details. After deletion, the details before deletion. Empty when the bucket does not exist.
  returned: success
  type: dict
  sample:
    id: 5
    name: media
    full_name: c1001-media
    quota_gb: 10
    used_bytes: 0
    object_count: 0
    public_read: false
    status: active
    endpoint: https://s3.example.com
    region: default
    created: "2026-01-01T10:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, pidginhost_argument_spec

BUCKETS = "/api/cloud/buckets/"
# The API hides cancelled and terminated buckets but keeps listing these until the deletion completes.
DELETING = ("cancelling", "terminating")


def find(api, name):
    return api.find_one(api.list(BUCKETS), "buckets", name=name)


def wait_active(api, module, bucket):
    if not module.params["wait"] or bucket["status"] == "active":
        return bucket
    done = api.wait_for(lambda: api.get("%s%s/" % (BUCKETS, bucket["id"])),
                        lambda b: b["status"] in ("active", "failed"))
    if not done or done["status"] != "active":
        module.fail_json(
            changed=True,
            msg="Bucket %s %s." % (bucket["name"], "failed" if done else "did not become active in time"),
            bucket=done or bucket,
        )
    return done


def create(api, module):
    params = module.params
    if params["quota_gb"] is None:
        module.fail_json(msg="Creating a bucket requires: quota_gb")
    if module.check_mode:
        module.exit_json(changed=True, bucket={})
    bucket = api.post(BUCKETS, drop_none(dict((k, params[k]) for k in ("name", "quota_gb", "public_read"))))
    module.exit_json(changed=True, bucket=wait_active(api, module, bucket))


def update(api, module, bucket):
    params = module.params
    if bucket["status"] in DELETING:
        module.fail_json(msg="Bucket %s is being deleted. Run again once it is gone." % bucket["name"], bucket=bucket)
    resize = params["quota_gb"] is not None and params["quota_gb"] != bucket["quota_gb"]
    visibility = params["public_read"] is not None and params["public_read"] != bucket["public_read"]
    if not (resize or visibility):
        module.exit_json(changed=False, bucket=bucket)
    if module.check_mode:
        module.exit_json(changed=True, bucket=bucket)

    path = "%s%s/" % (BUCKETS, bucket["id"])
    if resize:
        bucket = api.post(path + "resize/", {"quota_gb": params["quota_gb"]})
    if visibility:
        bucket = api.post(path + "visibility/", {"public_read": params["public_read"]})
    module.exit_json(changed=True, bucket=wait_active(api, module, bucket))


def delete(api, module, bucket):
    changed = bucket["status"] not in DELETING
    if module.check_mode:
        module.exit_json(changed=changed, bucket=bucket)
    if changed:
        api.delete("%s%s/" % (BUCKETS, bucket["id"]))
    if module.params["wait"]:
        status = api.wait_for(lambda: (find(api, bucket["name"]) or {"status": "gone"})["status"],
                              lambda s: s not in DELETING)
        if status not in ("gone", "cancelled", "terminated"):
            reason = "was not deleted in time" if status is None else "failed to delete"
            module.fail_json(changed=changed, msg="Bucket %s %s." % (bucket["name"], reason), bucket=bucket)
    module.exit_json(changed=changed, bucket=bucket)


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            name=dict(type="str", required=True),
            quota_gb=dict(type="int"),
            public_read=dict(type="bool"),
            wait=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    bucket = find(api, module.params["name"])

    if module.params["state"] == "absent":
        if not bucket:
            module.exit_json(changed=False, bucket={})
        delete(api, module, bucket)
    elif bucket:
        update(api, module, bucket)
    else:
        create(api, module)


if __name__ == "__main__":
    main()
