# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_route

short_description: Manage Gateway API routes of a Kubernetes cluster.

version_added: 0.4.0

description:
  - Create, update or delete an HTTP, TCP or UDP route that exposes a Kubernetes Service through the cluster
    gateway.
  - The route is identified by O(protocol), O(name) and O(namespace). Other routes are never changed, including
    the route the platform keeps for the Kubernetes API.
  - An existing route is updated in place for the options that are set and differ. Options that are not set are
    not compared.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_httproutes_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the route should exist.
    type: str
    choices: [present, absent]
    default: present
  cluster_id:
    description:
      - ID of the Kubernetes cluster. Takes precedence over O(cluster_name).
    type: int
  cluster_name:
    description:
      - Name of the Kubernetes cluster. Used when O(cluster_id) is not set, so it must be unique in the account.
    type: str
  protocol:
    description:
      - Route type. V(http) routes match host names, V(tcp) and V(udp) routes expose an external port.
    type: str
    choices: [http, tcp, udp]
    required: true
  name:
    description:
      - Route name.
    type: str
    required: true
  namespace:
    description:
      - Namespace of the route.
    type: str
    default: default
  hostnames:
    description:
      - Host names the route matches. Compared as a set. Required to create an V(http) route.
      - Only valid with O(protocol=http).
    type: list
    elements: str
  path_prefix:
    description:
      - Path prefix the route matches. The API uses V(/) when not set on creation.
      - Only valid with O(protocol=http).
    type: str
  enable_tls:
    description:
      - Terminate TLS with an automatically issued certificate. The API enables it when not set on creation.
      - Only valid with O(protocol=http).
    type: bool
  port:
    description:
      - External port to expose. Required to create a V(tcp) or V(udp) route.
      - The API refuses the reserved TCP ports 22, 6443, 50000 and 50001.
      - Only valid with O(protocol=tcp) or O(protocol=udp).
    type: int
  backend_service_name:
    description:
      - Name of the backend Service. Required to create a route.
    type: str
  backend_service_port:
    description:
      - Port of the backend Service. Required to create a route.
    type: int
  backend_namespace:
    description:
      - Namespace of the backend Service. The API uses V(default) when not set on creation.
    type: str
"""

EXAMPLES = r"""
- name: Expose a web Service over HTTPS
  pidginhost.cloud.kubernetes_route:
    cluster_name: prod
    protocol: http
    name: web
    hostnames:
      - example.com
      - www.example.com
    backend_service_name: web
    backend_service_port: 80

- name: Expose a TCP Service on port 5432
  pidginhost.cloud.kubernetes_route:
    cluster_name: prod
    protocol: tcp
    name: postgres
    namespace: db
    port: 5432
    backend_service_name: postgres
    backend_service_port: 5432
    backend_namespace: db

- name: Delete a route
  pidginhost.cloud.kubernetes_route:
    cluster_name: prod
    protocol: tcp
    name: postgres
    namespace: db
    state: absent
"""

RETURN = r"""
route:
  description:
    - Route details. After deletion, the details before deletion. Empty when the route does not exist.
    - HTTP routes carry O(hostnames), O(path_prefix) and O(enable_tls), TCP and UDP routes carry O(port).
  returned: success
  type: dict
  sample:
    id: 4
    name: web
    namespace: default
    hostnames:
      - example.com
    backend_service_name: web
    backend_service_port: 80
    backend_namespace: default
    path_prefix: /
    enable_tls: true
    status_ready: true
    status_message: ""
    created: "2026-01-01T10:00:00Z"
    updated: "2026-01-01T10:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec

OWN_FIELDS = {"http": ("hostnames", "path_prefix", "enable_tls"), "tcp": ("port",), "udp": ("port",)}
BACKEND_FIELDS = ("backend_service_name", "backend_service_port", "backend_namespace")
CREATE_REQUIRED = {"http": "hostnames", "tcp": "port", "udp": "port"}


def differs(key, wanted, current):
    if key == "hostnames":
        return set(wanted) != set(current or [])
    return wanted != current


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            protocol=dict(type="str", choices=["http", "tcp", "udp"], required=True),
            name=dict(type="str", required=True),
            namespace=dict(type="str", default="default"),
            hostnames=dict(type="list", elements="str"),
            path_prefix=dict(type="str"),
            enable_tls=dict(type="bool"),
            port=dict(type="int"),
            backend_service_name=dict(type="str"),
            backend_service_port=dict(type="int"),
            backend_namespace=dict(type="str"),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    protocol = params["protocol"]
    wrong = [k for k in ("hostnames", "path_prefix", "enable_tls", "port")
             if k not in OWN_FIELDS[protocol] and params[k] is not None]
    if wrong:
        module.fail_json(msg="Not valid with protocol=%s: %s" % (protocol, ", ".join(wrong)))

    api = PidginHostAPI(module)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/%sroutes/" % (CLUSTERS, cluster["id"], protocol)
    route = api.find_one(api.list(path), "%s routes" % protocol, name=params["name"], namespace=params["namespace"])

    if params["state"] == "absent":
        if not route:
            module.exit_json(changed=False, route={})
        if not module.check_mode:
            api.delete("%s%s/" % (path, route["id"]))
        module.exit_json(changed=True, route=route)

    desired = dict((k, params[k]) for k in OWN_FIELDS[protocol] + BACKEND_FIELDS if params[k] is not None)
    if not route:
        missing = [k for k in (CREATE_REQUIRED[protocol], "backend_service_name", "backend_service_port")
                   if k not in desired]
        if missing:
            module.fail_json(msg="Creating a %s route requires: %s" % (protocol, ", ".join(missing)))
        if module.check_mode:
            module.exit_json(changed=True, route={})
        module.exit_json(changed=True, route=api.post(path, dict(desired, name=params["name"],
                                                                 namespace=params["namespace"])))

    changes = dict((k, v) for k, v in desired.items() if differs(k, v, route.get(k)))
    if not changes:
        module.exit_json(changed=False, route=route)
    if module.check_mode:
        module.exit_json(changed=True, route=route)
    module.exit_json(changed=True, route=api.patch("%s%s/" % (path, route["id"]), changes))


if __name__ == "__main__":
    main()
