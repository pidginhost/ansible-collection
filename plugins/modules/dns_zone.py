# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_zone

short_description: Activate or deactivate FreeDNS hosting for a domain.

version_added: 0.4.0

description:
  - Activate or deactivate PidginHost FreeDNS hosting for a domain.
  - Activating an V(internal) domain also points its nameservers at the PidginHost nameservers. Deactivating it
    restores the nameservers it had before. Do not manage the same domain with M(pidginhost.cloud.domain_nameservers).
  - Activation creates the zone with a default A record for O(ip). Use M(pidginhost.cloud.dns_record) to manage
    records.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/freedns/freedns_dns_activate_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether FreeDNS hosting should be active for the domain.
    type: str
    choices: [present, absent]
    default: present
  domain:
    description:
      - Domain name, for example V(example.com).
    type: str
    required: true
  source:
    description:
      - V(internal) for a domain registered with PidginHost, V(external) for a domain added to the account in the
        PidginHost panel.
    type: str
    choices: [internal, external]
    default: internal
  ip:
    description:
      - IPv4 address for the default A record of a new zone.
      - Required to activate the zone. Not compared on an active zone.
    type: str
"""

EXAMPLES = r"""
- name: Host the DNS of a domain on FreeDNS
  pidginhost.cloud.dns_zone:
    domain: example.com
    ip: 192.0.2.10

- name: Stop hosting an external domain
  pidginhost.cloud.dns_zone:
    domain: external.example.com
    source: external
    state: absent
"""

RETURN = r"""
zone:
  description:
    - The FreeDNS zone. After deactivation, the zone before deactivation.
    - Empty when O(state=absent) and the zone was not active.
  returned: success
  type: dict
  sample:
    domain: example.com
    active: true
    source: internal
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, fqdn, pidginhost_argument_spec

ZONES = "/api/freedns/dns/"


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            domain=dict(type="str", required=True),
            source=dict(type="str", choices=["internal", "external"], default="internal"),
            ip=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    domain, source = fqdn(params["domain"]), params["source"]
    api = PidginHostAPI(module)
    zone = next(
        (z for z in api.list(ZONES) if fqdn(z["domain"]) == domain and z["source"] == source and z["active"]), None)

    if params["state"] == "absent":
        if not zone:
            module.exit_json(changed=False, zone={})
        body = {"domain": api.freedns_domain(domain, source), "source": source}
        if not module.check_mode:
            api.post(ZONES + "deactivate/", body)
        module.exit_json(changed=True, zone=zone)

    if zone:
        module.exit_json(changed=False, zone=zone)
    if not params["ip"]:
        module.fail_json(msg="Activating the FreeDNS zone of %s requires ip." % domain)
    body = {"domain": api.freedns_domain(domain, source), "source": source, "ip": params["ip"]}
    if not module.check_mode:
        domain = api.post(ZONES + "activate/", body).get("domain", domain)
    module.exit_json(changed=True, zone={"domain": domain, "active": True, "source": source})


if __name__ == "__main__":
    main()
