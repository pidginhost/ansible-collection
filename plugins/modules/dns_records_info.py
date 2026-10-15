# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_records_info

short_description: List the records of a FreeDNS zone.

version_added: 0.4.0

description:
  - List the A, AAAA, CAA, CNAME, MX, SRV and TXT records of a domain with FreeDNS hosting active.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/freedns/freedns_dns_records_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  domain:
    description:
      - Domain name of the zone, for example V(example.com).
    type: str
    required: true
  source:
    description:
      - V(internal) for a domain registered with PidginHost, V(external) for a domain added in the PidginHost panel.
    type: str
    choices: [internal, external]
    default: internal
  name:
    description:
      - Return only records with this name. A label relative to the zone such as V(www), V(@) or an empty string
        for the zone apex, or a fully qualified name.
    type: str
  type:
    description:
      - Return only records of this type.
    type: str
    choices: [A, AAAA, CAA, CNAME, MX, SRV, TXT]
"""

EXAMPLES = r"""
- name: List the MX records of a zone
  pidginhost.cloud.dns_records_info:
    domain: example.com
    name: "@"
    type: MX
  register: result
"""

RETURN = r"""
records:
  description:
    - Zone records, ordered by line.
    - C(name) is fully qualified with a trailing dot. CAA records have C(type=TYPE257).
    - C(Line) is the position of the record in the zone file. It changes when records above it are deleted.
  returned: success
  type: list
  elements: dict
  sample:
    - Line: 13
      name: www.example.com.
      ttl: 14400
      type: A
      address: 192.0.2.10
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, dns_record_name, fqdn, pidginhost_argument_spec

RECORD_TYPES = ["A", "AAAA", "CAA", "CNAME", "MX", "SRV", "TXT"]


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            domain=dict(type="str", required=True),
            source=dict(type="str", choices=["internal", "external"], default="internal"),
            name=dict(type="str"),
            type=dict(type="str", choices=RECORD_TYPES),
        ),
        supports_check_mode=True,
    )
    params = module.params
    domain = fqdn(params["domain"])
    api = PidginHostAPI(module)
    query = {"domain": api.freedns_domain(domain, params["source"]), "source": params["source"]}
    records = api.list("/api/freedns/dns/records/", **query)
    if params["name"] is not None:
        name = dns_record_name(params["name"], domain)
        records = [r for r in records if r["name"].lower() == name]
    if params["type"]:
        rtype = "TYPE257" if params["type"] == "CAA" else params["type"]
        records = [r for r in records if r["type"] == rtype]
    module.exit_json(changed=False, records=records)


if __name__ == "__main__":
    main()
