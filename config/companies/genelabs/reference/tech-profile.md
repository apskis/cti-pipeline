# Tech profile — DRAFT

**Status: DRAFT. This is no longer the shipped STUB, and April has not yet confirmed it.**
It was assembled on 2026-10-10 from what this repo already states elsewhere (sources named
per section), so it adds no new facts about GeneLabs. Say "tech profile is a DRAFT" once
in every run output. A relevance raised from this file is still a JUDGEMENT, phrased
"possible exposure — verify", until a connector measures it.

Keep it sanitized: GeneLabs names only, never a real employer, hostname or address.

## Own products and platforms
Source: `CustomerProfile` in `core/tools/reporting/src/core/config.py`, and the OWN-PRODUCT
WATCH in `components/bulletin-scan/task.md`. A vulnerability in any of these is a customer
facing and regulatory matter: surface it at the top.

- Sequencing instruments: HelixSeq X, HelixSeq Lite, HelixSeq Micro
- Cloud platforms holding customer genomic and clinical data: GeneLabs Connected Analytics
  (GCA), SeqSpace Sequence Hub
- Secondary analysis pipelines: RAPIDCALL
- Instrument software tracked for ICS advisories: Universal Copy Service, Local Run Manager

## Enterprise IT and SaaS in use
Source: the tech stack lens of `_DEFAULT_PEER_WATCH_ORGS` in the same config file, plus the
platforms the scan task and connector rules already refer to.

- Identity: Okta, Microsoft Active Directory
- Microsoft: Microsoft 365, Exchange, SharePoint, OneDrive, Viva Engage, Windows, IIS
- Cloud: Amazon Web Services (including CloudFront), Google
- Data and business SaaS: Snowflake, Salesforce, Workday, ServiceNow
- Network security: Zscaler, Palo Alto Networks
- Source control: GitHub
- Servers: Windows, Linux

## Security tooling
Source: `components/bulletin-scan/connectors.md`. A flaw in one of these is also a flaw in
the thing that would detect its exploitation.

- CrowdStrike Falcon, Splunk, Rapid7 InsightVM, Claroty xDome, ThreatQ, Intel 471, Shodan

## Infrastructure and compute partners
Source: the same watchlist, "publicly reported" lens.

- NVIDIA, Pure Storage, Equinix

## Not established: do not infer either way
The repo says nothing about these, so a story naming one is neither evidence of exposure
nor reassurance. Write "not in the tech profile; could not be assessed".

- VPN and remote access gateways, load balancers, mail security gateways
- Virtualisation, backup, storage area network, container platforms
- Laboratory information management and manufacturing execution systems
- Endpoint management, remote support tools, developer tooling beyond GitHub
