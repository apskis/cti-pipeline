#!/usr/bin/env python3
"""Tests for fetch_feeds.py. Run: python3 -m unittest scripts/test_fetch_feeds.py"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_feeds as ff  # noqa: E402

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>New &amp; exploited</title><link>https://example.test/a</link>
<pubDate>Wed, 07 Oct 2026 09:00:00 +0000</pubDate>
<description>&lt;p&gt;Patch &lt;b&gt;now&lt;/b&gt;.&lt;/p&gt;</description></item>
<item><title>Old story</title><link>https://example.test/b</link>
<pubDate>Tue, 01 Sep 2026 09:00:00 +0000</pubDate></item>
<item><title>No date</title><link>https://example.test/c</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom entry</title><link href="https://example.test/d"/>
<updated>2026-10-08T12:00:00Z</updated><summary>Short.</summary></entry></feed>"""

KEV = json.dumps({"catalogVersion": "2026.10.08", "vulnerabilities": [
    {"cveID": "CVE-2026-0001", "vendorProject": "Acme", "product": "Gateway", "dateAdded": "2026-10-08",
     "dueDate": "2026-10-11", "knownRansomwareCampaignUse": "Unknown",
     "vulnerabilityName": "Acme Gateway RCE", "shortDescription": "Remote code execution."},
    {"cveID": "CVE-2020-0002", "vendorProject": "Old", "product": "Thing", "dateAdded": "2020-01-01"},
]}).encode()

START, END = dt.date(2026, 10, 6), dt.date(2026, 10, 9)


class ParseTests(unittest.TestCase):
    def test_rss_window_keeps_dated_and_undated_drops_old(self) -> None:
        kept = ff.in_window(ff.rss_items(RSS), START, END)
        self.assertEqual([i.title for i in kept], ["New & exploited", "No date"])
        self.assertEqual(kept[0].summary, "Patch now .")

    def test_atom_link_comes_from_href(self) -> None:
        (item,) = ff.rss_items(ATOM)
        self.assertEqual((item.link, item.date), ("https://example.test/d", dt.date(2026, 10, 8)))

    def test_kev_dated_by_date_added_and_carries_due_date(self) -> None:
        items, version = ff.kev_items(KEV)
        kept = ff.in_window(items, START, END)
        self.assertEqual(version, "2026.10.08")
        self.assertEqual(len(kept), 1)
        self.assertIn("due 2026-10-11", kept[0].summary)

    def test_entity_expansion_is_refused(self) -> None:
        bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
        with self.assertRaises(Exception):
            ff.rss_items(bomb)

    def test_clean_caps_length(self) -> None:
        self.assertEqual(len(ff.clean("x" * 1000, 50)), 50)


class WindowTests(unittest.TestCase):
    def test_opens_day_before_newest_earlier_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("scan-2026-09-30.md", "scan-2026-10-08.md", "scan-2026-10-09.md", "notes.md"):
                (Path(tmp) / name).write_text("")
            # the report dated today is this run's own and must not shrink the window
            self.assertEqual(ff.scan_window(Path(tmp), dt.date(2026, 10, 9)),
                             (dt.date(2026, 10, 7), dt.date(2026, 10, 9)))

    def test_no_report_falls_back_to_three_days(self) -> None:
        self.assertEqual(ff.scan_window(Path("does-not-exist"), dt.date(2026, 10, 9)),
                         (dt.date(2026, 10, 6), dt.date(2026, 10, 9)))


class CollectTests(unittest.TestCase):
    def test_failure_is_a_status_and_names_the_url(self) -> None:
        result = ff.collect({"name": "Plain http", "url": "http://example.test/feed", "format": "rss"}, START, END)
        self.assertEqual(result.status, "failed")
        self.assertIn("http://example.test/feed", ff.render([result], START, END, END))


if __name__ == "__main__":
    unittest.main()
