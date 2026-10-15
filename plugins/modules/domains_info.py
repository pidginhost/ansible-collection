# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domains_info

short_description: List registered domains.

version_added: 0.4.0

description:
  - List the domains registered with PidginHost in the account, ordered by expiration date.
  - Contact data is left out.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/domain/domain_domain_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  status_group:
    description:
      - V(current) lists domains whose service is not cancelled or terminated. V(closed) lists only those.
      - Every domain is listed when not set.
    type: str
    choices: [current, closed]
  domain:
    description:
      - Return only this domain, for example V(example.com).
    type: str
"""

EXAMPLES = r"""
- name: List current domains
  pidginhost.cloud.domains_info:
    status_group: current
  register: result

- name: Get one domain
  pidginhost.cloud.domains_info:
    domain: example.com
  register: result
"""

RETURN = r"""
domains:
  description:
    - Domains. C(domain) is the name without the TLD, C(idna_name) the full ASCII name.
    - C(nameservers) is a comma separated string.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 12
      domain: example
      idna_name: example.com
      tld:
        tld: com
      nameservers: ns1.external.example.com,ns2.external.example.com
      expiration_date: "2027-01-31"
      service_status: Active
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, fqdn, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            status_group=dict(type="str", choices=["current", "closed"]),
            domain=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    domains = PidginHostAPI(module, sensitive=True).list(
        "/api/domain/domain/", **drop_none({"status_group": params["status_group"]}))
    if params["domain"]:
        domains = [d for d in domains if fqdn(d["idna_name"]) == fqdn(params["domain"])]
    for domain in domains:
        domain.pop("contacts", None)  # personal data
    module.exit_json(changed=False, domains=domains)


if __name__ == "__main__":
    main()
