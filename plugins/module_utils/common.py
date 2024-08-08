# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

import requests
import ipaddress
from ansible.module_utils.basic import env_fallback
import json
import logging


class PidginHostsConstants:
    BASE_URL = 'https://www.pidginhost.com/'
    FIREWALL_RULES_SET_ENDPOINT = "api/cloud/firewall-rules-set/"
    ACCOUNT_PROFILE_ENDPOINT = 'api/account/profile'
    CLOUD_IMAGE_ENDPOINT = "api/cloud/images"
    CLOUD_PACKAGES_ENDPOINT = "api/cloud/server-packages/"
    CLOUD_SERVERS_ENDPOINT = "api/cloud/servers/"
    SSH_KEYS_ENDPOINT = "api/account/ssh-keys/"
    CLOUD_IPV4_ENDPOINT = "api/cloud/ipv4/"
    POWER_MANAGEMENT = "/power-management/"
    VOLUMES_ENDPOINT = "api/cloud/volumes/"
    STORAGE_PRODUCT_ENDPOINT = "api/cloud/storage-products/"
    IPV4_ENDPOINT = "api/cloud/ipv4/"
    IPV6_ENDPOINT = "api/cloud/ipv6/"
    DETACH = "/detach/"
    ATTACHE = "/attach/"
    VOLUMES = "/volumes/"
    RULES = "/rules/"
    ATTACH_IPV4 = "/attach-ipv4/"
    ATTACH_IPV6 = "/attach-ipv6/"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    MODIFY_PACKAGES = "/modify-package/"
    PUBLIC_INTERFACE = "/public-interface/"
    PH_DEFAULT_USER = "phuser"
    SLEEP = 5
    DPORT_MAX_LENGTH = 500
    DESTINATION_MAX_LENGTH = 500
    SPORT_MAX_LENGTH = 500
    PROTOCOL_MAX_LENGTH = 100
    SOURCE_MAX_LENGTH = 500
    VOLUME_ALIAS_MAX_LENGTH = 50
    HOST_NAME_MAX_LENGTH = 253
    PROJECT_NAME_MAX_LENGTH = 200
    PASSWORD_MAX_LENGTH = 50
    SSH_PUB_KEY_MAX_LENGTH = 3000
    SSH_PUB_KEY_ID_LENGTH = 100
    FIREWALL_NAME_MAX_LENGTH = 200
    SUCCESS_CODE = 200
    ERROR_CODES = [400, 404, 500]
    CREATE_SERVER_SUCCESS_CODE = 201
    DELETE_SUCCESS_CODE = 204
    ADD_SUCCESS_CODE = 201
    REQUIRED_MAX_LENGTH_PARAMS = {"hostname": HOST_NAME_MAX_LENGTH,
                                  "project": PROJECT_NAME_MAX_LENGTH,
                                  "password": PASSWORD_MAX_LENGTH,
                                  "ssh_pub_key": SSH_PUB_KEY_MAX_LENGTH,
                                  "ssh_pub_key_id": SSH_PUB_KEY_ID_LENGTH,
                                  "alias": VOLUME_ALIAS_MAX_LENGTH,
                                  "rules_set_name": FIREWALL_NAME_MAX_LENGTH,
                                  "protocol": PROTOCOL_MAX_LENGTH,
                                  "source": SOURCE_MAX_LENGTH,
                                  "sport": SPORT_MAX_LENGTH,
                                  "destination": DESTINATION_MAX_LENGTH,
                                  "dport": DPORT_MAX_LENGTH}


class PidginHostOptions:
    @staticmethod
    def argument_spec():
        return dict(
            state=dict(
                type="str",
                choices=["present", "absent"],
                default="present",
            ),
            timeout=dict(
                type="int",
                default=300,  # 5 minutes
            ),
            token=dict(
                type="str",
                fallback=(
                    env_fallback,
                    [
                        "PIDGINHOST_ACCESS_TOKEN",
                        "PIDGINHOST_TOKEN",
                    ],
                ),
                no_log=True,
                required=True,
            ))


