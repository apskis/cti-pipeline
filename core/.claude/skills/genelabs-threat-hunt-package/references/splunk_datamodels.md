# GeneLabs Splunk Data Models — query reference for hunt SPL

Generate SPL as accelerated `tstats` against these data models, matching April's
house style (see CTI2602 examples):

```
| tstats summariesonly=true count from datamodel=<Model>.<Object>
    where <Prefix>.<field>="..." [NOT (<Prefix>.<field>="<known FP>")]
    by <Prefix>.dest <Prefix>.user <Prefix>._time
| rename <Prefix>.* as *
| sort - _time
```

Rules:
- `summariesonly=true` for accelerated models; use `summariesonly=false` only when
  backfilling non-accelerated data (note it in the query purpose).
- The FIELD PREFIX is the object's field-owner, which is NOT always the leaf node
  name. Use the "Prefix" column below. The node path after `datamodel=` is
  `Model.Object` (nested where shown).
- Always `| rename <Prefix>.* as *` then `sort - _time`.
- Add `NOT (...)` exclusions for known false positives and say so in the purpose.
- For counts/scope use `dc(<Prefix>.dest) as unique_hosts` and `stats`.
- IOC fields are flagged so hunts can pivot on and harvest indicators.

---

## Endpoint  (CrowdStrike + Splunk endpoint; accelerated)
Index macro: `cim_Endpoint_indexes`  ·  Prefix: **leaf object name**
- `Endpoint.Processes` (tag=process report) — Processes.process (full command line),
  process_name, process_exec, process_path, process_hash [IOC], parent_process,
  parent_process_name, parent_process_exec, user, user_id, dest,
  process_integrity_level, event_simpleName (CrowdStrike ProcessRollup2)
- `Endpoint.Filesystem` (tag=endpoint filesystem) — action (created/deleted/modified/read),
  file_path [IOC], file_name [IOC], file_create_time, dest, user, process_guid
- `Endpoint.Services` (tag=service report) — service_name, service, service_path [IOC],
  service_dll [IOC], start_mode, status, dest, user
- `Endpoint.Ports` (tag=listening port) — dest_port, transport, state, dest, src
IOC fields: process_hash, file_path, file_name, service_dll, process (embedded strings)
Primary use: process execution, LOLBins, persistence, credential-in-cmdline, malware on disk.

## Malware  (CrowdStrike detections; accelerated)
Constraint: `index=cs_win tag=malware`  ·  Prefix: **Malware_Attacks**
- `Malware.Malware_Attacks` (root) · `Malware.Blocked_Malware` (action="blocked") ·
  `Malware.Allowed_Malware` (action="allowed")
Fields: signature, category, action, dest, src, user, file_name [IOC], file_path,
file_hash [IOC], sha256 [IOC], md5 [IOC], url [IOC], sender [IOC], severity,
detect_name (event.DetectName), detect_id, IOCValue [IOC] (event.IOCValue),
IOCType (event.IOCType), DomainName [IOC], device_name (event.ComputerName),
HostLink (Falcon console), event.CommandLine
Primary use: confirmed/blocked malware, actor tooling by hash/name, IOC matches.

## Authentication  (accelerated)
Index macro: `cim_Authentication_indexes` tag=authentication  ·  Prefix: **Authentication**
- `Authentication.Authentication` (root) · `Authentication.Failed_Authentication`
  (action="failure") · `Authentication.Successful_Authentication` (action="success")
Fields: action, app, user, src [IOC], dest, src_user, authentication_method (MFA/SAML/FIDO),
authentication_service (Okta/ActiveDirectory), signature, signature_id, reason,
user_agent, src_nt_domain, dest_nt_domain
Primary use: brute force, MFA method changes, impossible travel, spray, service abuse.

## Network_Sessions  (accelerated)
Index macro: `cim_Network_Sessions_indexes` tag=network session  ·  Prefix: **All_Sessions**
- `Network_Sessions.All_Sessions` · `.Session_Start` (tag=start) · `.Session_End` (tag=end)
- `.DHCP` (tag=dhcp) · `.VPN` (tag=vpn)  ← GlobalProtect VPN sessions
Fields: src_ip [IOC], dest_ip [IOC], src_mac, dest_mac, src_dns, dest_dns, src_nt_host,
dest_nt_host, user, action, signature, duration; DHCP adds lease_duration, lease_scope
Primary use: VPN logon anomalies, new-ASN sessions, DHCP lease tracking.

