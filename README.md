# Cloud Clipboard

A single shared clipboard: paste content, hit **Upload**, and it shows up for everyone on the page (after refresh). Built with FastAPI, served over HTTPS.

## Run locally (HTTPS, self-signed)

```powershell
python -m venv .venv                          # one time
.venv\Scripts\python.exe -m pip install -r requirements.txt   # one time

.\make_cert.ps1                # one time; add -LanIP 192.168.x.x for LAN access

$env:SSL_CERT_FILE="cert.pem"; $env:SSL_KEY_FILE="key.pem"
.venv\Scripts\python.exe main.py              # NOTE: use the venv's python, not plain `python`
```

(Or `.venv\Scripts\activate` first, then `pip install -r requirements.txt` and `python main.py` work as usual.)

Open **https://localhost:8000** — accept the self-signed certificate warning.

No cert? Skip the SSL vars and open http://localhost:8000 instead (plain HTTP).

## Deploy to Render

1. Push this folder to a GitHub repo.
2. On [Render](https://render.com): **New → Blueprint** → pick the repo (it reads `render.yaml`).
3. Done — you get an `https://….onrender.com` URL with an automatic Let's Encrypt cert, a persistent disk for the clipboard data, and a health check on `/api/health`.

## How it works

| Endpoint | Description |
|---|---|
| `GET /` | the page |
| `GET /api/clipboard` | current text + last-updated time |
| `POST /api/clipboard` | `{"text": "..."}` — replaces the clipboard |

- Data lives in `clipboard.json` (path configurable via `CLIPBOARD_FILE` env var); writes are atomic so restarts never corrupt it.
- No auth by design — it's an open toy clipboard. Don't put anything sensitive in it.
