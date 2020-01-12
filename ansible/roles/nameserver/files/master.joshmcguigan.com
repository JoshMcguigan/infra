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

@      IN  A      104.198.14.52
www    IN  CNAME  agitated-haibt-e30b89.netlify.com.
