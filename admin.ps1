#requires -Version 5.1
<#
.SYNOPSIS
    Internal PowerShell Admin Console for CryptoPay Gateway
.DESCRIPTION
    CLI dashboard for monitoring payments, managing links, and checking stats.
    Run: pwsh admin.ps1  OR  powershell.exe -File admin.ps1
#>

# ─── Configuration ─────────────────────────────────────────────────────────────
$Script:BaseUrl  = if ($env:GATEWAY_URL)  { $env:GATEWAY_URL  } else { "http://localhost:8000" }
$Script:AdminKey = if ($env:ADMIN_API_KEY){ $env:ADMIN_API_KEY } else { "admin-secret-change-me" }
$Script:Headers  = @{ "X-Api-Key" = $Script:AdminKey; "Content-Type" = "application/json" }

# ─── Helpers ───────────────────────────────────────────────────────────────────
function Invoke-API {
    param(
        [string]$Path,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    $url = "$Script:BaseUrl$Path"
    try {
        $params = @{
            Uri         = $url
            Method      = $Method
            Headers     = $Script:Headers
            ErrorAction = "Stop"
        }
        if ($Body) {
            $params.Body        = ($Body | ConvertTo-Json -Depth 10)
            $params.ContentType = "application/json"
        }
        $response = Invoke-RestMethod @params
        return $response
    }
    catch {
        $msg = $_.Exception.Message
        Write-Host "  [ERROR] API call failed: $msg" -ForegroundColor Red
        return $null
    }
}

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ██████╗ ███████╗ █████╗ ███████╗████████╗██████╗  █████╗ ██╗   ██╗" -ForegroundColor Cyan
    Write-Host "  ██╔══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚██╗ ██╔╝" -ForegroundColor Cyan
    Write-Host "  ██████╔╝█████╗  ███████║███████╗   ██║   ██████╔╝███████║ ╚████╔╝ " -ForegroundColor Blue
    Write-Host "  ██╔══██╗██╔══╝  ██╔══██║╚════██║   ██║   ██╔═══╝ ██╔══██║  ╚██╔╝  " -ForegroundColor Blue
    Write-Host "  ██████╔╝███████╗██║  ██║███████║   ██║   ██║     ██║  ██║   ██║   " -ForegroundColor Magenta
    Write-Host "  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝   ╚═╝   " -ForegroundColor Magenta
    Write-Host ""
    Write-Host "            by  O P E N C L A W  ·  @Openclawbeastpay_bot" -ForegroundColor DarkGray
    Write-Host "  " + ("─" * 68) -ForegroundColor DarkGray
    Write-Host "  Gateway: $Script:BaseUrl" -NoNewline -ForegroundColor DarkGray
    # Quick health ping
    try {
        $h = Invoke-RestMethod -Uri "$Script:BaseUrl/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  ●  ONLINE" -ForegroundColor Green
    } catch {
        Write-Host "  ●  OFFLINE" -ForegroundColor Red
    }
    Write-Host ""
}

function Write-Menu {
    Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkCyan
    Write-Host "  │  MAIN MENU                          │" -ForegroundColor DarkCyan
    Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkCyan
    Write-Host "  │  [0] 🤖 BeastPay Bot Hub            │" -ForegroundColor White
    Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkGray
    Write-Host "  │  [1] Dashboard / Stats              │" -ForegroundColor White
    Write-Host "  │  [2] List Payment Links             │" -ForegroundColor White
    Write-Host "  │  [3] Create Payment Link            │" -ForegroundColor White
    Write-Host "  │  [4] View All Payments              │" -ForegroundColor White
    Write-Host "  │  [5] Check Payment Status           │" -ForegroundColor White
    Write-Host "  │  [6] Filter Payments by Status      │" -ForegroundColor White
    Write-Host "  │  [7] Add Merchant                   │" -ForegroundColor White
    Write-Host "  │  [8] Export Payments to CSV         │" -ForegroundColor White
    Write-Host "  │  [9] Health Check                   │" -ForegroundColor White
    Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkGray
    Write-Host "  │  [T] Telegram Menu                  │" -ForegroundColor Magenta
    Write-Host "  │  [W] WhatsApp Menu                  │" -ForegroundColor Green
    Write-Host "  │  [N] NOWPayments Menu               │" -ForegroundColor Cyan
    Write-Host "  │  [K] KYC / Sumsub Menu              │" -ForegroundColor Yellow
    Write-Host "  │  [S] 💜 Stripe Menu                 │" -ForegroundColor Magenta
    Write-Host "  │  [L] 🔐 Lockbox AI Parser           │" -ForegroundColor Cyan
    Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkCyan
    Write-Host "  │  [Q] Quit                           │" -ForegroundColor Yellow
    Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkCyan
    Write-Host ""
}

function Show-Stats {
    Write-Host "`n  Loading dashboard..." -ForegroundColor DarkGray
    $stats = Invoke-API "/api/stats"
    if (-not $stats) { return }

    Write-Host ""
    Write-Host "  ╔═══════════════════ DASHBOARD ═══════════════════╗" -ForegroundColor Green
    Write-Host ("  ║  Total Payments:  {0,-6}   Active Links: {1,-8}║" -f $stats.total_payments, $stats.active_links) -ForegroundColor White
    Write-Host ("  ║  Completed:       {0,-6}   Pending:      {1,-8}║" -f $stats.completed, $stats.pending) -ForegroundColor White
    Write-Host ("  ║  Failed:          {0,-6}   Conversion:   {1}%{2,-5}║" -f $stats.failed, $stats.conversion_rate, "") -ForegroundColor White
    Write-Host ("  ║  Volume (USD):   `${0,-35}║" -f $stats.total_volume_usd) -ForegroundColor Green
    Write-Host "  ╚═════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Pause-Prompt
}

function Show-Links {
    Write-Host "`n  Loading payment links..." -ForegroundColor DarkGray
    $links = Invoke-API "/api/links"
    if (-not $links) { return }
    if ($links.Count -eq 0) {
        Write-Host "  No payment links found." -ForegroundColor Yellow
        Pause-Prompt; return
    }

    Write-Host ""
    Write-Host ("  {0,-18} {1,-12} {2,-6} {3,-8} {4,-5} {5}" -f "ID","AMOUNT","FIAT","CRYPTO","USES","STATUS") -ForegroundColor Cyan
    Write-Host "  " + ("─" * 70) -ForegroundColor DarkGray
    foreach ($l in $links) {
        $amount = if ($l.amount) { $l.amount } else { "variable" }
        $crypto = if ($l.crypto_currency) { $l.crypto_currency } else { "any" }
        $status = if ($l.is_active -eq 1) { "ACTIVE" } else { "INACTIVE" }
        $color  = if ($l.is_active -eq 1) { "Green" } else { "Red" }
        Write-Host ("  {0,-18} {1,-12} {2,-6} {3,-8} {4,-5}" -f $l.id, $amount, $l.fiat_currency, $crypto, $l.use_count) -NoNewline
        Write-Host " $status" -ForegroundColor $color
        Write-Host "  URL: $($l.payment_url)" -ForegroundColor DarkGray
        Write-Host ""
    }
    Pause-Prompt
}

