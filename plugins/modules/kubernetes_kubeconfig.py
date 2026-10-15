# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_kubeconfig

short_description: Read or regenerate the kubeconfig of a Kubernetes cluster.

version_added: 0.4.0

description:
  - Return the kubeconfig of a PidginHost Kubernetes cluster.
  - With O(regenerate=true), generate a new kubeconfig and return it. This always reports a change.
  - The kubeconfig holds cluster admin credentials. Set C(no_log) on the task that registers the result and on any
    task that uses it.
  - Failed requests report the HTTP status without the response body, which may contain credentials.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_kubeconfig_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  cluster_id:
    description:
      - ID of the cluster.
    type: int
  cluster_name:
    description:
      - Name of the cluster. Must be unique in the account.
    type: str
  regenerate:
    description:
      - Generate a new kubeconfig instead of reading the current one.
      - In check mode, the current kubeconfig is returned and nothing is generated.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Read the kubeconfig
  pidginhost.cloud.kubernetes_kubeconfig:
    cluster_name: prod
  register: prod_kubeconfig
  no_log: true

- name: Save it for kubectl
  ansible.builtin.copy:
    content: "{{ prod_kubeconfig.kubeconfig }}"
    dest: ~/.kube/prod.yaml
    mode: "0600"
  no_log: true
"""

RETURN = r"""
kubeconfig:
  description:
    - The kubeconfig file content, in YAML. Contains credentials.
  returned: success
  type: str
  sample: |
    apiVersion: v1
    kind: Config
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            regenerate=dict(type="bool", default=False),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        mutually_exclusive=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module, sensitive=True)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/kubeconfig/" % (CLUSTERS, cluster["id"])
    # The endpoint only answers text/plain; GET reads the current file and POST replaces it.
    if params["regenerate"] and not module.check_mode:
        config = api.post(path, accept="text/plain")
    else:
        config = api.get(path, accept="text/plain")
    module.exit_json(changed=params["regenerate"], kubeconfig=config or "")


if __name__ == "__main__":
    main()
