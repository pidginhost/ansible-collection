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
- The API token is no longer sent to another host when a request is redirected.
- Reboots and package changes report success only once they have finished.
- A failed task still reports the changes it made before the error.
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
