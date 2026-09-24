"""
Renders emails using Jinja2, from HTML files that were compiled from MJML source.
 
MJML is a build-time step (run once, or whenever the design changes).
 
Jinja2 then fills in the actual alert data into that compiled HTML at
send time.
"""


import os
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Only critical/high are single-alert immediate templates.
# Medium (batched) and low/informational (digest) share batch.html
SEVERITY_TEMPLATE_FILES = {
    "critical": "critical.html",
    "high": "high.html",
#batch.html is not needed here. its directly called in the funtion below
}
 

"""Single-alert send -- critical/high only."""
def render_email(alert: dict) -> tuple[str, str]:
    template_file = SEVERITY_TEMPLATE_FILES[alert["severity"]]
    template = env.get_template(template_file)
    body = template.render(**alert)
    subject = f"[{alert['severity'].upper()}] DarkTrace alert {alert['alert_id']}"
    return subject, body
 
 
def render_batch_email(alerts: list, title: str) -> tuple[str, str]:
    template = env.get_template("batch.html") 
    body = template.render(alerts=alerts, title=title)
    subject = f"[BATCH] {title} -- {len(alerts)} alert(s)"
    return subject, body