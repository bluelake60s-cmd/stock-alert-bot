import json
import os

# State is a single JSON file committed back to the repo (same pattern as the
# repost-bot). It only needs a de-dupe set of alert ids we have already sent.
SEEN_CAP = 8000  # keep the file from growing unbounded


def load(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen": []}


def save(path, state):
    state["seen"] = state.get("seen", [])[-SEEN_CAP:]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
