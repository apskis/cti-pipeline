# Peer watchlist — DRAFT

**Status: DRAFT. This is no longer the shipped STUB, and April has not yet confirmed it.**
The organisations below are copied from the two watchlists the reporting component already
ships (`_DEFAULT_PEER_WATCH_ORGS` and `_DEFAULT_PEER_COMPETITOR_ORGS` in
`core/tools/reporting/src/core/config.py`), so the scan and the weekly report now watch the
same names. Change both places together. Say "peer watchlist is a DRAFT" once in every run
output.

A breach of any organisation here, or an SEC 8-K Item 1.05 filing by one, gets a STEP 5B
row. Match on the distinctive part of the name. No customers are listed: none are named
anywhere in this repo, and that lens stays empty until April supplies it.

Keep it sanitized: never add the real employer or anything that identifies it.

## Competitors (genomics, sequencing, diagnostics)
| Organisation | Relationship | Sector |
|---|---|---|
| Thermo Fisher | Competitor | Life science tools |
| Pacific Biosciences (PacBio) | Competitor | Sequencing |
| Oxford Nanopore | Competitor | Sequencing |
| BGI Genomics | Competitor | Sequencing |
| MGI Tech | Competitor | Sequencing |
| Complete Genomics | Competitor | Sequencing |
| Qiagen | Competitor | Life science tools |
| Agilent | Competitor | Life science tools |
| 10x Genomics | Competitor | Genomics |
| Bio-Rad | Competitor | Life science tools |
| Element Biosciences | Competitor | Sequencing |
| Ultima Genomics | Competitor | Sequencing |
| Singular Genomics | Competitor | Sequencing |
| Twist Bioscience | Competitor | Genomics |
| Guardant Health | Competitor | Diagnostics |
| Natera | Competitor | Diagnostics |
| Tempus | Competitor | Diagnostics |
| Roche | Competitor | Diagnostics and pharma |

## Partners and suppliers
| Organisation | Relationship | Sector |
|---|---|---|
| Broad Institute | Research partner | Genomics research |
| SOPHiA Genetics | Informatics partner | Genomics software |
| Microba | Informatics partner | Genomics |
| Benchling | Supplier | Lab software |
| Bristol Myers Squibb | Partner | Pharma |
| Merck | Partner | Pharma |
| Myriad Genetics | Partner | Diagnostics |
| Kura Oncology | Partner | Pharma |
| NVIDIA | Infrastructure partner | Compute |
| Pure Storage | Infrastructure partner | Storage |
| Equinix | Infrastructure partner | Data centres |

## Technology vendors whose compromise reaches GeneLabs
| Organisation | Relationship | Sector |
|---|---|---|
| Okta | Vendor | Identity |
| Microsoft | Vendor | Cloud and productivity |
| Amazon Web Services | Vendor | Cloud |
| Google | Vendor | Cloud |
| Snowflake | Vendor | Data platform |
| Salesforce | Vendor | SaaS |
| Workday | Vendor | SaaS |
| ServiceNow | Vendor | SaaS |
| CrowdStrike | Vendor | Security |
| Zscaler | Vendor | Security |
| Palo Alto Networks | Vendor | Security |
