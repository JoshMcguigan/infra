$TTL	1h
@  IN  SOA ns1.rhiyo.com. hostmaster.rhiyo.com. (
			      0 ; serial
			      3H ; refresh
			      15 ; retry
			      1w ; expire
			      3h ; min ttl
			     )
       IN  NS     ns1.rhiyo.com.
       IN  NS     ns2.rhiyo.com.

ns1    IN  A      74.207.254.44
ns2    IN  A      173.230.148.139
