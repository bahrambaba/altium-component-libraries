#!/usr/bin/env python3
"""Create update summary for GitHub Actions."""
import json
from datetime import datetime

summary = {
    "last_update": datetime.utcnow().isoformat(),
    "status": "success",
}
with open("data/last_update.json", "w") as f:
    json.dump(summary, f, indent=2)
print("Summary created")
