#!/bin/python3

"""
Load linode API key from dotenv file
"""
import os
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '../.env')
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

linodes_to_create = [
        # ("ns3", "us-west"),
        ("ns3-next", "us-west"),
    ]

"""
Create new nameservers

This fails if the nameservers are already created.
"""
linodes_created = []
for linode_label, linode_region in linodes_to_create:
    new_linode, _password = client.linode.instance_create(
        "g6-nanode-1",
        linode_region,
        label=linode_label,
        image="linode/centos8",
        authorized_keys="~/.ssh/id_ed25519.pub")

    new_ip = new_linode.ips.ipv4.public[0]
    print(f"Created {linode_label} with at {new_ip}")
    linodes_created.append((linode_label, new_ip))

print("Update the ansible inventory file with new IPs, wait for the machines to finish starting, then run `ansible-playbook playbook.yml -i inventory`.")
input("Press Enter to continue...")

for linode_label, new_ip in linodes_created:
    # TODO do a health check of the new linode
    print("Perform a health check on the new linode.")
    input("Press Enter to continue...")
    print("If there is an existing linode, we want to swap the old IP.")
    print(f"Run `ssh root@{new_ip}` then on the new linode run `systemd-run --scope --user ipswap $EXISTING_IP $EXISTING_GATEWAY`.")
    input("Press Enter to continue...")
    print("Trigger IP swap between new and old linode, then perform health check on the public IP.")
    input("Press Enter to continue...")
    print("Delete the old linode.")
    input("Press Enter to continue...")
    print("Rename the new linode to remove `-next`.")
    input("Press Enter to continue...")
