#!/bin/python3

from typing import Iterable
import subprocess
import fileinput
import os
from os.path import join, dirname

"""
Set current working directory to repository root.
"""
os.chdir(join(dirname(__file__), '..'))

"""
Load linode API key from dotenv file
"""
from dotenv import load_dotenv
load_dotenv('.env')
LINODE_API_KEY = os.environ.get("LINODE_API_KEY")

"""
Instantiate linode API client with key
"""
from linode_api4 import LinodeClient  # type: ignore
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

def create_linode(desired_linode: DesiredLinode) -> CreatedLinode:
    """
    Create new linodes. This fails if linodes with these names already exist.
    """
    print(f"Creating {desired_linode.name}..")
    new_linode, _password = client.linode.instance_create(
        "g6-nanode-1",
        desired_linode.region,
        private_ip=True,
        label=desired_linode.name,
        image="linode/centos8",
        authorized_keys="~/.ssh/id_ed25519.pub")

    public_ip = new_linode.ips.ipv4.public[0].address
    private_ip = new_linode.ips.ipv4.private[0].address

    return CreatedLinode(desired_linode, public_ip, private_ip)

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
    for linode in desired_linodes:
        create_linode(desired_linode)

def deploy_updated_nameservers():
    """
    Deploys updated nameservers in a blue-green style. The existing name servers are left
    running until the new nameservers pass a health check. After a passing health check,
    the load balancers are updated to point to the new name servers. Finally, the old
    nameservers are removed.
    """

    def update_ansible_nameserver_public_ip(ns1_ip: str, ns2_ip: str):
        """
        Update the ansible configuration with the public IP addresses of the newly
        created linodes, so we can ansible configure them.
        """
        print("updating ansible inventory file with new public IP for ns1 and ns2..")
        for line in fileinput.input("ansible/inventory", inplace=True):
            if line.startswith("ns1"):
                print(f"ns1 ansible_host={ns1_ip}")
            elif line.startswith("ns2"):
                print(f"ns2 ansible_host={ns2_ip}")
            else:
                # file input adds a newline, so we need to strip the
                # existing new line
                print(line.rstrip())
             
    def wait_for_ssh(ip: str):
        """
        Blocks until SSH is up for this IP
        """
        for i in range(5):
            try:
                # Test if this machine is available via SSH by connecting
                # and then immediately `exit`ing. Turn off strict host
                # key checking because linode could be re-using an IP
                # my machine has previously connected to. Set batch
                # mode to ensure a password prompt doesn't come up if
                # key based auth fails (these machines should be accesible
                # by key).
                print(f"Attempting to connect to {ip}..")
                command = f"ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes root@{ip} exit"
                subprocess.run(command, shell=True, check=True)
                print("Connected")
                return
            except CalledProcessError:
                # SSH down, try again
                # Due to the long SSH connection timeout value, adding
                # a time delay here is not necessary.
                pass

        raise Exception(f"Failed to SSH to {ip}")

    def ansible_configure_nameservers():
        print("running ansible playbook on newly created nameservers..")
        command = "ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbook.yml -i ansible/inventory -l nameserver"
        subprocess.run(command, shell=True, check=True)

    def dns_health_check(nameserver_ip: str) -> bool:
        try:
            # TODO this doesn't check the actual returned DNS records
            # This should eventually become a feature of the
            # infra-tools/monitoring application, to ensure
            # the production checks are the same as the deploy
            # checks.
            command = f"dig ns1.rhiyo.com @{nameserver_ip}"
            subprocess.run(command, shell=True, check=True)
        except CalledProcessError:
            return False
        return True

    def health_check_nameservers(ns1_public_ip: str, ns2_public_ip: str) -> bool:
        """
        Health checks new nameservers by connecting to them directly (not through
        load balancers).
        """
        print("running DNS health check on new nameservers public IP")
        return dns_health_check(ns1_public_ip) and dns_health_check(ns2_public_ip)

    def update_ansible_load_balancer_config(ns1_private_ip: str, ns2_private_ip: str):
        print("updating the host vars for lb1/lb2 with the private IP for ns1-next/ns2-next..")
        for line in fileinput.input("ansible/host_vars/lb1.yml", inplace=True):
            if line.startswith("UPSTREAM_DNS_SERVER"):
                print(f"UPSTREAM_DNS_SERVER: \"{ns1_private_ip}\"")
            else:
                print(line.rstrip())
        for line in fileinput.input("ansible/host_vars/lb2.yml", inplace=True):
            if line.startswith("UPSTREAM_DNS_SERVER"):
                print(f"UPSTREAM_DNS_SERVER: \"{ns2_private_ip}\"")
            else:
                print(line.rstrip())

    def ansible_configure_load_balancers():
        """
        Deploy updated configuration to load balancers to send traffic to new
        nameserver instances.
        """
        print("running ansible playbook to update load balancers..")
        command = "ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbook.yml -i ansible/inventory -l proxy"
        subprocess.run(command, shell=True, check=True)

    def health_check() -> bool:
        """
        Performs system level health check by performing DNS lookup through
        load balancers.
        """
        print("running health check through load balancer")
        # TODO this information should come from the ansible inventory file
        LB1_PUBLIC_IP = "173.255.245.83"
        LB2_PUBLIC_IP = "212.71.246.209"
        return dns_health_check(LB1_PUBLIC_IP) and dns_health_check(LB2_PUBLIC_IP)

    ns1 = create_linode(DesiredLinode("ns1-next", "us-west"))
    ns2 = create_linode(DesiredLinode("ns2-next", "eu-west"))

    wait_for_ssh(ns1.public_ip)
    wait_for_ssh(ns2.public_ip)

    update_ansible_nameserver_public_ip(ns1.public_ip, ns2.public_ip)
    ansible_configure_nameservers()

    if not health_check_nameservers(ns1.public_ip, ns2.public_ip):
        print("Health check failed on newly created linodes.")
        print("Traffic is still pointing to existing nameservers.")
        print("Recommended action: delete new nameserver instances.")
        return

    update_ansible_load_balancer_config(ns1.private_ip, ns2.private_ip)
    ansible_configure_load_balancers()

    if not health_check():
        print("Health check failed.")
        print("Traffic is pointing to new linodes.")
        print("Recommended action: delete new nameserver instances, and revert load balancer configuration.")
        return

    print("load balancers are now pointing to ns1-next and ns2-next")
    print("deleting ns1/ns2")
    for linode in client.linode.instances():
        if linode.label in ["ns1", "ns2"]:
            linode.delete()

    print("renaming ns1-next and ns2-next to ns1/ns2")
    for linode in client.linode.instances():
        if linode.label.endswith("-next"):
            linode.label = linode.label.rstrip("-next")
            linode.save()

    print("Deploy complete!")
    print("Suggested action:")
    print(" - git commit the updated configuration")

def main():
    # The bootstrap infra script only needs to be run once. All other scripts assume
    # these machines already exist.
    # bootstrap_infra()

    deploy_updated_nameservers()

if __name__ == "__main__":
    main()
