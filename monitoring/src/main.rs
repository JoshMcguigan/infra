use std::net::{Ipv4Addr, IpAddr};
use std::net::SocketAddr;
use std::str::FromStr;
use std::process::exit;
use trust_dns_client::client::{Client, SyncClient};
use trust_dns_client::udp::UdpClientConnection;
use trust_dns_client::op::DnsResponse;
use trust_dns_client::rr::{DNSClass, Name, RData, Record, RecordType};

struct NameServer {
    address: Ipv4Addr,
    name: Name,
}

fn main() {
    // Ideally we'd parse the ansible config for this information.
    let ns1 = NameServer {
        address: "173.255.245.83".parse().unwrap(),
        name: Name::from_str("ns1.rhiyo.com.").unwrap(),
    };
    let ns2 = NameServer {
        address: "212.71.246.209".parse().unwrap(),
        name: Name::from_str("ns2.rhiyo.com.").unwrap(),
    };
    let name_servers = vec![&ns1, &ns2];

    let mut failed = false;

    for name_server in &name_servers {
        // Right now the DNS servers are only configured with records for themselves. Again
        // this information would ideally be parsed from the zonefile / ansible config
        // so when additional zones or hosts are added new checks would automatically start.
        for record_to_request in &name_servers {
            print!("Checking resolution of {} from server {} ",
                    record_to_request.name,
                    name_server.name,
                );

            match check(name_server, record_to_request) {
                Ok(_) => println!("OK"),
                Err(_) => {
                    failed = true;
                    println!("FAILED");
                },
            };
        }
    }

    if failed {
        exit(1);
    }
}

fn check(name_server: &NameServer, record_to_request: &NameServer) -> Result<(), ()> {
    let socket_addr = SocketAddr::new(IpAddr::V4(name_server.address), 53);
    let conn = UdpClientConnection::new(socket_addr).unwrap();
    let client = SyncClient::new(conn);

    let response: DnsResponse = client.query(
            &record_to_request.name,
            DNSClass::IN,
            RecordType::A,
        ).map_err(|_| ())?;
    let answers: &[Record] = response.answers();

    if let RData::A(ref ip) = answers[0].rdata() {
        if *ip == record_to_request.address {
            Ok(())
        } else {
            Err(())
        }
    } else {
        Err(())
    }

}
