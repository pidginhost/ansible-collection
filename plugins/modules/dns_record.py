# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_record

short_description: Manage a record in a FreeDNS zone.

version_added: 0.4.0

description:
  - Add, update or delete a record in a domain with FreeDNS hosting active. See M(pidginhost.cloud.dns_zone).
  - A record is identified by its O(name), O(type) and the value options of its type. A record with the same
    identity and a different O(ttl) is updated in place. A record with other values is a different record and is
    kept unless O(solo=true).
  - Value options by type. V(A) and V(AAAA) use O(address). V(CNAME) uses O(cname). V(MX) uses O(preference) and
    O(exchange). V(SRV) uses O(priority), O(weight), O(port) and O(target). V(TXT) uses O(txtdata). V(CAA) uses
    O(flag), O(tag) and O(value).
  - Host names in O(cname), O(exchange) and O(target) are compared without the trailing dot and case.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/freedns/freedns_dns_add_record_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the record should exist.
      - With V(absent), every record with the O(name) and O(type) whose values match the value options that are set
        is deleted. Without value options, every record with the O(name) and O(type) is deleted.
    type: str
    choices: [present, absent]
    default: present
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
      - Record name. A label relative to the zone such as V(www), V(@) or an empty string for the zone apex, or a
        fully qualified name such as V(www.example.com).
      - Internationalized names are converted to their ASCII DNS form.
    type: str
    required: true
  type:
    description:
      - Record type.
    type: str
    required: true
    choices: [A, AAAA, CAA, CNAME, MX, SRV, TXT]
  ttl:
    description:
      - Time to live in seconds.
    type: int
    default: 14400
  solo:
    description:
      - Delete every other record with the same O(name) and O(type).
      - When the requested value is missing, replace the last matching record before deleting the others.
    type: bool
    default: false
  address:
    description:
      - IP address of an V(A) or V(AAAA) record.
    type: str
  cname:
    description:
      - Target host name of a V(CNAME) record.
    type: str
  exchange:
    description:
      - Mail server host name of an V(MX) record.
    type: str
  preference:
    description:
      - Preference of an V(MX) record.
    type: int
  txtdata:
    description:
      - Text of a V(TXT) record, without quotes.
    type: str
  target:
    description:
      - Target host name of an V(SRV) record.
    type: str
  priority:
    description:
      - Priority of an V(SRV) record.
    type: int
  weight:
    description:
      - Weight of an V(SRV) record.
    type: int
  port:
    description:
      - Port of an V(SRV) record.
    type: int
  flag:
    description:
      - Flag of a V(CAA) record.
    type: int
  tag:
    description:
      - Tag of a V(CAA) record, for example V(issue).
    type: str
  value:
    description:
      - Value of a V(CAA) record, for example V(ca.example.com).
    type: str
"""

EXAMPLES = r"""
- name: Point www at a server
  pidginhost.cloud.dns_record:
    domain: example.com
    name: www
    type: A
    address: 192.0.2.10
    solo: true

- name: Add a mail server
  pidginhost.cloud.dns_record:
    domain: example.com
    name: "@"
    type: MX
    preference: 10
    exchange: mail.example.com

- name: Publish an SPF policy
  pidginhost.cloud.dns_record:
    domain: example.com
    name: "@"
    type: TXT
    txtdata: v=spf1 mx -all

- name: Delete every AAAA record of www
  pidginhost.cloud.dns_record:
    domain: example.com
    name: www
    type: AAAA
    state: absent
"""

RETURN = r"""
record:
  description:
    - The record after the change. Empty when O(state=absent).
    - In check mode, the requested record without C(Line).
  returned: success
  type: dict
  sample:
    Line: 13
    name: www.example.com.
    ttl: 14400
    type: A
    address: 192.0.2.10
records:
  description:
    - Every record with the O(name) and O(type) after the change. In check mode, before the change.
    - C(name) is fully qualified with a trailing dot. CAA records have C(type=TYPE257).
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

import ipaddress

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, dns_record_name, fqdn, pidginhost_argument_spec

