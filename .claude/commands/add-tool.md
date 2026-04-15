# /add-tool — Add a New Integration to BeastPay-OpenClaw

This skill walks through adding any new tool, provider, or service integration to the
BeastPay payment gateway. It covers all 5 layers that must be updated for a complete integration.

**Before using this skill, run `/beastpay-openclaw` to load full project context.**

---

## What "add-tool" means in this project

A "tool" is any new external service or internal capability wired into the gateway:
- A new **payment provider** (e.g. Coinbase Commerce, Binance Pay, NOWPayments)
- A new **KYC provider** (e.g. Sumsub, Persona, Onfido)
- A new **notification channel** (e.g. WhatsApp, Email/SMTP, Slack, Discord)
- A new **crypto on-ramp** (e.g. Simplex, Wyre, Banxa)
- A new **analytics/reporting** backend (e.g. Google Sheets, Airtable, webhook relay)
- A new **admin UI widget** or internal dashboard panel

---

## The 5-Layer Integration Checklist

When the user runs `/add-tool`, ask:
> "What tool or service do you want to add?"

Then work through all 5 layers below. Check off each layer as it is completed.

---

### Layer 1 — Config (`config.py`)

Add all credentials and toggles as environment variables:

```python
# Tool: <TOOL_NAME>
TOOLNAME_API_KEY    = os.getenv("TOOLNAME_API_KEY", "")
TOOLNAME_SECRET     = os.getenv("TOOLNAME_SECRET",  "")
TOOLNAME_ENABLED    = bool(os.getenv("TOOLNAME_API_KEY", ""))
TOOLNAME_WEBHOOK_SECRET = os.getenv("TOOLNAME_WEBHOOK_SECRET", "")
```

Also add to `.env`:
```bash
export TOOLNAME_API_KEY="your-key-here"
export TOOLNAME_SECRET="your-secret-here"
```

---

### Layer 2 — Backend Module

**For a payment provider** → create `providers/<toolname>.py`:
```python
class ToolNameProvider:
    name = "toolname"
    def build_widget_url(self, payment: dict) -> str: ...
    def verify_webhook(self, raw_body: bytes, sig: str) -> bool: ...
    def parse_webhook(self, payload: dict) -> dict: ...
        # Must return: {payment_id, provider_order_id, provider_tx_id,
        #               status, crypto_amount, exchange_rate, fee_amount}
```
Register in `providers/__init__.py`:
```python
from .toolname import ToolNameProvider
PROVIDERS["toolname"] = ToolNameProvider()
```

**For a notification/service tool** → create `<toolname>.py` at project root:
```python
async def notify_event(data: dict) -> bool: ...
async def send_message(text: str) -> bool: ...
def is_configured() -> dict: ...
```

---

### Layer 3 — Server Endpoints (`server.py`)

Add API endpoints for the tool:

```python
# ─── <ToolName> endpoints ──────────────────────────────────────────────────
@app.get("/api/<toolname>/status", dependencies=[Depends(require_admin)])
async def toolname_status():
    return toolname_module.is_configured()

@app.post("/api/<toolname>/test", dependencies=[Depends(require_admin)])
async def toolname_test():
    ok = await toolname_module.send_test()
    if not ok:
        raise HTTPException(502, "Tool unreachable. Check credentials.")
    return {"sent": True}

# If it has webhooks:
@app.post("/webhooks/<toolname>")
async def webhook_toolname(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get("<toolname>-signature", "")
    provider = get_provider("<toolname>")
    if not provider.verify_webhook(raw_body, sig):
        raise HTTPException(401, "Invalid signature")
    payload = await request.json()
    background_tasks.add_task(_process_webhook, provider, payload)
    return {"received": True}
```

Hook into existing events (payment initiated, status update, link created):
```python
# In initiate_payment():
asyncio.create_task(toolname_module.notify_new_payment(payment))

# In _process_webhook():
await toolname_module.notify_payment_update(payment, parsed["status"], parsed)
```

---

### Layer 4 — Admin Web UI (`web/admin.html`)

Add a new nav item and page section:

```html
<!-- Sidebar nav -->
<div class="nav-item" data-page="toolname" onclick="showPage('toolname')">
  <span class="icon">🔧</span> ToolName
</div>

<!-- Page section -->
<div class="page" id="page-toolname">
  <div class="page-title">ToolName Integration</div>
  <div class="page-sub">Manage ToolName settings and status</div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Status</div>
      <div class="stat-value" id="tn-status">—</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Actions</div>
    <button class="btn btn-primary" onclick="testToolName()">Send Test</button>
  </div>
</div>
```

Add JS to fetch status and trigger actions:
```javascript
async function loadToolNameStatus() {
  const s = await api('/api/toolname/status');
  document.getElementById('tn-status').textContent = s.enabled ? 'Active' : 'Not Configured';
}

async function testToolName() {
  const r = await api('/api/toolname/test', { method: 'POST' });
  toast(r.sent ? 'Test sent!' : 'Failed');
}
```

Wire into `showPage()` switch:
```javascript
if (name === 'toolname') loadToolNameStatus();
```

---

### Layer 5 — PowerShell Admin Console (`admin.ps1`)

Add a menu entry and function block:

```powershell
# In Write-Menu — add new option:
Write-Host "  │  [T2] <ToolName> Menu              │" -ForegroundColor White

# In main switch:
"T2" { Show-ToolNameMenu }

# New function:
function Show-ToolNameMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkGreen
        Write-Host "  │  🔧 TOOLNAME INTEGRATION            │" -ForegroundColor Green
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkGreen
        Write-Host "  │  [1] Show Status                    │" -ForegroundColor White
        Write-Host "  │  [2] Send Test                      │" -ForegroundColor White
        Write-Host "  │  [B] Back                           │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkGreen
        $choice = Read-Host "  Choice"
        switch ($choice.ToUpper()) {
            "1" {
                $s = Invoke-API "/api/toolname/status"
                Write-Host "  Enabled: $($s.enabled)" -ForegroundColor $(if($s.enabled){"Green"}else{"Red"})
                Pause-Prompt
            }
            "2" {
                Invoke-API "/api/toolname/test" "POST" | Out-Null
                Write-Host "  ✅ Test sent!" -ForegroundColor Green
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}
```

---

## Quick-Add Reference Table

| Tool Type         | Provider File | Server Endpoints | Webhook | Telegram Hook |
|-------------------|--------------|-----------------|---------|---------------|
| Payment provider  | `providers/X.py` | status, test, webhook | yes | yes |
| Notification tool | `X.py`       | status, test, send | no  | optional |
| KYC provider      | `kyc/X.py`   | status, verify  | yes     | yes |
| Analytics         | `analytics/X.py` | status, report | no | optional |

---

## Usage

When the user says `/add-tool [name]` or describes a new tool to integrate:

1. Identify which of the 4 tool types it is
2. Ask for credentials/API keys needed
3. Work through all 5 layers in order
4. Run a syntax check after each file edit:
   ```bash
   python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"
   ```
5. Test the integration:
   ```bash
   cd /home/kali/payment-gateway && source .env
   python3 -c "import <toolname>; print(<toolname>.is_configured())"
   ```
6. Send a test notification / API call to confirm end-to-end

Always update `.env` with the new tool's credentials template.
