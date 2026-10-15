# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domain_nameservers

short_description: Set the nameservers of a registered domain.

version_added: 0.4.0

description:
  - Set the nameservers of a domain registered with PidginHost.
  - Nameservers are compared without case, order and trailing dot. The registry is updated only when they differ.
  - The domain service must be active or pending cancellation.
  - Activating FreeDNS with M(pidginhost.cloud.dns_zone) also changes the nameservers. Do not manage the same domain
    with both modules.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/domain/domain_domain_nameservers_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  domain:
    description:
      - Domain name, for example V(example.com).
    type: str
    required: true
  nameservers:
    description:
      - Nameserver host names. Two to five.
    type: list
    elements: str
    required: true
"""

EXAMPLES = r"""
- name: Delegate a domain to external nameservers
  pidginhost.cloud.domain_nameservers:
    domain: example.com
    nameservers:
      - ns1.example.net
      - ns2.example.net
"""

RETURN = r"""
domain:
  description:
    - Domain details with the nameservers after the change, as a list. Contact data is left out.
  returned: success
  type: dict
  sample:
    id: 12
    domain: example
    idna_name: example.com
    tld:
      tld: com
    expiration_date: "2027-01-31"
    nameservers:
      - ns1.example.net
      - ns2.example.net
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, fqdn, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            domain=dict(type="str", required=True),
            nameservers=dict(type="list", elements="str", required=True),
        ),
        supports_check_mode=True,
    )
    wanted = [ns.strip().rstrip(".") for ns in module.params["nameservers"] if ns.strip()]
    if not 2 <= len(wanted) <= 5:
        module.fail_json(msg="nameservers needs 2 to 5 host names, got %d." % len(wanted))

    domain = fqdn(module.params["domain"])
    path = "/api/domain/domain/%s/" % domain
    api = PidginHostAPI(module)
    detail = api.get(path, allow_404=True)
    if not detail:
        module.fail_json(msg="Domain %s not found in the account." % domain)
    detail.pop("contacts", None)  # personal data
    current = [ns.strip() for ns in (detail.get("nameservers") or "").split(",") if ns.strip()]
    detail["nameservers"] = current

    if set(fqdn(ns) for ns in current) == set(fqdn(ns) for ns in wanted):
        module.exit_json(changed=False, domain=detail)
    if not module.check_mode:
        api.post(path + "nameservers/", {"nameservers": wanted})
    detail["nameservers"] = wanted
    module.exit_json(changed=True, domain=detail)


if __name__ == "__main__":
    main()