function Create-Link {
    Write-Host ""
    Write-Host "  ─── Create Payment Link ───" -ForegroundColor Cyan
    Write-Host ""
    $wallet = Read-Host "  Wallet Address (required)"
    if (-not $wallet.Trim()) { Write-Host "  Wallet required." -ForegroundColor Red; Pause-Prompt; return }

    $amountStr = Read-Host "  Fixed Amount in USD (leave blank for variable)"
    $cryptos   = @("USDT","USDC","ETH","BTC","BNB","SOL","TRX","MATIC","")
    Write-Host "  Crypto options: USDT, USDC, ETH, BTC, BNB, SOL, TRX, MATIC (blank = customer chooses)"
    $crypto    = Read-Host "  Crypto currency"
    $desc      = Read-Host "  Description (e.g. Invoice #1234)"
    $reusable  = (Read-Host "  Reusable link? [Y/n]").ToLower()

    $body = @{
        wallet_address = $wallet.Trim()
        fiat_currency  = "USD"
        is_reusable    = ($reusable -ne "n")
        description    = $desc.Trim()
    }
    if ($amountStr.Trim()) { $body.amount = [double]$amountStr }
    if ($crypto.Trim())    { $body.crypto_currency = $crypto.Trim().ToUpper() }

    $result = Invoke-API "/api/links" "POST" $body
    if ($result) {
        Write-Host ""
        Write-Host "  ✅ Payment Link Created!" -ForegroundColor Green
        Write-Host "  Link ID:  $($result.id)" -ForegroundColor White
        Write-Host "  Pay URL:  $($result.payment_url)" -ForegroundColor Cyan
        Write-Host "  API URL:  $($result.api_url)" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  Share the Pay URL with your customer." -ForegroundColor Yellow
    }
    Pause-Prompt
}

function Show-Payments {
    param([string]$StatusFilter = "")
    Write-Host "`n  Loading payments..." -ForegroundColor DarkGray
    $path = "/api/payments"
    if ($StatusFilter) { $path += "?status=$StatusFilter" }
    $payments = Invoke-API $path
    if (-not $payments) { return }
    if ($payments.Count -eq 0) {
        Write-Host "  No payments found." -ForegroundColor Yellow
        Pause-Prompt; return
    }

    Write-Host ""
    Write-Host ("  {0,-10} {1,-10} {2,-6} {3,-8} {4,-25} {5,-12} {6}" -f `
        "ID","AMOUNT","FIAT","CRYPTO","CUSTOMER","STATUS","DATE") -ForegroundColor Cyan
    Write-Host "  " + ("─" * 85) -ForegroundColor DarkGray

    foreach ($p in $payments) {
        $statusColor = switch ($p.status) {
            "completed"  { "Green"  }
            "pending"    { "Yellow" }
            "processing" { "Cyan"   }
            "failed"     { "Red"    }
            default      { "Gray"   }
        }
        $shortId = $p.id.Substring(0, [Math]::Min(8, $p.id.Length)) + "…"
        $date    = if ($p.created_at.Length -ge 16) { $p.created_at.Substring(0,16) } else { $p.created_at }
        $email   = if ($p.customer_email) { $p.customer_email } else { "—" }
        Write-Host ("  {0,-10} {1,-10} {2,-6} {3,-8} {4,-25} " -f `
            $shortId, $p.amount, $p.fiat_currency, $p.crypto_currency, $email) -NoNewline
        Write-Host ("{0,-12}" -f $p.status.ToUpper()) -ForegroundColor $statusColor -NoNewline
        Write-Host " $date"
    }
    Write-Host ""
    Write-Host "  Total: $($payments.Count) payments" -ForegroundColor DarkGray
    Pause-Prompt
}

function Check-Payment {
    Write-Host ""
    $pid = Read-Host "  Enter Payment ID (or first 8 chars)"
    $payment = Invoke-API "/api/payments/$($pid.Trim())"
    if (-not $payment) { Pause-Prompt; return }

    $statusColor = switch ($payment.status) {
        "completed"  { "Green"  }
        "pending"    { "Yellow" }
        "processing" { "Cyan"   }
        "failed"     { "Red"    }
        default      { "Gray"   }
    }

    Write-Host ""
    Write-Host "  Payment Details" -ForegroundColor Cyan
    Write-Host "  ─────────────────────────────────────"
    Write-Host "  ID:              $($payment.id)"
    Write-Host "  Status:          " -NoNewline; Write-Host $payment.status.ToUpper() -ForegroundColor $statusColor
    Write-Host "  Amount:          `$$($payment.amount) $($payment.fiat_currency)"
    Write-Host "  Crypto:          $($payment.crypto_currency)"
    Write-Host "  Wallet:          $($payment.wallet_address)"
    Write-Host "  Customer Email:  $($payment.customer_email)"
    Write-Host "  Customer Name:   $($payment.customer_name)"
    Write-Host "  Provider:        $($payment.provider)"
    Write-Host "  Provider Tx ID:  $($payment.provider_tx_id)"
    Write-Host "  Crypto Amount:   $($payment.crypto_amount)"
    Write-Host "  Exchange Rate:   $($payment.exchange_rate)"
    Write-Host "  Created:         $($payment.created_at)"
    Write-Host "  Updated:         $($payment.updated_at)"
    Write-Host ""
    Pause-Prompt
}

function Filter-Payments {
    Write-Host ""
    Write-Host "  Filter by status:" -ForegroundColor Cyan
    Write-Host "    [1] pending"
    Write-Host "    [2] processing"
    Write-Host "    [3] completed"
    Write-Host "    [4] failed"
    $choice = Read-Host "  Choice"
    $statusMap = @{"1"="pending";"2"="processing";"3"="completed";"4"="failed"}
    $status = $statusMap[$choice]
    if ($status) { Show-Payments $status } else { Write-Host "  Invalid choice" -ForegroundColor Red; Pause-Prompt }
}

function Add-Merchant {
    Write-Host ""
    Write-Host "  ─── Add Merchant ───" -ForegroundColor Cyan
    $name    = Read-Host "  Business Name"
    $email   = Read-Host "  Email"
    $webhook = Read-Host "  Webhook URL (optional, press Enter to skip)"

    $body = @{ name = $name.Trim(); email = $email.Trim() }
    if ($webhook.Trim()) { $body.webhook_url = $webhook.Trim() }

    $result = Invoke-API "/api/merchants" "POST" $body
    if ($result) {
        Write-Host ""
        Write-Host "  ✅ Merchant Created!" -ForegroundColor Green
        Write-Host "  ID:      $($result.id)" -ForegroundColor White
        Write-Host "  Name:    $($result.name)" -ForegroundColor White
        Write-Host "  API Key: $($result.api_key)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  ⚠  Save the API Key — it will not be shown again!" -ForegroundColor Red
    }
    Pause-Prompt
}

function Export-Payments {
    Write-Host "`n  Exporting all payments to CSV..." -ForegroundColor DarkGray
    $payments = Invoke-API "/api/payments?limit=10000"
    if (-not $payments -or $payments.Count -eq 0) {
        Write-Host "  No payments to export." -ForegroundColor Yellow
        Pause-Prompt; return
    }

    $filename = "payments_export_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
    $payments | Select-Object id, amount, fiat_currency, crypto_currency, `
        customer_email, customer_name, status, provider, provider_tx_id, `
        crypto_amount, exchange_rate, created_at, updated_at `
        | Export-Csv -Path $filename -NoTypeInformation

    Write-Host "  ✅ Exported $($payments.Count) payments to: $filename" -ForegroundColor Green
    Pause-Prompt
}

function Health-Check {
    Write-Host "`n  Checking gateway health..." -ForegroundColor DarkGray
    $h = Invoke-API "/health"
    if ($h) {
        Write-Host "  ✅ Gateway is UP" -ForegroundColor Green
        Write-Host "  Status:    $($h.status)"
        Write-Host "  Timestamp: $($h.timestamp)"
    } else {
        Write-Host "  ❌ Gateway is DOWN or unreachable at $Script:BaseUrl" -ForegroundColor Red
    }
    Pause-Prompt
}

