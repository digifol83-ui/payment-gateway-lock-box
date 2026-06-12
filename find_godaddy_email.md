# 🔍 FIND YOUR GODADDY USERNAME — 30 SECONDS

## Method 1: Search Gmail (FASTEST)

Open https://mail.google.com — log in to ANY of your accounts.

In the search bar, type EXACTLY:
```
from:godaddy.com
```

Press Enter.

You'll see GoDaddy emails. Look at any one.

**The email address it was sent TO** is your GoDaddy username.

---

## Method 2: GoDaddy Recovery (if Gmail empty)

1. Go to: https://sso.godaddy.com/account/forgotusername
2. Enter the domain: `sichermayorfx.com`
3. GoDaddy emails the username to whoever owns it
4. Check ALL your email inboxes for the GoDaddy email

---

## Method 3: Try Common Logins

The login screen accepts email OR customer number. Try these:

```
digifol83@gmail.com
ullaakcrypto@gmail.com
sichermayorfx@gmail.com
admin@sichermayorfx.com
info@sichermayorfx.com
```

For password — try whatever you commonly use, then "Forgot password" if none work.

---

## Method 4: Check Browser Saved Passwords

If you've ever logged into GoDaddy from this computer:

**Chrome:** chrome://settings/passwords → search "godaddy"
**Firefox:** about:logins → search "godaddy"
**Edge:** edge://settings/passwords → search "godaddy"

The username will be there.

---

## Method 5: Bank Statements

Search your bank statement for "GoDaddy" charges. The associated email is often the one used for the account.

---

## What I'll do once you have access

The moment you can log in, you have **2 options:**

### A) Manual (faster — 90 seconds)
Go to: https://dcc.godaddy.com/manage/sichermayorfx.com/dns

Delete current MX (the Outlook one).
Add these 2 MX records:

| Type | Name | Value | Priority | TTL |
|------|------|-------|----------|-----|
| MX | @ | mx1.improvmx.com | 10 | 1 hour |
| MX | @ | mx2.improvmx.com | 20 | 1 hour |

Save.

### B) API (fully automated — 30 seconds)
1. Generate API key at: https://developer.godaddy.com/keys
2. Paste here in this format:
   ```
   GODADDY_KEY: <key>
   GODADDY_SECRET: <secret>
   ```
3. I run automation, you do nothing.

Pick whichever is easier once you have the login.
