# Infra

Check out [this blog post](https://www.joshmcguigan.com/blog/run-your-own-dns-servers/) for the backstory on why I've chosen to run my own authoritative DNS servers.

### scripts

Contains scripts for creating cloud servers, as well as local testing.

### ansible

Contains Ansible provisioning scripts.

### infra-tools

Additional infra support tooling can be found in the [infra-tools](https://github.com/JoshMcguigan/infra-tools) repository.

## Operations

### DNS server updates

Since the DNS servers (ns1/ns2) sit behind the load balancers, they can be updated in a blue-green fashion (the old servers continue serving requests until the new servers are completely ready, then the load balancer configuration is changed to point to the new servers). This allows performing all types of updates without downtime.

Running `./scripts/deploy-infra.py` will deploy a new pair of DNS server (ns1-next and ns2-next), configure them with the latest ansible configuration from this repository, update the load balancers to point to them, then remove the old DNS servers. This is the process for performing updates of any type on the DNS servers.

### Load balancer updates

The load balancers (lb1/lb2) are nginx reverse proxies. They exist in the infrastructure not so much to balance load but to allow for the blue-green deployments of the servers behind them, as described above. For this reason, the DNS glue records actual point to the load balancer public IP addresses rather than pointing to the DNS servers directly.

While this makes changes to the DNS servers very easy, updates to the load balancers need to be performed a bit more carefully.

Updating the nginx configuration, as well as the nginx software itself, can be done with zero downtime. These operations can be done in-place, on the live production server while it is serving traffic.

Linux kernel updates, or any other update which requires restarting the machine, should be done by first spinning up a new set of load balancers (lb1-next/lb2-next), the updating the DNS glue records to point to the new load balancers, and then finally taking the old load balancers offline when they are no longer receiving traffic (be careful of potentially long DNS TTL here).