function Pause-Prompt {
    Write-Host "  Press Enter to continue…" -ForegroundColor DarkGray
    [void][System.Console]::ReadLine()
}

# ─── Telegram Functions ───────────────────────────────────────────────────────
function Show-TelegramMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkMagenta
        Write-Host "  │  📱 TELEGRAM INTEGRATION            │" -ForegroundColor Magenta
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkMagenta
        Write-Host "  │  [1] Show Bot Status                │" -ForegroundColor White
        Write-Host "  │  [2] Send Test Ping                 │" -ForegroundColor White
        Write-Host "  │  [3] Push Stats Summary Now         │" -ForegroundColor White
        Write-Host "  │  [4] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [5] Set Bot Token (this session)   │" -ForegroundColor White
        Write-Host "  │  [6] Set Chat ID (this session)     │" -ForegroundColor White
        Write-Host "  │  [B] Back to Main Menu              │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkMagenta
        Write-Host ""
        $choice = Read-Host "  Enter choice"
        switch ($choice.Trim().ToUpper()) {
            "1" { Show-TelegramStatus  }
            "2" { Send-TelegramTest    }
            "3" { Send-TelegramSummary }
            "4" { Show-TelegramGuide   }
            "5" { Set-TelegramToken    }
            "6" { Set-TelegramChatId   }
            "B" { return }
            default {
                Write-Host "  Invalid choice." -ForegroundColor Red
                Start-Sleep -Milliseconds 800
            }
        }
    } while ($true)
}

function Show-TelegramStatus {
    Write-Host "`n  Fetching Telegram bot status..." -ForegroundColor DarkGray
    $status = Invoke-API "/api/telegram/status"
    if (-not $status) { Pause-Prompt; return }

    Write-Host ""
    Write-Host "  ╔════════════════ TELEGRAM STATUS ════════════════╗" -ForegroundColor Magenta

    $enabledColor = if ($status.enabled) { "Green" } else { "Red" }
    $enabledText  = if ($status.enabled) { "✅  ENABLED" } else { "❌  DISABLED" }
    Write-Host ("  ║  Bot:        {0,-36}║" -f $enabledText) -ForegroundColor $enabledColor
    Write-Host ("  ║  Token:      {0,-36}║" -f $status.bot_token) -ForegroundColor White
    Write-Host ("  ║  Chat ID:    {0,-36}║" -f $status.chat_id) -ForegroundColor White
    Write-Host "  ╠═════════════════════════════════════════════════╣" -ForegroundColor Magenta

    $yn = { param($v) if ($v) { "ON " } else { "off" } }
    Write-Host ("  ║  Notify new payments:    {0,-24}║" -f (& $yn $status.notify_new_payment)) -ForegroundColor White
    Write-Host ("  ║  Notify completed:       {0,-24}║" -f (& $yn $status.notify_completed)) -ForegroundColor White
    Write-Host ("  ║  Notify failed:          {0,-24}║" -f (& $yn $status.notify_failed)) -ForegroundColor White
    Write-Host ("  ║  Notify new links:       {0,-24}║" -f (& $yn $status.notify_new_link)) -ForegroundColor White
    Write-Host ("  ║  Daily summary:          {0,-24}║" -f (& $yn $status.notify_daily_summary)) -ForegroundColor White
    Write-Host "  ╚═════════════════════════════════════════════════╝" -ForegroundColor Magenta

    if (-not $status.enabled) {
        Write-Host ""
        Write-Host "  ⚠  Telegram is not configured." -ForegroundColor Yellow
        Write-Host "  Set env vars or use options [5] and [6] in this menu." -ForegroundColor DarkGray
    }
    Write-Host ""
    Pause-Prompt
}

function Send-TelegramTest {
    Write-Host "`n  Sending test message to Telegram..." -ForegroundColor DarkGray
    $result = Invoke-API "/api/telegram/test" "POST"
    if ($result) {
        Write-Host "  ✅ Test message sent! Check your Telegram." -ForegroundColor Green
        Write-Host "  Chat ID: $($result.chat_id)" -ForegroundColor DarkGray
    }
    Pause-Prompt
}

function Send-TelegramSummary {
    Write-Host "`n  Pushing stats summary to Telegram..." -ForegroundColor DarkGray
    $result = Invoke-API "/api/telegram/summary" "POST"
    if ($result) {
        Write-Host "  ✅ Summary sent to Telegram!" -ForegroundColor Green
        Write-Host "  Total payments: $($result.stats.total_payments)" -ForegroundColor DarkGray
        Write-Host "  Completed:      $($result.stats.completed)" -ForegroundColor DarkGray
        Write-Host "  Volume (USD):  `$$($result.stats.total_volume_usd)" -ForegroundColor DarkGray
    }
    Pause-Prompt
}

function Show-TelegramGuide {
    Write-Host ""
    Write-Host "  ──────────────────────────────────────────────────" -ForegroundColor Magenta
    Write-Host "  📱  TELEGRAM BOT SETUP GUIDE" -ForegroundColor Magenta
    Write-Host "  ──────────────────────────────────────────────────" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  STEP 1 — Create Bot" -ForegroundColor Cyan
    Write-Host "    1. Open Telegram, search @BotFather"
    Write-Host "    2. Send /newbot"
    Write-Host "    3. Choose a name (e.g. 'MyCryptoPay Bot')"
    Write-Host "    4. Copy the token: 123456789:ABCdefGHI..."
    Write-Host ""
    Write-Host "  STEP 2 — Get your Chat ID" -ForegroundColor Cyan
    Write-Host "    Personal:  Message @userinfobot → copy 'Id'"
    Write-Host "    Group:     Add @RawDataBot to group → send msg → read chat.id"
    Write-Host "    Channel:   Use @channel_username or numeric ID (prefix -100)"
    Write-Host ""
    Write-Host "  STEP 3 — Add bot to your chat/channel" -ForegroundColor Cyan
    Write-Host "    For groups:   Add bot as member"
    Write-Host "    For channels: Add bot as admin"
    Write-Host ""
    Write-Host "  STEP 4 — Set environment variables" -ForegroundColor Cyan
    Write-Host "    Linux / Kali:" -ForegroundColor White
    Write-Host '    export TELEGRAM_BOT_TOKEN="123456:ABCdef..."' -ForegroundColor Yellow
    Write-Host '    export TELEGRAM_CHAT_ID="-100123456789"' -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Windows PowerShell:" -ForegroundColor White
    Write-Host '    $env:TELEGRAM_BOT_TOKEN = "123456:ABCdef..."' -ForegroundColor Yellow
    Write-Host '    $env:TELEGRAM_CHAT_ID   = "-100123456789"' -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  STEP 5 — Restart the gateway server and test (option [2])" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  OPTIONAL: Toggle specific notifications" -ForegroundColor Cyan
    Write-Host '    export TG_NOTIFY_NEW_PAYMENT=1    # 1=on, 0=off' -ForegroundColor DarkGray
    Write-Host '    export TG_NOTIFY_COMPLETED=1' -ForegroundColor DarkGray
    Write-Host '    export TG_NOTIFY_FAILED=1' -ForegroundColor DarkGray
    Write-Host '    export TG_NOTIFY_NEW_LINK=1' -ForegroundColor DarkGray
    Write-Host '    export TG_NOTIFY_DAILY_SUMMARY=1' -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  ──────────────────────────────────────────────────" -ForegroundColor Magenta
    Write-Host ""
    Pause-Prompt
}

