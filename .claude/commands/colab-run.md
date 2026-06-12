# /colab-run — Drive a Colab notebook fully autonomously

Take a Jupyter notebook (`.ipynb`) from WSL → upload to Colab → switch to T4 GPU →
Run All, no Windows-side clicks needed. Uses CDP through a PowerShell TCP relay.

Usage:
  `/colab-run <path_to_notebook.ipynb>`
  `/colab-run /home/kali/unsloth_beastpay_finetune.ipynb`

If Chrome is already running with the relay (from a previous run), use the lighter:
  `python3 /home/kali/openclaw_skills/colab_set_t4_and_run.py`
(no kill+relaunch, just sets T4 and Run All on the open Colab tab)

---

## What this skill does

1. **Verifies Chrome is debug-listening** on the Windows host at port 9222
2. **Attaches Playwright** to that signed-in browser session (no separate sign-in needed)
3. **Opens Colab** in a new tab in the user's signed-in browser
4. **Uploads the notebook** via the File → Upload tab
5. **Switches runtime to T4 GPU** via Runtime menu
6. **Triggers Run All** (`Ctrl+F9`)
7. **Hands off** — the notebook keeps running in the browser; this script exits

The user's main Chrome session is NOT affected — a separate profile (`C:\chrome-cdp-profile`)
is used.

---

## Hard limit honored

`[[openclaw_no_captcha_solver]]` — if Google shows any CAPTCHA / "browser may not be secure"
challenge, the skill stops and prompts the user to clear it manually. It never tries to
bypass.

---

## Pre-flight — none needed after first run

The script `colab_full_auto.py` does all the Windows setup itself:
1. `taskkill /F /IM chrome.exe` — closes all Chrome
2. `Start-Process chrome.exe` — launches Chrome with `--remote-debugging-port=9222`
   using the user's MAIN profile (`C:\Users\shahe\AppData\Local\Google\Chrome\User Data`)
   so the existing Google sign-in carries over
3. Launches `cdp_relay.ps1` — PowerShell TCP relay 0.0.0.0:9223 → 127.0.0.1:9222
   (needed because Chrome 111+ ignores `--remote-debugging-address`; pure WSL→Windows
   localhost is not reachable, the relay is mandatory)

**First-ever run only:** Windows Firewall may pop up "Allow PowerShell network access" —
click Allow once. After that, the path is fully automatic.

---

## Execution

```bash
python3 /home/kali/openclaw_skills/colab_full_auto.py /home/kali/unsloth_beastpay_finetune.ipynb
```

The script:

- Kills any running Chrome on Windows
- Re-launches Chrome with debug port + user's main profile (keeps Google sign-in)
- Starts the PowerShell TCP relay (`cdp_relay.ps1`)
- Probes Windows host IP on port 9223 (the relay's listen port)
- Reuses the existing Colab tab; uploads the notebook; switches to T4; presses Ctrl+F9
- Exits with `OK — handoff complete.` once cells are running

---

## Failure modes (and what to do)

| Symptom | Cause | Fix |
|---|---|---|
| "Cannot reach Chrome's debug port" | Chrome not launched with `--remote-debugging-port=9222` | Run `launch_chrome_debug.bat`. Make sure no other Chrome window is open with the same profile. |
| "Colab is showing a sign-in page" | Cookie didn't persist | Sign in inside the debug-profile Chrome; visit Colab once; re-run. |
| "Upload tab not found" | Colab UI changed | Selectors in `colab_runner.py` need a minor tweak. |
| "T4 may already be selected" | Already on T4 | Not an error; skill proceeds. |
| Cell hangs at "Connecting to GPU" | Google's free GPU pool is exhausted | Wait 15-30 min and re-run. Free tier isn't guaranteed. |

---

## Why this design

- **No password storage** — we never see Google credentials; we attach to an already-signed-in browser
- **No headless mode** — required for Google's security checks; the user sees the browser drive itself, transparent
- **Profile isolation** — `C:\chrome-cdp-profile` doesn't pollute the main Chrome profile
- **Idempotent** — re-running just opens another Colab tab; no destructive state

---

## After Run All starts

The skill exits and the browser keeps running. You can:

- Watch cells execute in the browser
- Close the WSL terminal — the Colab job is independent now
- Come back in ~30 min, the notebook will have finished
- Results land in `/content/` (Colab) or your Drive if the last cell ran

---

## Future extensions (not built yet)

- `/colab-monitor` — poll Colab for cell completion, ping Telegram when done
- `/colab-fetch <gcs-path>` — auto-download outputs to GCS bucket after run
- `/openclaw-task <description>` — natural-language task → browser automation via OpenClaw agent
