# CrowdStrike Falcon CQL (LogScale / Next-Gen SIEM) — query reference

Falcon LogScale uses **CrowdStrike Query Language (CQL)**, native to LogScale — it
is NOT Splunk SPL. In the GeneLabs hunt package, CQL is the PRIMARY hunt query set
(CrowdStrike is the EDR / endpoint source of truth); Splunk `tstats` queries are
supporting/corroborating. Write real CQL, not legacy Event Search `| stats`.

## Syntax essentials
- Filters are space-separated = implicit AND: `#event_simpleName=ProcessRollup2 UserName=/svc_/i`
- Tagged fields take `#` (the sensor event stream): `#event_simpleName=DnsRequest`.
- Exact match: `Field="value"`. Regex: `Field=/pattern/` with flags (`/pat/i` = case-insensitive).
  Glob: `Field="*substr*"`. Prefer regex for robustness.
- Negation: `Field!=value`  or  `!Field=/pat/`.
- OR group: `(#event_simpleName=ProcessRollup2 OR #event_simpleName=SyntheticProcessRollup2)`.
- Membership: `in(Field, values=["a","b","c"])`.
- Aggregate with `groupBy`, not stats:
  `| groupBy([ComputerName, UserName], function=count(as=cnt))`
  distinct: `| groupBy([UserName], function=count(RemoteAddressIP4, distinct=true, as=distinct_ips))`
- Post-aggregation filter: `| cnt > 5`  (or `| test(cnt>5)`).
- Order / limit: `| sort(cnt, order=desc, limit=100)`  ·  `| head(50)`.
- Present columns: `| table([@timestamp, ComputerName, UserName, CommandLine, SHA256HashData])`.
- Time range is set by the search window (UI/API) — note the intended lookback in the
  query purpose (e.g., "last 14 days") rather than hardcoding it.

## Core events and fields (raw sensor stream)
- **ProcessRollup2 / SyntheticProcessRollup2** — process exec:
  CommandLine, ImageFileName, ParentBaseFileName, RawProcessId, ParentProcessId,
  UserName, UserSid, SHA256HashData [IOC], MD5HashData [IOC], ComputerName, aid
- **DnsRequest** — DomainName [IOC], ComputerName, ContextProcessId, aid
- **NetworkConnectIP4 / NetworkReceiveAcceptIP4** — RemoteAddressIP4 [IOC], RemotePort,
  LocalAddressIP4, LocalPort, Protocol, ComputerName, aid
- **UserLogon / UserLogonFailed2** — UserName, LogonType, RemoteAddressIP4 [IOC],
  ComputerName, UserIsAdmin
- **DetectionSummaryEvent / EppDetectionSummaryEvent** — DetectName, DetectDescription,
  Tactic, Technique, Severity, FileName, SHA256HashData [IOC], CommandLine,
  ComputerName, FalconHostLink
- **FileWritten / PeFileWritten / NewExecutableWritten** — TargetFileName [IOC],
  FileName, SHA256HashData [IOC], ComputerName
- **AsepValueUpdate / RegSystemConfigValueUpdate** — RegObjectName, RegValueName (persistence)
- **ServiceStarted / ScheduledTaskRegistered** — ServiceDisplayName / TaskName (persistence)

## Pattern examples
Credential / secret in command line (like CTI2602):
```
(#event_simpleName=ProcessRollup2 OR #event_simpleName=SyntheticProcessRollup2)
| CommandLine=/ghp_[A-Za-z0-9]{20,}/
| groupBy([ComputerName, UserName, CommandLine], function=count(as=cnt))
| sort(cnt, order=desc)
```
Lookalike / AitM domain resolution:
```
#event_simpleName=DnsRequest
| DomainName=/okta-sso-verify|sso-.*-login|passkey-verify/i
| groupBy([ComputerName, DomainName], function=count(as=cnt))
| sort(cnt, order=desc)
```
Beacon / egress to a bad IP:
```
#event_simpleName=NetworkConnectIP4
| in(RemoteAddressIP4, values=["203.0.113.44","198.51.100.7"])
| groupBy([ComputerName, RemoteAddressIP4, RemotePort], function=count(as=cnt))
```
MFA-reset takeover proxy — many source IPs per user:
```
(#event_simpleName=UserLogon OR #event_simpleName=UserLogonFailed2)
| groupBy([UserName], function=count(RemoteAddressIP4, distinct=true, as=distinct_ips))
| distinct_ips > 3
| sort(distinct_ips, order=desc)
```
Known-bad hash execution:
```
(#event_simpleName=ProcessRollup2 OR #event_simpleName=PeFileWritten)
| in(SHA256HashData, values=["<sha256-ioc-1>","<sha256-ioc-2>"])
| table([@timestamp, ComputerName, UserName, ImageFileName, SHA256HashData])
```
Actor tooling by detection name/technique:
```
#event_simpleName=DetectionSummaryEvent
| Technique=/T1556|T1078/ OR DetectName=/Scattered|Vishing|AitM/i
| table([@timestamp, ComputerName, UserName, DetectName, Tactic, Technique, FalconHostLink])
```
Note: CrowdStrike raw event fields map to April's Splunk **Malware** data model
(event.DetectName, event.IOCValue/IOCType, event.CommandLine, ComputerName, HostLink),
so a CQL hunt and the Splunk Malware/Endpoint queries corroborate each other.