function Set-TelegramToken {
    Write-Host ""
    $token = Read-Host "  Enter Bot Token (from @BotFather)"
    if (-not $token.Trim()) { Pause-Prompt; return }
    $env:TELEGRAM_BOT_TOKEN = $token.Trim()
    Write-Host "  ✅ TELEGRAM_BOT_TOKEN set for this session." -ForegroundColor Green
    Write-Host "  ⚠  Restart the gateway server to apply the change." -ForegroundColor Yellow
    Pause-Prompt
}

function Set-TelegramChatId {
    Write-Host ""
    $chatId = Read-Host "  Enter Chat ID (e.g. -100123456789 or @yourchannel)"
    if (-not $chatId.Trim()) { Pause-Prompt; return }
    $env:TELEGRAM_CHAT_ID = $chatId.Trim()
    Write-Host "  ✅ TELEGRAM_CHAT_ID set for this session." -ForegroundColor Green
    Write-Host "  ⚠  Restart the gateway server to apply the change." -ForegroundColor Yellow
    Pause-Prompt
}

# ─── BeastPay Bot Hub ─────────────────────────────────────────────────────────
function Show-BeastPayBot {
    Write-Banner
    Write-Host "  ╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "  ║  🤖  BEASTPAY BOT HUB  ·  Full Feature Overview                ║" -ForegroundColor Magenta
    Write-Host "  ╠══════════════════════════════════════════════════════════════════╣" -ForegroundColor Magenta
    Write-Host "  ║  Bot:      @Openclawbeastpay_bot                                ║" -ForegroundColor White
    Write-Host "  ║  Chat ID:  933545457  (@Watchpipe)                              ║" -ForegroundColor White
    Write-Host "  ║  Gateway:  $($Script:BaseUrl.PadRight(52))║" -ForegroundColor White
    Write-Host "  ║  Admin UI: $("$Script:BaseUrl/admin".PadRight(52))║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""

    # ── Integration Status (live check) ──────────────────────────────────────
    Write-Host "  INTEGRATION STATUS" -ForegroundColor Cyan
    Write-Host "  " + ("─" * 66) -ForegroundColor DarkGray

    $integrations = @(
        @{ Name="Telegram Bot";   Endpoint="/api/telegram/status";    Key="enabled"; Icon="📱" },
        @{ Name="WhatsApp";       Endpoint="/api/whatsapp/status";     Key="enabled"; Icon="💬" },
        @{ Name="NOWPayments";    Endpoint="/api/nowpayments/status";  Key="enabled"; Icon="🪙" },
        @{ Name="Sumsub KYC";     Endpoint="/api/kyc/config";          Key="enabled"; Icon="🛡️" },
        @{ Name="Stripe";         Endpoint="/api/stripe/status";       Key="enabled"; Icon="💜" }
    )

    foreach ($intg in $integrations) {
        $status = Invoke-API $intg.Endpoint
        $enabled = if ($status) { $status.($intg.Key) } else { $false }
        $dot   = if ($enabled) { "●" } else { "○" }
        $label = if ($enabled) { "ACTIVE  " } else { "NOT SET " }
        $color = if ($enabled) { "Green"  } else { "DarkGray" }
        Write-Host ("  {0}  {1,-14}  " -f $intg.Icon, $intg.Name) -NoNewline
        Write-Host "$dot $label" -ForegroundColor $color -NoNewline

        # Show extra detail per integration
        if ($enabled -and $status) {
            switch ($intg.Name) {
                "Telegram Bot"  { Write-Host "  Chat: $($status.chat_id)" -ForegroundColor DarkGray }
                "WhatsApp"      { Write-Host "  To: $($status.to_number)" -ForegroundColor DarkGray }
                "NOWPayments"   { Write-Host "  Env: $($status.env)" -ForegroundColor DarkGray }
                "Sumsub KYC"    { Write-Host "  Level: $($status.level_name)" -ForegroundColor DarkGray }
                default         { Write-Host "" }
            }
        } else {
            Write-Host ""
        }
    }

    Write-Host ""

    # ── Payment Providers ──────────────────────────────────────────────────────
    Write-Host "  PAYMENT PROVIDERS" -ForegroundColor Cyan
    Write-Host "  " + ("─" * 66) -ForegroundColor DarkGray
    Write-Host "  💳  Transak      ●  Fiat→Crypto via card/bank   KYC: None < `$200" -ForegroundColor White
    Write-Host "  🌙  MoonPay      ●  Fiat→Crypto via card/bank   KYC: Email < `$150" -ForegroundColor White
    Write-Host "  🪙  NOWPayments  ●  Wallet-to-Wallet (300+ coins) KYC: None ever" -ForegroundColor White
    Write-Host "  💜  Stripe       ●  Card payments via Checkout   KYC: Stripe-managed" -ForegroundColor White
    Write-Host ""

    # ── Live Stats ─────────────────────────────────────────────────────────────
    Write-Host "  LIVE STATS" -ForegroundColor Cyan
    Write-Host "  " + ("─" * 66) -ForegroundColor DarkGray
    $stats = Invoke-API "/api/stats"
    if ($stats) {
        $bar_filled = [int]($stats.conversion_rate / 5)
        $bar = ("█" * $bar_filled) + ("░" * (20 - $bar_filled))
        Write-Host ("  Total Payments : {0,-8}  Completed : {1,-8}  Failed : {2}" -f `
            $stats.total_payments, $stats.completed, $stats.failed) -ForegroundColor White
        Write-Host ("  Volume (USD)   : `${0,-8}  Pending   : {1,-8}  Links  : {2}" -f `
            $stats.total_volume_usd, $stats.pending, $stats.active_links) -ForegroundColor White
        Write-Host "  Conversion     : [$bar] $($stats.conversion_rate)%" -ForegroundColor $(if($stats.conversion_rate -gt 60){"Green"}elseif($stats.conversion_rate -gt 30){"Yellow"}else{"Red"})
    } else {
        Write-Host "  Could not fetch stats (gateway may be offline)" -ForegroundColor DarkGray
    }
    Write-Host ""

    # ── Feature Map ───────────────────────────────────────────────────────────
    Write-Host "  FEATURES" -ForegroundColor Cyan
    Write-Host "  " + ("─" * 66) -ForegroundColor DarkGray
    $features = @(
        "✅  Payment Links     — reusable or one-time, shareable URLs",
        "✅  Multi-Provider    — Transak, MoonPay, NOWPayments",
        "✅  Concurrent Pay    — async engine handles many payments simultaneously",
        "✅  Telegram Alerts   — new payment, completed, failed, summary",
        "✅  WhatsApp Alerts   — parallel notifications via Meta Cloud API",
        "✅  KYC Tiering       — no KYC → email only → Sumsub full KYC",
        "✅  Merchant System   — multi-merchant API keys + per-merchant webhooks",
        "✅  Webhook Engine    — HMAC-verified from all 4 providers",
        "✅  Admin Web UI      — live dashboard at /admin",
        "✅  PowerShell UI     — this console (admin.ps1)",
        "✅  CSV Export        — full payment history download"
    )
    foreach ($f in $features) {
        Write-Host "  $f" -ForegroundColor White
    }
    Write-Host ""

    # ── Quick Actions ─────────────────────────────────────────────────────────
    Write-Host "  QUICK ACTIONS" -ForegroundColor Cyan
    Write-Host "  " + ("─" * 66) -ForegroundColor DarkGray
    Write-Host "  [1] Test Telegram Notification" -ForegroundColor Yellow
    Write-Host "  [2] Test WhatsApp Notification" -ForegroundColor Yellow
    Write-Host "  [3] Send Stats to Telegram + WhatsApp" -ForegroundColor Yellow
    Write-Host "  [4] Create a Payment Link (quick)" -ForegroundColor Yellow
    Write-Host "  [5] Open Admin Web UI in browser" -ForegroundColor Yellow
    Write-Host "  [B] Back to Main Menu" -ForegroundColor DarkGray
    Write-Host ""

    $action = Read-Host "  Quick action"
    switch ($action.Trim().ToUpper()) {
        "1" {
            Write-Host "  Sending Telegram test..." -ForegroundColor DarkGray
            $r = Invoke-API "/api/telegram/test" "POST"
            if ($r) { Write-Host "  ✅ Telegram test sent! Check @Openclawbeastpay_bot" -ForegroundColor Green }
            Pause-Prompt
        }
        "2" {
            Write-Host "  Sending WhatsApp test..." -ForegroundColor DarkGray
            $r = Invoke-API "/api/whatsapp/test" "POST"
            if ($r) { Write-Host "  ✅ WhatsApp test sent!" -ForegroundColor Green }
            Pause-Prompt
        }
        "3" {
            Write-Host "  Pushing stats to all channels..." -ForegroundColor DarkGray
            $t = Invoke-API "/api/telegram/summary" "POST"
            $w = Invoke-API "/api/whatsapp/summary" "POST"
            if ($t) { Write-Host "  ✅ Telegram summary sent" -ForegroundColor Green }
            if ($w) { Write-Host "  ✅ WhatsApp summary sent" -ForegroundColor Green }
            Pause-Prompt
        }
        "4" { Create-Link }
        "5" {
            Start-Process "$Script:BaseUrl/admin"
            Write-Host "  Opened in browser." -ForegroundColor Green
            Pause-Prompt
        }
        default { }
    }
}