class PidginHostLengthChecker(PidginHostsConstants):
    def __init__(self, module):
        self.module = module

    def arguments_max_length(self, **kwargs):
        max_length_result = {
            key: len(value) for key, value in kwargs.items()
            if value and len(value) > self.REQUIRED_MAX_LENGTH_PARAMS.get(key, 0)
        }

        if max_length_result:
            max_length_error = dict()
            for key, value in max_length_result.items():
                max_length_error[key] = f'Max length for ({key}) is set to ' \
                                        f'{self.REQUIRED_MAX_LENGTH_PARAMS.get(key, 0)} ' \
                                        f'but your chosen {key} has a length of {value}'

            if max_length_error:
                self.module.fail_json(
                    changed=False,
                    msg=max_length_error,
                    server=[]
                )

    def volume_minim_max(self, **kwargs):
        product = kwargs.get("product")
        size_gigabytes = kwargs.get("size_gigabytes")

        min_size = kwargs['products_data'][product]['min_size']
        max_size = kwargs['products_data'][product]['max_size']
        if size_gigabytes < min_size or size_gigabytes > max_size:
            self.module.fail_json(
                changed=False,
                msg=f"Storage size {size_gigabytes} for {product} must be between {min_size} and {max_size}."
            )


class PidginHostCommonModule(PidginHostLengthChecker):
    def __init__(self, module):
        super().__init__(module)
        self.module = module
        self.state = module.params.get("state")
        self.token = module.params.get("token")
        self.ssh_pub_key = module.params.get("ssh_pub_key")
        self.payload = {}
        self.headers = {
            'Authorization': f"Token {self.token}",
            'Accept': 'application/json',
        }

    def get_ipv6_address_info(self):
        return self.get_request(self.IPV6_ENDPOINT, self.SUCCESS_CODE)

    def get_ipv4_address_info(self):
        return self.get_request(self.IPV4_ENDPOINT, self.SUCCESS_CODE)

    def attach_ip_by_id(self, server_id, ip_type, body):
        if ip_type == self.IPV4:
            attach = self.ATTACH_IPV4
        else:
            attach = self.ATTACH_IPV6
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{attach}"
        return self.post_request(url, body, self.SUCCESS_CODE)

    def detach_ip_by_id(self, ip_type, ip_id, body):

        if ip_type == self.IPV4:
            endpoint = self.IPV4_ENDPOINT
        else:
            endpoint = self.IPV6_ENDPOINT

        url = f"{endpoint}{ip_id}{self.DETACH}"
        return self.post_request(url, body, self.SUCCESS_CODE)

    def get_storage_products_info(self):
        return self.get_request(self.STORAGE_PRODUCT_ENDPOINT, self.SUCCESS_CODE)

    def increase_volume(self, volume_id, body):
        url = f"{self.VOLUMES_ENDPOINT}{volume_id}"

        return self.patch_request(url, body, self.SUCCESS_CODE)

    def delete_volume(self, volume_id):
        url = f"{self.VOLUMES_ENDPOINT}{volume_id}"
        return self.delete_request(url, self.DELETE_SUCCESS_CODE)

    def add_volume_to_server(self, server_id, body):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.VOLUMES}"
        return self.post_request(url, body, self.CREATE_SERVER_SUCCESS_CODE)

    def detach_volume_by_id(self, volume_id, body):
        url = f"{self.VOLUMES_ENDPOINT}{volume_id}{self.DETACH}"
        return self.post_request(url, body, self.SUCCESS_CODE)

    def attach_volume_by_id(self, volume_id, body):
        url = f"{self.VOLUMES_ENDPOINT}{volume_id}{self.ATTACHE}"
        self.post_request(url, body, self.SUCCESS_CODE)

    def get_server_power_management_by_id(self, server_id, api_code):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.POWER_MANAGEMENT}"
        return self.get_request(url, api_code)

    def get_server_volume_by_id(self, volume_id, server_id, api_code):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.VOLUMES}{volume_id}"
        return self.get_request(url, api_code)

    def get_volumes_info(self, api_code):
        return self.get_request(self.VOLUMES_ENDPOINT, api_code)

    def get_volumes_info_server(self, api_code, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.VOLUMES}"
        return self.get_request(url, api_code)

    def get_volume_by_id(self, volume_id):
        url = f"{self.VOLUMES_ENDPOINT}{volume_id}"
        return self.get_request(url, self.SUCCESS_CODE)

    def get_all_volumes_from_server_by_id(self, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.VOLUMES}"
        return self.get_request(url, self.SUCCESS_CODE)

    def delete_firewall_rules_set(self, rules_set_id):
        url = f"{self.SSH_KEYS_ENDPOINT}{rules_set_id}"
        return self.delete_request(url, self.DELETE_SUCCESS_CODE)

    def get_firewalls_info(self, api_code):
        return self.get_request(self.FIREWALL_RULES_SET_ENDPOINT, api_code)

    def create_firewall_rules_set(self, body):
        return self.post_request(self.FIREWALL_RULES_SET_ENDPOINT,
                                 body, self.ADD_SUCCESS_CODE)

    def remove_public_interface(self, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.PUBLIC_INTERFACE}"
        return self.delete_request(url, self.DELETE_SUCCESS_CODE)

    def add_public_interface(self, body, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.PUBLIC_INTERFACE}"
        return self.post_request(url, body, self.SUCCESS_CODE)

    def get_public_interface_for_server(self, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.PUBLIC_INTERFACE}"
        return self.get_request(url, self.SUCCESS_CODE)

    def add_firewall_rules(self, body, rules_set_id):
        url = f'{self.FIREWALL_RULES_SET_ENDPOINT}{rules_set_id}{self.RULES}'
        return self.post_request(url, body, self.ADD_SUCCESS_CODE)

    def get_account_info(self, api_code):
        return self.get_request(self.ACCOUNT_PROFILE_ENDPOINT,
                                api_code)

    def get_images_info(self, api_code):
        return self.get_request(self.CLOUD_IMAGE_ENDPOINT,
                                api_code)

    def modify_package(self, server_id, body):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.MODIFY_PACKAGES}"
        return self.post_request(url, body, self.SUCCESS_CODE)

    def get_packages_info(self, api_code):
        return self.get_request(self.CLOUD_PACKAGES_ENDPOINT,
                                api_code)

    def return_packages_choices(self):
        packages_choices = list()
        data = self.get_packages_info(self.SUCCESS_CODE)
        for item in data.get('results'):
            packages_choices.append(item['slug'])
        return packages_choices

    def get_cloud_servers_data(self, api_code):
        return self.get_request(self.CLOUD_SERVERS_ENDPOINT,
                                api_code)

    def get_cloud_server_data_by_id(self, server_id, api_code):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}"
        return self.get_request(url, api_code)

    def get_cloud_server_volumes_by_id(self, server_id, api_code):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.VOLUMES}"
        return self.get_request(url, api_code)

    def get_cloud_server_action_by_id(self, server_id, api_code):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}{self.POWER_MANAGEMENT}"
        return self.get_request(url, api_code)

    def get_cloud_server_by_id(self, server_id):
        url = f"{self.CLOUD_SERVERS_ENDPOINT}{server_id}"
        return self.get_request(url, self.SUCCESS_CODE)

    def get_cloud_server_ipv4(self, api_code):
        return self.get_request(self.CLOUD_IPV4_ENDPOINT,
                                api_code)

    def get_request_exist(self, endpoint):
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self.headers)
        if self.SUCCESS_CODE == response.status_code:
            return True
        else:
            return None

    def patch_request(self, endpoint, body, api_code):
        url = f"{self.BASE_URL}{endpoint}"
        self.headers.update({
            'Content-Type': 'application/json',
        })
        response = requests.patch(url, json=body, headers=self.headers)
        return self.handle_response(response, endpoint, api_code)

    def get_request(self, endpoint, api_code):
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self.headers)
        return self.handle_response(response, endpoint, api_code)

    def post_request(self, endpoint, body, api_code):
        url = f"{self.BASE_URL}{endpoint}"
        self.headers.update({
            'Content-Type': 'application/json',
        })
        for key, value in body.items():
            if value is not None and value != "":
                self.payload.update({
                    key: value,
                })
        try:
            response = requests.post(url, json=self.payload, headers=self.headers)

            return self.handle_response(response, endpoint, api_code)

        except requests.RequestException as e:
            self.module.fail_json(
                changed=False,
                msg=f"An error occurred during POST request to {url}",
                error=e,
            )

    def delete_request(self, endpoint, api_code):
        url = f"{self.BASE_URL}{endpoint}"
        self.headers.update({
            'Content-Type': 'application/json',
        })

        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == api_code:
                return True
            else:
                return self.handle_response(response, endpoint, api_code)

        except requests.RequestException as e:
            self.module.fail_json(
                changed=False,
                msg=f"An error occurred during DELETE request to {url}",
                error=e,
            )

    def handle_response(self, response, endpoint, api_code):
        url = f"{self.BASE_URL}{endpoint}"
        if api_code == self.ERROR_CODES:
            for code in self.ERROR_CODES:
                if code == response.status_code:
                    return False
            return True
        else:
            if api_code == response.status_code:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return response.text
            else:
                self.module.fail_json(
                    changed=False,
                    msg=f"PidginHost API error, request to {url} failed",
                    response=response.text,
                    status_code=response.status_code
                )

    def get_ssh_key_by_id(self, ssh_key_id):
        url = f"{self.SSH_KEYS_ENDPOINT}{ssh_key_id}"
        return self.get_request(url, self.SUCCESS_CODE)

    def get_ssh_keys(self):
        """Get available SSH keys from the cloud server."""
        return self.get_request(self.SSH_KEYS_ENDPOINT,
                                self.SUCCESS_CODE)

    @staticmethod
    def check_if_just_one(**kwargs):
        products = []
        data = kwargs.get("data")
        list_name = kwargs.get("list_name")
        name = kwargs.get("name")
        check_name = kwargs.get("check_name")

        if data and isinstance(data, dict):
            if list_name:
                items = data.get(list_name)
                products = [product for product in items if product.get(check_name) == name]
        if data and isinstance(data, list):
            products = [product for product in data if product[check_name] == name]

        return products

    def check_existing_ssh_pub_keys(self, key):
        """Check if the SSH public key already exists on the cloud server."""
        check_keys_data = self.get_ssh_keys()
        if isinstance(check_keys_data, dict) and check_keys_data:
            for ph_key in check_keys_data.get("results"):
                if key == ph_key["key"]:
                    return ph_key
        return None

    def add_ssh_key(self, body):
        """Add a new SSH public key to the cloud server."""
        return self.post_request(self.SSH_KEYS_ENDPOINT,
                                 body, self.ADD_SUCCESS_CODE)

    def delete_ssh_key(self, ssh_key_id):
        url = f"{self.SSH_KEYS_ENDPOINT}{ssh_key_id}"
        return self.delete_request(url, self.DELETE_SUCCESS_CODE)

    def validate_ip(self, ip_address):
        try:
            ipaddress.IPv4Address(ip_address)
            return self.get_ipv4_address_info(), self.IPV4
        except ipaddress.AddressValueError:
            pass

        try:
            ipaddress.IPv6Address(ip_address)
            return self.get_ipv6_address_info(), self.IPV6
        except ipaddress.AddressValueError:
            pass
        return None, None

    @staticmethod
    def return_valid_body_items(body):
        return {
            key: value if value else ""
            for key, value in body.items()
        }

    def check_if_products_exist(self, p):
        data = self.get_storage_products_info()

        products_data = {product["slug"]: {"min_size": product["min_size"], "max_size": product["max_size"]}
                         for product in data.get("results")}

        exists = any(product["slug"] == p for product in data.get("results"))

        if not exists:
            products = [product["slug"] for product in data.get("results")]
            self.module.fail_json(
                changed=False,
                msg=f"No Product named {p}, available products: {', '.join(products)}",
                volume=[]
            )
        return products_data


class PidginHostCommonInventory:
    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': f"Token {self.token}",
            'Accept': 'application/json',
        }
        self.url = f"{PidginHostsConstants.BASE_URL}{PidginHostsConstants.CLOUD_SERVERS_ENDPOINT}"

    def get_inventory(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            if response.status_code == PidginHostsConstants.SUCCESS_CODE:
                return response.json().get("results")
            else:
                logging.warning(f"{response}")
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Connection Error: {e}")
