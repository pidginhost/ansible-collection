# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  token:
    description:
      - PidginHost API token.
      - Read from the C(PIDGINHOST_ACCESS_TOKEN) or C(PIDGINHOST_TOKEN) environment variable when not set.
    type: str
    required: true
  timeout:
    description:
      - Seconds to wait for an API request, and for long running operations when the module waits for them.
    type: int
    default: 300
"""

    INFO = r"""
options:
  state:
    description:
      - Ignored. Accepted so playbooks written for earlier releases keep working.
    type: str
"""
