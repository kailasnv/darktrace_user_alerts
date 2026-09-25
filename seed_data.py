"""Sample data: ALERTS (initial table contents) and HARDCODED_ALERTS (live demo feed)."""
from datetime import datetime, timezone


def _t(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc)


# (alert_id, fingerprint, source_id, watchlist_id, severity, confidence, state,
#  first_seen, last_seen, count)
_ROWS = [
    ("alr_001", "fp_leak_acmecorp",         "src_pastesite_x",   "wl_credential_leaks",   "critical",      0.950, "new",            _t(20, 8, 15), _t(22, 9, 30), 1),
    ("alr_002", "fp_leak_acmecorp",         "src_pastesite_y",   "wl_credential_leaks",   "critical",      0.910, "new",            _t(21, 14),    _t(22, 10, 5), 1),  # duplicate of alr_001
    ("alr_003", "fp_leak_othercorp",        "src_pastesite_x",   "wl_credential_leaks",   "critical",      0.880, "new",            _t(22, 6),     _t(22, 6),     1),
    ("alr_004", "fp_domain_impersonation_1", "src_domainwatch",  "wl_brand_protection",   "high",          0.820, "new",            _t(19, 11),    _t(22, 8),     2),
    ("alr_005", "fp_cve_mention_1",         "src_forumscrape",   "wl_cve_watch",          "high",          0.747, "new",            _t(21, 3),     _t(21, 3),     1),
    ("alr_006", "fp_exposed_api_key",       "src_githubscrape",  "wl_secrets_exposure",   "high",          0.815, "acknowledged",   _t(18, 9),     _t(20, 12),    5),
    ("alr_007", "fp_cve_mention_2",         "src_forumscrape",   "wl_cve_watch",          "medium",        0.530, "new",            _t(22, 4),     _t(22, 4),     3),
    ("alr_008", "fp_brand_mention_1",       "src_socialscrape",  "wl_brand_protection",   "medium",        0.743, "investigating",  _t(17, 10),    _t(21, 15),    1),
    ("alr_009", "fp_typosquat_domain_1",    "src_domainwatch",   "wl_brand_protection",   "medium",        0.792, "new",            _t(22, 1),     _t(22, 7),     5),
    ("alr_010", "fp_general_chatter_1",     "src_chatterfeed",   "wl_general_monitoring", "low",           0.619, "new",            _t(20, 5),     _t(22, 2),     4),
    ("alr_011", "fp_general_chatter_2",     "src_chatterfeed",   "wl_general_monitoring", "low",           0.853, "resolved",       _t(15, 8),     _t(16, 8),     2),
    ("alr_012", "fp_brand_mention_2",       "src_socialscrape",  "wl_brand_protection",   "low",           0.755, "new",            _t(21, 20),    _t(22, 3),     4),
    ("alr_013", "fp_industry_mention_1",    "src_chatterfeed",   "wl_general_monitoring", "informational", 0.977, "new",            _t(22, 0),     _t(22, 0),     5),
    ("alr_014", "fp_industry_mention_2",    "src_forumscrape",   "wl_general_monitoring", "informational", 0.664, "false_positive", _t(19, 6),     _t(19, 6),     2),
    ("alr_015", "fp_industry_mention_3",    "src_chatterfeed",   "wl_general_monitoring", "informational", 0.799, "new",            _t(20, 18),    _t(22, 5),     5),
]
_KEYS = ("alert_id", "fingerprint", "source_id", "watchlist_id", "severity",
         "confidence", "state", "first_seen", "last_seen", "count")

ALERTS = [dict(zip(_KEYS, row)) for row in _ROWS]


HARDCODED_ALERTS = [
    {"alert_id": "alr_001", "fingerprint": "fp_leak_acmecorp", "severity": "critical",
     "confidence": 0.95, "count": 1, "state": "new", "source": "PasteSite-X",
     "summary": "Employee credentials for acmecorp.com found in a paste dump"},
    {"alert_id": "alr_002", "fingerprint": "fp_leak_acmecorp", "severity": "critical",
     "confidence": 0.91, "count": 1, "state": "new", "source": "PasteSite-Y",
     "summary": "Same acmecorp.com credential leak, re-posted on a second site"},
    # ^ duplicate of alr_001 -- same fingerprint, should merge into one alert
    {"alert_id": "alr_003", "fingerprint": "fp_domain_impersonation_1", "severity": "high",
     "confidence": 0.82, "count": 2, "state": "new", "source": "DomainWatch",
     "summary": "Lookalike domain 'acme-corp-login.com' registered this week"},
    {"alert_id": "alr_004", "fingerprint": "fp_cve_mention_1", "severity": "medium",
     "confidence": 0.70, "count": 1, "state": "new", "source": "ForumScrape",
     "summary": "Forum post referencing a CVE affecting our product line"},
    {"alert_id": "alr_005", "fingerprint": "fp_brand_mention_1", "severity": "low",
     "confidence": 0.55, "count": 3, "state": "new", "source": "SocialScrape",
     "summary": "Brand name mentioned in a low-relevance forum thread"},
    {"alert_id": "alr_006", "fingerprint": "fp_general_chatter_1", "severity": "informational",
     "confidence": 0.40, "count": 1, "state": "new", "source": "ChatterFeed",
     "summary": "General dark-web chatter mentioning the industry, not us specifically"},
]
