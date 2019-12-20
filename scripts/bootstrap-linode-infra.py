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

"""
Create new nameservers

This fails if the nameservers are already created.
"""
for linode_label in ["ns1", "ns2"]:
    new_linode, _password = client.linode.instance_create(
        "g6-nanode-1",
        "us-west",
        label=linode_label,
        image="linode/centos8",
        authorized_keys="~/.ssh/id_ed25519.pub")

    print(f"Created {linode_label} with at {new_linode.ips.ipv4.public[0]}")
