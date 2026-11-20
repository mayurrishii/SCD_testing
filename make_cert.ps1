# One-time self-signed cert for local HTTPS testing.
# Run from the project folder:  .\make_cert.ps1
# Add your LAN IP so other devices on the network can connect too:
#   .\make_cert.ps1 -LanIP 192.168.1.42

param([string]$LanIP = "")

$san = "subjectAltName=DNS:localhost,IP:127.0.0.1"
if ($LanIP) { $san += ",IP:$LanIP" }

openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes `
  -subj "/CN=localhost" -addext $san

Write-Host "Created key.pem and cert.pem in $PWD" -ForegroundColor Green
