"""
Appends one line per delivery attempt (success or failure) to a local text file. 
Only email_sender.py calls this; nothing else in the project needs to know it exists.
"""

import os
from datetime import datetime, timezone

#file for logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "audit_log.txt")



def log_delivery(channel: str, label: str, subject: str, success: bool, detail: str = ""):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = "SUCCESS" if success else "FAILED"
    line = f"[{timestamp}] [{status}] channel={channel} | {label} | subject={subject}"
    if detail:
        line += f" | detail={detail}" # (if not configered smtp, we are giving extra details)
 
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
 