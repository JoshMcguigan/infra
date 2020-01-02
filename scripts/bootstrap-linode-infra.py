#!/bin/python3

from typing import Iterable

"""
Load linode API key from dotenv file
"""
import os
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
LINODE_API_KEY = os.environ.get("LINODE_API_KEY")

"""
Instantiate linode API client with key
"""
from linode_api4 import LinodeClient
client = LinodeClient(LINODE_API_KEY)

"""
Print available linode types, regions, and images
"""
# ltypes = client.linode.types()
# regions = client.regions()
# images = client.images()
# for ltype in ltypes:
#     print(ltype)
# for region in regions:
#     print(region)
# for image in images:
#     print(image)

class DesiredLinode:
    def __init__(self, name: str, region: str):
        self.name = name
        self.region = region

class CreatedLinode:
    def __init__(self, desired_linode: DesiredLinode, public_ip: str, private_ip: str):
        self.name = desired_linode.name
        self.region = desired_linode.region
        self.public_ip = public_ip
        self.private_ip = private_ip

def create_linodes(desired_linodes: Iterable[DesiredLinode]) -> Iterable[CreatedLinode]:
    """
    Create new linodes. This fails if linodes with these names already exist.
    """
    created_linodes = []
    for desired_linode in desired_linodes:
        new_linode, _password = client.linode.instance_create(
            "g6-nanode-1",
            desired_linode.region,
            private_ip=True,
            label=desired_linode.name,
            image="linode/centos8",
            authorized_keys="~/.ssh/id_ed25519.pub")

        public_ip = new_linode.ips.ipv4.public[0]
        private_ip = new_linode.ips.ipv4.private[0] 
        created_linodes.append(CreatedLinode(desired_linode, public_ip, private_ip))

    return created_linodes

def bootstrap_infra():
    """
    Creates all infrastructure from scratch. Expects user to manually update/run ansible after.
    """
    desired_linodes = [
            DesiredLinode("lb1", "us-west"),
            DesiredLinode("ns1", "us-west"),
            DesiredLinode("lb2", "eu-west"),
            DesiredLinode("ns2", "eu-west"),
        ]
    create_linodes(desired_linodes)

def deploy_updated_nameservers():
    # TODO documentation
    #  - nginx config/version can be updated live
    #  - kernel updates can be done blue-green and update glue records to point to new machine
    #    - this is a much slower blue-green deploy than we have for the nameservers because
    #      we have to wait out the DNS ttl
    """
    Deploys updated nameservers in a blue-green style. The existing name servers are left
    running until the new nameservers pass a health check. After a passing health check,
    the load balancers are updated to point to the new name servers. Finally, the old
    nameservers are removed.
    """

    def update_ansible_nameserver_public_ip(created_linodes: Iterable[CreatedLinode]):
        pass

    def ansible_configure_nameservers(created_linodes: Iterable[CreatedLinode]):
        pass

    def health_check_nameservers(created_linodes: Iterable[CreatedLinode]) -> bool:
        pass

    def update_ansible_load_balancer_config(created_linodes: Iterable[CreatedLinode]):
        pass

    def ansible_configure_load_balancers():
        """
        Deploy updated configuration to load balancers to send traffic to new
        nameserver instances.
        """
        pass

    desired_linodes = [
            DesiredLinode("ns1-next", "us-west"),
            DesiredLinode("ns2-next", "eu-west"),
        ]
    created_linodes = create_linodes(desired_linodes)

    update_ansible_nameserver_public_ip(created_linodes)
    ansible_configure_nameservers(created_linodes)

    if not health_check_nameservers(created_linodes):
        print("Health check failed on newly created linodes.")
        print("Traffic is still pointing to existing nameservers.")
        print("Recommended action: delete new nameserver instances.")
        return

    update_ansible_load_balancer_config(created_linodes)
    ansible_configure_load_balancers()

    # TODO do a system health check and roll back if needed
    # TODO delete old nameserver linodes
    # TODO rename new nameserver linodes

def main():
    """
    Expects to be run from the root of the repository.
    """

    # The bootstrap infra script only needs to be run once. All other scripts assume
    # these machines already exist.
    # bootstrap_infra()

    deploy_updated_nameservers()

if __name__ == "main":
    main()
