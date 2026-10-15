# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_lb_firewall

short_description: Manage the firewall rules of a Kubernetes cluster load balancer.

version_added: 0.4.0

description:
  - Manage the firewall rules on the public interface of a PidginHost Kubernetes cluster load balancer.
  - A rule is identified by its direction, action, protocol, source, sport, destination and dport. A listed rule
    that is missing is added. A matching rule is updated when its O(rules[].comment), O(rules[].enabled) or
    O(rules[].position) differ.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_lb_firewall_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  cluster_id:
    description:
      - ID of the Kubernetes cluster. Takes precedence over O(cluster_name).
    type: int
  cluster_name:
    description:
      - Name of the Kubernetes cluster. Used when O(cluster_id) is not set, so it must be unique in the account.
    type: str
  rules:
    description:
      - Rules the load balancer should have.
    type: list
    elements: dict
    suboptions:
      direction:
        description:
          - Traffic direction.
        type: str
        required: true
        choices: [in, out]
      action:
        description:
          - Action for matching traffic.
        type: str
        required: true
        choices: [ACCEPT, DROP, REJECT]
      protocol:
        description:
          - Protocol, for example V(tcp), V(udp) or V(icmp). Required when O(rules[].sport) or O(rules[].dport)
            is set.
        type: str
      source:
        description:
          - Source IP address or CIDR.
        type: str
      sport:
        description:
          - Source port or range, for example V(1024-65535).
        type: str
      destination:
        description:
          - Destination IP address or CIDR.
        type: str
      dport:
        description:
          - Destination port or range, for example V(80) or V(8000-9000).
        type: str
      comment:
        description:
          - Free text comment. Not compared when not set.
        type: str
      enabled:
        description:
          - Whether the rule is active.
        type: bool
        default: true
      position:
        description:
          - Rule order, lower runs first. The API uses V(100) when not set on creation. Not compared when not set.
        type: int
  purge_rules:
    description:
      - Delete rules that are not listed in O(rules).
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Allow HTTP and HTTPS, drop every other rule
  pidginhost.cloud.kubernetes_lb_firewall:
    cluster_name: prod
    purge_rules: true
    rules:
      - direction: in
        action: ACCEPT
        protocol: tcp
        dport: "80"
      - direction: in
        action: ACCEPT
        protocol: tcp
        dport: "443"
        comment: web

- name: Allow SSH from one network
  pidginhost.cloud.kubernetes_lb_firewall:
    cluster_name: prod
    rules:
      - direction: in
        action: ACCEPT
        protocol: tcp
        dport: "22"
        source: 203.0.113.0/24
"""

RETURN = r"""
rules:
  description:
    - Load balancer firewall rules after the changes.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 1
      direction: in
      action: ACCEPT
      protocol: tcp
      source: ""
      sport: ""
      destination: ""
      dport: "443"
      comment: web
      enabled: true
      position: 100
      created: "2026-01-01T10:00:00Z"
      updated: "2026-01-01T10:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, drop_none, pidginhost_argument_spec, plan_rules

MATCH_FIELDS = ("direction", "action", "protocol", "source", "sport", "destination", "dport")


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            rules=dict(
                type="list",
                elements="dict",
                options=dict(
                    direction=dict(type="str", required=True, choices=["in", "out"]),
                    action=dict(type="str", required=True, choices=["ACCEPT", "DROP", "REJECT"]),
                    protocol=dict(type="str"),
                    source=dict(type="str"),
                    sport=dict(type="str"),
                    destination=dict(type="str"),
                    dport=dict(type="str"),
                    comment=dict(type="str"),
                    enabled=dict(type="bool", default=True),
                    position=dict(type="int"),
                ),
            ),
            purge_rules=dict(type="bool", default=False),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    desired = module.params["rules"] or []
    for rule in desired:
        if (rule["sport"] or rule["dport"]) and not rule["protocol"]:
            module.fail_json(msg="Firewall rule %s sets a port without a protocol." % drop_none(rule))

    api = PidginHostAPI(module)
    cluster = api.require_cluster(module.params["cluster_id"], module.params["cluster_name"])
    path = "%s%s/lb-firewall/" % (CLUSTERS, cluster["id"])
    existing = api.list(path)
    create, patch, delete = plan_rules(
        existing, desired, MATCH_FIELDS, ("comment", "enabled", "position"), module.params["purge_rules"])
    if not (create or patch or delete):
        module.exit_json(changed=False, rules=existing)
    if module.check_mode:
        module.exit_json(changed=True, rules=existing)

    for rule in delete:
        api.delete("%s%s/" % (path, rule["id"]))
    for rule_id, changes in patch:
        api.patch("%s%s/" % (path, rule_id), changes)
    for rule in create:
        api.post(path, rule)
    module.exit_json(changed=True, rules=api.list(path))


if __name__ == "__main__":
    main()
