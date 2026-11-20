"""Quick smoke test: emoji round-trip + persistence check. Run with the server up."""
import json
import urllib.request

BASE = "http://localhost:8000"
EMOJI_TEXT = "emoji test: \U0001F4CB"  # built from codepoint, never via console

def api(path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data else "GET",
    )
    return json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

assert api("/api/health") == {"status": "ok"}, "health failed"

posted = api("/api/clipboard", {"text": EMOJI_TEXT})
assert posted["text"] == EMOJI_TEXT, f"POST mangled: {posted['text']!r}"
assert posted["updated_at"], "no timestamp"

fetched = api("/api/clipboard")
assert fetched["text"] == EMOJI_TEXT, f"GET mangled: {fetched['text']!r}"
assert fetched["updated_at"] == posted["updated_at"], "timestamp mismatch"

with open("clipboard.json", encoding="utf-8") as f:
    on_disk = json.load(f)
assert on_disk["text"] == EMOJI_TEXT, f"file mangled: {on_disk['text']!r}"

html = urllib.request.urlopen(BASE + "/").read().decode("utf-8")
assert "Cloud Clipboard" in html and "uploadBtn" in html, "index page broken"

print("SMOKE TEST PASSED: health, POST/GET round-trip (utf-8 intact), file persistence, index page")