# ─── WhatsApp Functions ──────────────────────────────────────────────────────
function Show-WhatsAppMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkGreen
        Write-Host "  │  💬 WHATSAPP INTEGRATION            │" -ForegroundColor Green
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkGreen
        Write-Host "  │  [1] Show Status                    │" -ForegroundColor White
        Write-Host "  │  [2] Send Test Message              │" -ForegroundColor White
        Write-Host "  │  [3] Push Stats Summary             │" -ForegroundColor White
        Write-Host "  │  [4] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [B] Back                           │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkGreen
        $choice = Read-Host "  Choice"
        switch ($choice.Trim().ToUpper()) {
            "1" {
                $s = Invoke-API "/api/whatsapp/status"
                if ($s) {
                    $col = if ($s.enabled) { "Green" } else { "Red" }
                    Write-Host ""
                    Write-Host "  ╔════════════ WHATSAPP STATUS ════════════╗" -ForegroundColor Green
                    Write-Host ("  ║  Enabled:    {0,-30}║" -f $(if($s.enabled){"✅ YES"}else{"❌ NO"})) -ForegroundColor $col
                    Write-Host ("  ║  Phone ID:   {0,-30}║" -f $s.phone_id) -ForegroundColor White
                    Write-Host ("  ║  To:         {0,-30}║" -f $s.to_number) -ForegroundColor White
                    Write-Host "  ╠══════════════════════════════════════════╣" -ForegroundColor Green
                    Write-Host ("  ║  New Payment: {0,-29}║" -f $(if($s.notify_new_payment){"ON"}else{"off"})) -ForegroundColor White
                    Write-Host ("  ║  Completed:   {0,-29}║" -f $(if($s.notify_completed){"ON"}else{"off"})) -ForegroundColor White
                    Write-Host ("  ║  Failed:      {0,-29}║" -f $(if($s.notify_failed){"ON"}else{"off"})) -ForegroundColor White
                    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Green
                }
                Pause-Prompt
            }
            "2" {
                $r = Invoke-API "/api/whatsapp/test" "POST"
                if ($r) { Write-Host "  ✅ Test message sent to WhatsApp!" -ForegroundColor Green }
                Pause-Prompt
            }
            "3" {
                $r = Invoke-API "/api/whatsapp/summary" "POST"
                if ($r) { Write-Host "  ✅ Stats summary sent to WhatsApp!" -ForegroundColor Green }
                Pause-Prompt
            }
            "4" {
                Write-Host ""
                Write-Host "  ─── WhatsApp Cloud API Setup ───────────────" -ForegroundColor Green
                Write-Host "  1. developers.facebook.com → My Apps → Create App → Business"
                Write-Host "  2. Add WhatsApp product → API Setup"
                Write-Host "  3. Copy Phone Number ID + generate Permanent Access Token"
                Write-Host "  4. Add recipient number (verified in test or live mode)"
                Write-Host ""
                Write-Host '  export WHATSAPP_TOKEN="EAAxxxxxxxx"' -ForegroundColor Yellow
                Write-Host '  export WHATSAPP_PHONE_ID="123456789012345"' -ForegroundColor Yellow
                Write-Host '  export WHATSAPP_TO="911234567890"' -ForegroundColor Yellow
                Write-Host ""
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}

# ─── NOWPayments Functions ────────────────────────────────────────────────────
function Show-NowPaymentsMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkCyan
        Write-Host "  │  🪙 NOWPAYMENTS INTEGRATION         │" -ForegroundColor Cyan
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkCyan
        Write-Host "  │  [1] Show Status                    │" -ForegroundColor White
        Write-Host "  │  [2] List Supported Currencies      │" -ForegroundColor White
        Write-Host "  │  [3] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [B] Back                           │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkCyan
        $choice = Read-Host "  Choice"
        switch ($choice.Trim().ToUpper()) {
            "1" {
                $s = Invoke-API "/api/nowpayments/status"
                if ($s) {
                    $col = if ($s.enabled) { "Green" } else { "Red" }
                    Write-Host ""
                    Write-Host "  ╔═══════════ NOWPAYMENTS STATUS ═══════════╗" -ForegroundColor Cyan
                    Write-Host ("  ║  Enabled:     {0,-28}║" -f $(if($s.enabled){"✅ YES"}else{"❌ NO"})) -ForegroundColor $col
                    Write-Host ("  ║  API Key:     {0,-28}║" -f $s.api_key) -ForegroundColor White
                    Write-Host ("  ║  Environment: {0,-28}║" -f $s.env.ToUpper()) -ForegroundColor $(if($s.env -eq 'production'){"Green"}else{"Yellow"})
                    Write-Host ("  ║  KYC:         {0,-28}║" -f "None required") -ForegroundColor Green
                    Write-Host ("  ║  Currencies:  {0,-28}║" -f "300+") -ForegroundColor White
                    Write-Host "  ╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
                }
                Pause-Prompt
            }
            "2" {
                Write-Host "`n  Fetching supported currencies..." -ForegroundColor DarkGray
                $r = Invoke-API "/api/nowpayments/currencies"
                if ($r) {
                    Write-Host "  Total supported: $($r.count)" -ForegroundColor Green
                    Write-Host "  First 50: $($r.currencies -join ', ')" -ForegroundColor White
                }
                Pause-Prompt
            }
            "3" {
                Write-Host ""
                Write-Host "  ─── NOWPayments Setup ──────────────────────" -ForegroundColor Cyan
                Write-Host "  1. Sign up at nowpayments.io"
                Write-Host "  2. Dashboard → API Keys → Create key"
                Write-Host "  3. Settings → IPN Secret → set secret string"
                Write-Host "  4. Add webhook: {BASE_URL}/webhooks/nowpayments"
                Write-Host ""
                Write-Host '  export NOWPAYMENTS_API_KEY="your_api_key"' -ForegroundColor Yellow
                Write-Host '  export NOWPAYMENTS_IPN_SECRET="your_ipn_secret"' -ForegroundColor Yellow
                Write-Host '  export NOWPAYMENTS_ENV="production"' -ForegroundColor Yellow
                Write-Host ""
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}

# ─── KYC / Sumsub Functions ───────────────────────────────────────────────────
function Show-KYCMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor DarkYellow
        Write-Host "  │  🛡️  KYC / SUMSUB INTEGRATION       │" -ForegroundColor Yellow
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor DarkYellow
        Write-Host "  │  [1] Show KYC Config                │" -ForegroundColor White
        Write-Host "  │  [2] List KYC Records               │" -ForegroundColor White
        Write-Host "  │  [3] Check Applicant Status         │" -ForegroundColor White
        Write-Host "  │  [4] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [B] Back                           │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor DarkYellow
        $choice = Read-Host "  Choice"
        switch ($choice.Trim().ToUpper()) {
            "1" {
                $s = Invoke-API "/api/kyc/config"
                if ($s) {
                    $col = if ($s.enabled) { "Green" } else { "Red" }
                    Write-Host ""
                    Write-Host "  ╔══════════════ KYC STATUS ════════════════╗" -ForegroundColor Yellow
                    Write-Host ("  ║  Enabled:     {0,-28}║" -f $(if($s.enabled){"✅ YES"}else{"❌ NO"})) -ForegroundColor $col
                    Write-Host ("  ║  App Token:   {0,-28}║" -f $s.app_token) -ForegroundColor White
                    Write-Host ("  ║  Level Name:  {0,-28}║" -f $s.level_name) -ForegroundColor White
                    Write-Host ("  ║  KYC Trigger: {0,-28}║" -f $s.kyc_trigger) -ForegroundColor Yellow
                    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Yellow
                }
                Pause-Prompt
            }
            "2" {
                Write-Host "`n  Loading KYC records..." -ForegroundColor DarkGray
                $records = Invoke-API "/api/kyc/records"
                if ($records -and $records.Count -gt 0) {
                    Write-Host ("  {0,-10} {1,-26} {2,-14} {3,-12}" -f "ID","EMAIL","STATUS","DATE") -ForegroundColor Cyan
                    Write-Host "  " + ("─" * 65) -ForegroundColor DarkGray
                    foreach ($r in $records) {
                        $sc = switch ($r.kyc_status) { "approved"{"Green"} "rejected"{"Red"} default{"Yellow"} }
                        Write-Host ("  {0,-10} {1,-26} " -f $r.id.Substring(0,8), $r.customer_email) -NoNewline
                        Write-Host ("{0,-14}" -f $r.kyc_status.ToUpper()) -ForegroundColor $sc -NoNewline
                        Write-Host $r.created_at.Substring(0,10)
                    }
                } else {
                    Write-Host "  No KYC records found." -ForegroundColor Yellow
                }
                Pause-Prompt
            }
            "3" {
                $appId = Read-Host "  Enter Applicant ID"
                $r = Invoke-API "/api/kyc/status/$($appId.Trim())"
                if ($r) {
                    Write-Host ""
                    Write-Host "  KYC Status:    $($r.kyc_status)" -ForegroundColor $(if($r.kyc_status -eq 'approved'){"Green"}elseif($r.kyc_status -eq 'rejected'){"Red"}else{"Yellow"})
                    Write-Host "  Review Status: $($r.review_status)"
                    Write-Host "  Answer:        $($r.review_answer)"
                    if ($r.reject_labels) { Write-Host "  Reject Labels: $($r.reject_labels -join ', ')" -ForegroundColor Red }
                }
                Pause-Prompt
            }
            "4" {
                Write-Host ""
                Write-Host "  ─── Sumsub KYC Setup ───────────────────────" -ForegroundColor Yellow
                Write-Host "  1. Sign up at dashboard.sumsub.com"
                Write-Host "  2. Developers → App Tokens → Create token"
                Write-Host "  3. Copy App Token and Secret Key"
                Write-Host "  4. Create a verification flow in Sumsub dashboard"
                Write-Host "  5. Add webhook URL: {BASE_URL}/webhooks/sumsub"
                Write-Host ""
                Write-Host '  export SUMSUB_APP_TOKEN="sbx:xxxx"' -ForegroundColor Yellow
                Write-Host '  export SUMSUB_SECRET_KEY="your_secret"' -ForegroundColor Yellow
                Write-Host '  export SUMSUB_LEVEL_NAME="basic-kyc-level"' -ForegroundColor Yellow
                Write-Host '  export KYC_SUMSUB_LIMIT=500' -ForegroundColor Yellow
                Write-Host ""
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}

function Show-LockboxMenu {
    do {
        Clear-Host
        Write-Host ""
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor Cyan
        Write-Host "  │  🔐 LOCKBOX AI PARSER               │" -ForegroundColor Cyan
        Write-Host "  │  Claude-powered card data extractor │" -ForegroundColor DarkGray
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor Cyan
        Write-Host "  │  [1] Show Lockbox Status            │" -ForegroundColor White
        Write-Host "  │  [2] Parse Payment Text (manual)    │" -ForegroundColor White
        Write-Host "  │  [3] View Recent Transactions       │" -ForegroundColor White
        Write-Host "  │  [4] View Transaction Detail        │" -ForegroundColor White
        Write-Host "  │  [5] Setup Telegram Webhook         │" -ForegroundColor White
        Write-Host "  │  [6] Remove Telegram Webhook        │" -ForegroundColor White
        Write-Host "  │  [7] Test Claude AI Connection      │" -ForegroundColor White
        Write-Host "  │  [8] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [B] Back to Main Menu              │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor Cyan
        Write-Host ""

        $choice = Read-Host "  Enter choice"
        switch ($choice.Trim().ToUpper()) {
            "1" {
                Write-Host "`n  Fetching Lockbox status…" -ForegroundColor DarkGray
                $status = Invoke-API "/api/lockbox/status"
                if ($status) {
                    $aiColor = if ($status.claude_online) { "Green" } else { "Red" }
                    $aiText  = if ($status.claude_online) { "ONLINE" } else { "OFFLINE" }
                    $enText  = if ($status.enabled) { "ENABLED" } else { "DISABLED (set ANTHROPIC_API_KEY)" }
                    Write-Host ""
                    Write-Host "  Lockbox Enabled : $enText" -ForegroundColor $(if($status.enabled){"Green"}else{"Red"})
                    Write-Host "  Claude AI       : $aiText" -ForegroundColor $aiColor
                    Write-Host ""
                    Write-Host "  ── Statistics ──────────────────────────"
                    Write-Host "  Total Parsed    : $($status.stats.total)"
                    Write-Host "  Valid Cards     : $($status.stats.valid)" -ForegroundColor Green
                    Write-Host "  Invalid / Flags : $($status.stats.invalid)" -ForegroundColor Red
                }
                Pause-Prompt
            }
            "2" {
                Write-Host ""
                Write-Host "  ─── Parse Payment Text ─────────────────────" -ForegroundColor Cyan
                Write-Host "  Paste raw payment text below (press Enter twice when done):"
                Write-Host ""
                $lines = @()
                do {
                    $line = Read-Host "  "
                    if ($line -ne "") { $lines += $line }
                } while ($line -ne "")
                $rawText = $lines -join "`n"
                if ($rawText.Trim() -eq "") {
                    Write-Host "  No input provided." -ForegroundColor Red
                    Pause-Prompt
                    continue
                }
                Write-Host ""
                Write-Host "  Sending to Claude AI…" -ForegroundColor DarkGray
                $body = @{ rawInput = $rawText; source = "manual" } | ConvertTo-Json
                try {
                    $result = Invoke-RestMethod -Uri "$BASE_URL/api/lockbox/parse" -Method Post `
                        -Body $body -ContentType "application/json"
                    if ($result.success) {
                        $p = $result.parsed
                        $v = $result.validation.overall
                        $statusColor = if ($v.isValid) { "Green" } else { "Red" }
                        $statusText  = if ($v.isValid) { "VALID" } else { "INVALID" }
                        Write-Host ""
                        Write-Host "  ── Parse Result ─────────────────────────" -ForegroundColor $(if($v.isValid){"Green"}else{"Red"})
                        Write-Host "  Status    : $statusText" -ForegroundColor $statusColor
                        Write-Host "  Card      : $($p.cardNumber)"
                        Write-Host "  Expiry    : $($p.expiryDate)"
                        Write-Host "  CVV       : $($p.cvv)"
                        Write-Host "  Name      : $($p.cardholderName)"
                        $addr = $p.billingAddress
                        Write-Host "  Address   : $($addr.street), $($addr.city), $($addr.state) $($addr.zipCode), $($addr.country)"
                        Write-Host ""
                        Write-Host "  ── Confidence ───────────────────────────"
                        $conf = $p.confidence
                        $confFields = @("cardNumber","expiryDate","cvv","cardholderName","billingAddress")
                        foreach ($f in $confFields) {
                            $val = [math]::Round($conf.$f * 100)
                            $bar = ("█" * [math]::Round($val/10)) + ("░" * (10 - [math]::Round($val/10)))
                            Write-Host "  $($f.PadRight(16)): [$bar] $val%"
                        }
                        if ($v.errors -and $v.errors.Count -gt 0) {
                            Write-Host ""
                            Write-Host "  ── Validation Errors ────────────────────" -ForegroundColor Red
                            $v.errors | ForEach-Object { Write-Host "  ⚠ $_" -ForegroundColor Yellow }
                        }
                        if ($p.anomalies -and $p.anomalies.Count -gt 0) {
                            Write-Host ""
                            Write-Host "  ── Anomalies ────────────────────────────" -ForegroundColor Yellow
                            $p.anomalies | ForEach-Object { Write-Host "  🔸 $_" -ForegroundColor Yellow }
                        }
                        Write-Host ""
                        Write-Host "  Transaction ID : #$($result.transaction.id)" -ForegroundColor Cyan
                    } else {
                        Write-Host "  Error: $($result.error)" -ForegroundColor Red
                    }
                } catch {
                    Write-Host "  Request failed: $_" -ForegroundColor Red
                }
                Pause-Prompt
            }
            "3" {
                Write-Host "`n  Recent Lockbox Transactions" -ForegroundColor Cyan
                $txs = Invoke-API "/api/lockbox/transactions?limit=15"
                if ($txs -and $txs.transactions) {
                    Write-Host ""
                    Write-Host "  ID     Card               Name             Status    Source     Time" -ForegroundColor DarkGray
                    Write-Host "  ─────────────────────────────────────────────────────────────────────"
                    $txs.transactions | ForEach-Object {
                        $sc = if($_.validation_status -eq "valid"){"Green"}else{"Red"}
                        $id   = ("#"+$_.id).PadRight(7)
                        $card = ($_.masked_card_number).PadRight(20)
                        $name = ($_.cardholder_name -replace ".{15}$","...").PadRight(17)
                        $st   = ($_.validation_status).PadRight(10)
                        $src  = ($_.source).PadRight(11)
                        $time = ($_.created_at).Substring(0,16)
                        Write-Host "  $id$card$name" -NoNewline
                        Write-Host $st -ForegroundColor $sc -NoNewline
                        Write-Host "$src$time"
                    }
                    Write-Host "`n  Total: $($txs.total)" -ForegroundColor DarkGray
                } else {
                    Write-Host "  No transactions yet." -ForegroundColor DarkGray
                }
                Pause-Prompt
            }
            "4" {
                $txId = Read-Host "  Enter Transaction ID"
                if ($txId -match "^\d+$") {
                    $data = Invoke-API "/api/lockbox/transactions/$txId"
                    if ($data -and $data.transaction) {
                        $t = $data.transaction
                        $sc = if($t.validation_status -eq "valid"){"Green"}else{"Red"}
                        Write-Host ""
                        Write-Host "  Transaction #$($t.id)" -ForegroundColor Cyan
                        Write-Host "  Status      : $($t.validation_status)" -ForegroundColor $sc
                        Write-Host "  Card        : $($t.masked_card_number)"
                        Write-Host "  Expiry      : $($t.expiry_date)"
                        Write-Host "  Name        : $($t.cardholder_name)"
                        Write-Host "  Address     : $($t.billing_street), $($t.billing_city), $($t.billing_state) $($t.billing_zip), $($t.billing_country)"
                        Write-Host "  Source      : $($t.source)"
                        Write-Host "  Created     : $($t.created_at)"
                        Write-Host "  AI Reasoning: $($t.ai_reasoning)"
                    } else {
                        Write-Host "  Transaction not found." -ForegroundColor Red
                    }
                } else {
                    Write-Host "  Invalid ID." -ForegroundColor Red
                }
                Pause-Prompt
            }
            "5" {
                Write-Host "`n  Setting up Telegram webhook…" -ForegroundColor DarkGray
                try {
                    $r = Invoke-RestMethod -Uri "$BASE_URL/api/lockbox/setup-webhook" -Method Post `
                        -Headers @{"X-Api-Key"=$ADMIN_KEY} -ContentType "application/json"
                    Write-Host "  Webhook set: $($r.webhook_url)" -ForegroundColor Green
                    Write-Host "  Telegram says: $($r.telegram_response.description)"
                } catch { Write-Host "  Error: $_" -ForegroundColor Red }
                Pause-Prompt
            }
            "6" {
                Write-Host "`n  Removing Telegram webhook…" -ForegroundColor DarkGray
                try {
                    $r = Invoke-RestMethod -Uri "$BASE_URL/api/lockbox/setup-webhook" -Method Delete `
                        -Headers @{"X-Api-Key"=$ADMIN_KEY} -ContentType "application/json"
                    Write-Host "  Done: $($r.description)" -ForegroundColor Green
                } catch { Write-Host "  Error: $_" -ForegroundColor Red }
                Pause-Prompt
            }
            "7" {
                Write-Host "`n  Testing Claude AI connection…" -ForegroundColor DarkGray
                try {
                    $r = Invoke-RestMethod -Uri "$BASE_URL/api/lockbox/test" -Method Post `
                        -Headers @{"X-Api-Key"=$ADMIN_KEY} -ContentType "application/json"
                    if ($r.connected) {
                        Write-Host "  ✅ Claude API is online and responding." -ForegroundColor Green
                    } else {
                        Write-Host "  ❌ Claude API not reachable. Check ANTHROPIC_API_KEY." -ForegroundColor Red
                    }
                } catch { Write-Host "  Error: $_" -ForegroundColor Red }
                Pause-Prompt
            }
            "8" {
                Write-Host ""
                Write-Host "  ─── Lockbox Setup Guide ─────────────────────" -ForegroundColor Cyan
                Write-Host "  1. Get Anthropic API key at console.anthropic.com"
                Write-Host "  2. Add to .env:"
                Write-Host '     export ANTHROPIC_API_KEY="sk-ant-..."' -ForegroundColor Yellow
                Write-Host "  3. Restart gateway:"
                Write-Host "     source .env && python3 server.py" -ForegroundColor Yellow
                Write-Host "  4. Set Telegram webhook so bot inputs flow here:"
                Write-Host "     Lockbox menu → [5] Setup Webhook" -ForegroundColor Yellow
                Write-Host "  5. Test: send any card text to @Openclawbeastpay_bot"
                Write-Host ""
                Write-Host "  ─── Bot Commands ────────────────────────────" -ForegroundColor Cyan
                Write-Host "  /parse <text>  — force parse"
                Write-Host "  /transactions  — last 10 records"
                Write-Host "  /status        — AI + DB status"
                Write-Host "  /help          — command list"
                Write-Host ""
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}

# ─── Stripe Functions ────────────────────────────────────────────────────────
function Show-StripeMenu {
    do {
        Write-Banner
        Write-Host "  ┌─────────────────────────────────────┐" -ForegroundColor Magenta
        Write-Host "  │  💜 STRIPE INTEGRATION              │" -ForegroundColor Magenta
        Write-Host "  ├─────────────────────────────────────┤" -ForegroundColor Magenta
        Write-Host "  │  [1] Show Status                    │" -ForegroundColor White
        Write-Host "  │  [2] Test Connection (Balance)      │" -ForegroundColor White
        Write-Host "  │  [3] Setup Guide                    │" -ForegroundColor White
        Write-Host "  │  [B] Back                           │" -ForegroundColor Yellow
        Write-Host "  └─────────────────────────────────────┘" -ForegroundColor Magenta
        $choice = Read-Host "  Choice"
        switch ($choice.Trim().ToUpper()) {
            "1" {
                $s = Invoke-API "/api/stripe/status"
                if ($s) {
                    $col = if ($s.enabled) { "Green" } else { "Red" }
                    $modeCol = if ($s.mode -eq "live") { "Green" } else { "Yellow" }
                    Write-Host ""
                    Write-Host "  ╔══════════════ STRIPE STATUS ═════════════╗" -ForegroundColor Magenta
                    Write-Host ("  ║  Enabled:     {0,-28}║" -f $(if($s.enabled){"✅ YES"}else{"❌ NO"})) -ForegroundColor $col
                    Write-Host ("  ║  Mode:        {0,-28}║" -f $s.mode.ToUpper()) -ForegroundColor $modeCol
                    Write-Host ("  ║  Secret Key:  {0,-28}║" -f $s.secret_key) -ForegroundColor White
                    Write-Host ("  ║  Webhook:     {0,-28}║" -f $s.webhook_secret) -ForegroundColor White
                    Write-Host ("  ║  Env:         {0,-28}║" -f $s.env.ToUpper()) -ForegroundColor $modeCol
                    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Magenta
                }
                Pause-Prompt
            }
            "2" {
                Write-Host "`n  Testing Stripe connection…" -ForegroundColor DarkGray
                $r = Invoke-API "/api/stripe/test" "POST"
                if ($r -and $r.connected) {
                    Write-Host "  ✅ Stripe connected!" -ForegroundColor Green
                    Write-Host "  Balance : $($r.balance)" -ForegroundColor White
                    Write-Host "  Mode    : $($r.mode.ToUpper())" -ForegroundColor $(if($r.mode -eq 'live'){"Green"}else{"Yellow"})
                } else {
                    Write-Host "  ❌ Connection failed. Check STRIPE_SECRET_KEY." -ForegroundColor Red
                }
                Pause-Prompt
            }
            "3" {
                Write-Host ""
                Write-Host "  ─── Stripe Setup ───────────────────────────" -ForegroundColor Magenta
                Write-Host "  1. Sign up at dashboard.stripe.com"
                Write-Host "  2. Developers → API Keys → copy Secret key"
                Write-Host "  3. Developers → Webhooks → Add endpoint:"
                Write-Host "       {BASE_URL}/webhooks/stripe" -ForegroundColor Cyan
                Write-Host "  4. Select events:"
                Write-Host "       checkout.session.completed" -ForegroundColor DarkGray
                Write-Host "       checkout.session.expired" -ForegroundColor DarkGray
                Write-Host "       payment_intent.payment_failed" -ForegroundColor DarkGray
                Write-Host "       charge.refunded" -ForegroundColor DarkGray
                Write-Host "  5. Copy Signing secret (whsec_...)"
                Write-Host ""
                Write-Host '  export STRIPE_SECRET_KEY="sk_test_..."' -ForegroundColor Yellow
                Write-Host '  export STRIPE_PUBLISHABLE_KEY="pk_test_..."' -ForegroundColor Yellow
                Write-Host '  export STRIPE_WEBHOOK_SECRET="whsec_..."' -ForegroundColor Yellow
                Write-Host '  export STRIPE_ENV="test"  # → "live" for production' -ForegroundColor Yellow
                Write-Host ""
                Write-Host "  Use provider 'stripe' when calling POST /api/payments/initiate" -ForegroundColor Cyan
                Write-Host ""
                Pause-Prompt
            }
            "B" { return }
        }
    } while ($true)
}

# ─── Main Loop ────────────────────────────────────────────────────────────────
do {
    Write-Banner
    Write-Menu
    $choice = Read-Host "  Enter choice"
    switch ($choice.Trim().ToUpper()) {
        "1" { Show-Stats        }
        "2" { Show-Links        }
        "3" { Create-Link       }
        "4" { Show-Payments     }
        "5" { Check-Payment     }
        "6" { Filter-Payments   }
        "7" { Add-Merchant      }
        "8" { Export-Payments   }
        "0" { Show-BeastPayBot    }
        "9" { Health-Check         }
        "T" { Show-TelegramMenu    }
        "W" { Show-WhatsAppMenu   }
        "N" { Show-NowPaymentsMenu }
        "K" { Show-KYCMenu         }
        "S" { Show-StripeMenu      }
        "L" { Show-LockboxMenu     }
        "Q" { Write-Host "`n  Goodbye.`n" -ForegroundColor Yellow; exit 0 }
        default {
            Write-Host "  Invalid choice. Press Enter to try again…" -ForegroundColor Red
            [void][System.Console]::ReadLine()
        }
    }
} while ($true)
