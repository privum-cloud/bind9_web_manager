; Zone file for example.com
; DNS Web Manager - Example Zone
;
$TTL 86400      ; 24 hours default TTL

@   IN  SOA     ns1.example.com. admin.example.com. (
                2025112701  ; Serial (YYYYMMDDNN)
                3600        ; Refresh (1 hour)
                1800        ; Retry (30 minutes)
                604800      ; Expire (1 week)
                86400       ; Minimum TTL (24 hours)
)

; Nameservers
@               IN  NS      ns1.example.com.
@               IN  NS      ns2.example.com.

; Nameserver A records
ns1             IN  A       172.20.0.10
ns2             IN  A       172.20.0.11

; Main domain
@               IN  A       172.20.0.100

; Common subdomains (examples)
www             IN  A       172.20.0.100
mail            IN  A       172.20.0.101
ftp             IN  A       172.20.0.102

; CNAME records
webmail         IN  CNAME   mail.example.com.

; MX record for email
@               IN  MX  10  mail.example.com.

; TXT record for SPF
@               IN  TXT     "v=spf1 mx -all"