FREEDNS = "/api/freedns/dns/"
TYPE_FIELDS = {
    "A": ("address",),
    "AAAA": ("address",),
    "CAA": ("flag", "tag", "value"),
    "CNAME": ("cname",),
    "MX": ("preference", "exchange"),
    "SRV": ("priority", "weight", "port", "target"),
    "TXT": ("txtdata",),
}
VALUE_FIELDS = sorted(set(f for fields in TYPE_FIELDS.values() for f in fields))
HOST_FIELDS = ("cname", "exchange", "target")


def normalize(field, value):
    """Compare values as strings: the API returns some numbers as strings and host names without the dot."""
    value = "" if value is None else str(value)
    if field in HOST_FIELDS:
        return value.rstrip(".").lower()
    if field == "address":
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
    return value


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            domain=dict(type="str", required=True),
            source=dict(type="str", choices=["internal", "external"], default="internal"),
            name=dict(type="str", required=True),
            type=dict(type="str", required=True, choices=sorted(TYPE_FIELDS)),
            ttl=dict(type="int", default=14400),
            solo=dict(type="bool", default=False),
            address=dict(type="str"),
            cname=dict(type="str"),
            exchange=dict(type="str"),
            preference=dict(type="int"),
            txtdata=dict(type="str"),
            target=dict(type="str"),
            priority=dict(type="int"),
            weight=dict(type="int"),
            port=dict(type="int"),
            flag=dict(type="int"),
            tag=dict(type="str"),
            value=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    present = params["state"] == "present"
    fields = TYPE_FIELDS[params["type"]]
    extra = [f for f in VALUE_FIELDS if params[f] is not None and f not in fields]
    if extra:
        module.fail_json(msg="%s records do not use %s." % (params["type"], ", ".join(extra)))
    missing = [f for f in fields if params[f] is None]
    if present and missing:
        module.fail_json(msg="A %s record requires %s." % (params["type"], ", ".join(missing)))

    domain = fqdn(params["domain"])
    name = dns_record_name(params["name"], domain)
    rtype = "TYPE257" if params["type"] == "CAA" else params["type"]
    ttl = params["ttl"]
    given = dict((f, params[f]) for f in fields if params[f] is not None)
    api = PidginHostAPI(module)
    query = {"domain": api.freedns_domain(domain, params["source"]), "source": params["source"]}

    def same_name_and_type():
        records = api.list(FREEDNS + "records/", **query)
        return [r for r in records if r["name"].lower() == name and r["type"] == rtype]

    def matches(record):
        return all(normalize(f, record.get(f)) == normalize(f, v) for f, v in given.items())

    current = same_name_and_type()
    found = [r for r in current if matches(r)]
    body, keep, add = {}, None, False
    if present:
        body = dict(name=name, ttl=ttl, type=rtype, **given)
        if rtype == "TXT":
            body["unencoded"] = "1"
        keep = next((r for r in found if str(r["ttl"]) == str(ttl)), found[0] if found else None)
        if keep is None and params["solo"] and current:
            # Replace before deleting anything. A rejected value must not wipe out the existing records.
            keep = max(current, key=lambda r: r["Line"])
        add = keep is None
        # (line, add-record body to edit the record in place, or None to delete it)
        edit = keep and (not matches(keep) or str(keep["ttl"]) != str(ttl))
        ops = [(keep["Line"], dict(body, line=keep["Line"]))] if edit else []
        if params["solo"]:
            ops.extend((r["Line"], None) for r in current if r is not keep)
    else:
        ops = [(r["Line"], None) for r in found]

    if not (ops or add):
        module.exit_json(changed=False, record=keep or {}, records=current)
    if module.check_mode:
        module.exit_json(changed=True, record=body, records=current)

    # A delete renumbers every later line: work from the last line up so the pending line numbers stay valid.
    for line, edit in sorted(ops, key=lambda op: op[0], reverse=True):
        if edit:
            api.post(FREEDNS + "add-record/", edit, query=query)
        else:
            api.post(FREEDNS + "delete-record/", {"line": line}, query=query)
    if add:
        api.post(FREEDNS + "add-record/", body, query=query)

    after = same_name_and_type()
    record = next((r for r in after if matches(r) and str(r["ttl"]) == str(ttl)), {}) if present else {}
    module.exit_json(changed=True, record=record, records=after)


if __name__ == "__main__":
    main()
