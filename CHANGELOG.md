# Changelog

## [Unreleased]

### Added
- New modules manage server snapshots, rescue mode, public IP allocation and reverse DNS, floating IPs, private networks and object storage buckets.
- New info modules list hardware generations, floating IPs, private networks and buckets.
- Servers can be created with a startup script, a hardware generation and high availability, and protected from deletion.
- Server packages can be filtered by hardware generation.

### Changed
- Every module reports no change when the resource already matches, and changes nothing in check mode.
- The inventory sets each host's login user from its server image.
- Requires ansible-core 2.16 or later and works with the latest Ansible release.

### Fixed
- Dry runs leave bucket credentials unread and make no account changes.
- Reboots, snapshot restores and package changes no longer report success before completion.
- Repeated tasks wait for pending operations without requesting duplicate changes.
- Ambiguous server names and invalid private addresses no longer risk unintended disconnections.
- New servers cannot silently skip requested deletion protection.
- Invalid server hostnames no longer leave newly allocated floating IPs behind.
- API authentication tokens stay private during redirected requests.
- Failed cloud operations report changes already completed before the error.
- Inventory connection timeouts now produce readable errors.
- Accounts with many servers, IPs, images or SSH keys now see all of them instead of only the first page.
- Module documentation loads again with ansible-doc.
- Reading a server's public IP no longer crashes.
- The inventory reports API errors instead of crashing, and the sample inventory no longer sets an invalid host address.
- The sample Ansible configuration works with current Ansible releases.
- The published collection no longer includes local cache and log files.

### Breaking
- The server module finds servers by hostname or ID and no longer creates duplicates; the old unique hostname option is ignored.
- The firewall module manages a rules set and its full rule list; creating a set no longer needs a separate flag.
- Managing several SSH keys at once uses a list option instead of a list written as text.
- Info modules return a plain list of every item instead of one item or a page with paging fields.
