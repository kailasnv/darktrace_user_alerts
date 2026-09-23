"""
Severity-specific email templates -- different tone/urgency/detail level
per severity, matching the actual Alert model's fields (alert_id,
fingerprint, source_id, watchlist_id, severity, confidence, state,
first_seen, last_seen, count). No free-text summary field exists on
this model, so templates describe the alert using its IDs and
timestamps instead.
"""

EMAIL_TEMPLATES = {
    "critical": (
        "CRITICAL ALERT -- IMMEDIATE ACTION REQUIRED\n\n"
        "Alert ID:     {alert_id}\n"
        "Fingerprint:  {fingerprint}\n"
        "Source:       {source_id}\n"
        "Watchlist:    {watchlist_id}\n"
        "Confidence:   {confidence:.0%}\n"
        "Occurrences:  {count} (first seen {first_seen:%Y-%m-%d %H:%M} UTC, "
        "last seen {last_seen:%Y-%m-%d %H:%M} UTC)\n"
        "Status:       {state}\n\n"
        "This requires immediate investigation. Acknowledge in the "
        "dashboard as soon as you've reviewed it.\n"
        "-- DarkTrace Alerting System"
    ),
    "high": (
        "HIGH SEVERITY ALERT\n\n"
        "Alert ID:     {alert_id}\n"
        "Source:       {source_id}\n"
        "Watchlist:    {watchlist_id}\n"
        "Confidence:   {confidence:.0%}\n"
        "Occurrences:  {count} (last seen {last_seen:%Y-%m-%d %H:%M} UTC)\n"
        "Status:       {state}\n\n"
        "Please review within the next few hours.\n"
        "-- DarkTrace Alerting System"
    ),
    "medium": (
        "Medium Severity Alert\n\n"
        "Alert ID:     {alert_id}\n"
        "Source:       {source_id}\n"
        "Watchlist:    {watchlist_id}\n"
        "Confidence:   {confidence:.0%}\n"
        "Occurrences:  {count}\n"
        "Status:       {state}\n\n"
        "No immediate action needed -- included in your regular review "
        "queue.\n"
        "-- DarkTrace Alerting System"
    ),
    "low": (
        "Low Severity Item (Digest)\n\n"
        "{alert_id} | source: {source_id} | watchlist: {watchlist_id} | "
        "seen {count}x | status: {state}\n"
        "-- DarkTrace Alerting System"
    ),
    "informational": (
        "Informational Item\n\n"
        "{alert_id}: {count} occurrence(s) from {source_id} "
        "(watchlist {watchlist_id})\n"
        "-- DarkTrace Alerting System"
    ),
}


