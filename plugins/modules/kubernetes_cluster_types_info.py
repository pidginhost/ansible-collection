# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_cluster_types_info

short_description: List Kubernetes cluster types.

version_added: 0.4.0

description:
  - List the PidginHost Kubernetes cluster types, their worker node limits and worker node packages.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_cluster_types_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List cluster types
  pidginhost.cloud.kubernetes_cluster_types_info:
  register: result
"""

RETURN = r"""
cluster_types:
  description:
    - Every cluster type available to the account.
  returned: success
  type: list
  elements: dict
  sample:
    - type: prod
      worker_nodes_count_min: 3
      worker_nodes_count_max: 10
      worker_node_packages:
        - id: 1
          slug: k8s-w2
          name: Worker 2
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(argument_spec=pidginhost_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, cluster_types=PidginHostAPI(module).list("/api/kubernetes/cluster-types/"))


if __name__ == "__main__":
    main()