## Network_Traffic  (accelerated)
Index macro: `cim_Network_Traffic_indexes` tag=network communicate  ·  Prefix: **All_Traffic**
- `Network_Traffic.All_Traffic` · `.Traffic_By_Action`
Fields: src_ip [IOC], dest_ip [IOC], src_port, dest_port [IOC], action (allowed/blocked/teardown),
direction (inbound/outbound), transport (tcp/udp/icmp), app, protocol, bytes, bytes_in,
bytes_out, dvc, rule, tcp_flag, src_zone, dest_zone, user, dest_translated_ip
Primary use: C2 beaconing, exfil (bytes_out), blocked/allowed egress to bad dest_ip.

## Network_Resolution (DNS)  (accelerated)
Index macro: `cim_Network_Resolution_indexes` tag=network resolution dns  ·  Prefix: **DNS**
- `Network_Resolution.DNS`
Fields: query [IOC] (domain), answer [IOC] (resolved IP), record_type, query_type,
message_type, reply_code (NXDOMAIN etc.), src [IOC], dest, transport, name, category,
blocked_category, user
Primary use: malicious/DGA/newly-registered domain lookups, DNS tunneling, C2 domains.

## Web  (proxy; accelerated)
Index macro: `cim_Web_indexes` (tag=proxy OR web OR resolution)  ·  Prefix: **Web**
- `Web.Web` (root) · `Web.Proxy` (tag=proxy)
Fields: url [IOC], uri_path, uri_query, http_method, http_user_agent [IOC], http_referrer,
status (HTTP code), category, dest [IOC], src, dest_port, site, user, bytes, http_content_type,
url_length, cookie, app, file_name [IOC]
Primary use: malicious URLs, suspicious user-agents, AitM/phishing landing pages, downloads.

## <firewall-app>  (Palo Alto NGFW / Panorama; accelerated, NON-CIM)
Constraint: `p_index` eventtype="<firewall-app>" (NOT CIM tags)  ·  Prefix: **log**
Node paths (nested): `<firewall-app>.log` · `.log.traffic` (eventtype=pan_traffic) ·
`.log.traffic.start` · `.log.traffic.end` · `.log.threat` (pan_threat) ·
`.log.threat.vulnerability` (log_subtype=vulnerability) · `.log.threat.virus` ·
`.log.threat.spyware` · `.log.url` (URL Filtering)
Fields: action, app, category, src_ip [IOC], dest_ip [IOC], src_port, dest_port, src_user,
dest_user, rule, threat_id, threat_name [IOC], threat_category, url [IOC], file_name [IOC],
file_hash [IOC], file_type, severity, src_zone, dest_zone, session_id, bytes_in, bytes_out,
http_user_agent [IOC], http_method, verdict, direction, dvc_name, session_end_reason
Primary use: firewall allow/deny to bad dest_ip, IPS/AV/spyware hits, URL filtering,
GlobalProtect-adjacent perimeter activity.
Example: `| tstats summariesonly=true count from datamodel=<firewall-app>.log.threat
where log.threat_name="*" by log.src_ip log.dest_ip log.threat_name log.action _time
| rename log.* as * | sort - _time`

## Windows (Windows_Security)  (accelerated)
Constraint: `cim_Windows_indexes` `wineventcode_filters` tag=windows security tag!=authentication
Prefix: **Windows_Security**
- `Windows.Windows_Security`
Fields: EventCode, Logon_ID, Security_ID, action, user, src, dest, src_ip [IOC], dest_ip [IOC],
Object_Name, Service_Name, Service_File_Name [IOC], Service_Start_Type, user_group, src_user,
Share_Name, Share_Path, Caller_Computer_Name, signature, signature_id, status, New_DN, Old_DN,
Change_Type
Primary use: service creation (7045), object/share access, group changes, GPO/account changes
(non-auth Security channel events).

## Email  (Proofpoint + mail; accelerated)
Index macro: `cim_Email_indexes`  ·  Prefix: **All_Email**
- `Email.All_Email` (root) · `Email.Delivery` (sourcetype=pps_maillog → Proofpoint) ·
  `Email.Content`
Fields: src_user [IOC] (sender), sender [IOC], recipient, recipient_domain, subject [IOC],
url [IOC], file_name [IOC], file_hash [IOC], message_id, action (delivered/blocked/quarantined),
threatStatus, src, dest, protocol
Primary use: phishing sender/subject/url/attachment hunting, malspam delivery, lure themes.

---
### Falcon (CrowdStrike) starters — for endpoint/identity pivots outside Splunk
Use Event Search / RTR when a hunt needs raw Falcon telemetry:
`event_simpleName=ProcessRollup2 CommandLine=*<pattern>*`,
`event_simpleName=DnsRequest DomainName=*<domain>*`,
`event_simpleName=UserLogon RemoteAddressIP4=*`. Label these as Falcon starters.
