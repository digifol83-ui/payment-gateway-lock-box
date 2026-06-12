"""Outbound mailer with attachments + a tiny CLI for gateway-application packages.

Reads SMTP settings from config.settings (same as verification/otp_mailer.py).
Application "spec" is a JSON file with: to, cc, subject, body, attachments[].
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

from config import settings


class MailerNotConfigured(RuntimeError):
    pass


def _require_smtp() -> tuple[str, int, str, str, str]:
    host = settings.SMTP_HOST
    port = int(settings.SMTP_PORT or 587)
    user = settings.SMTP_USERNAME
    pwd = settings.SMTP_PASSWORD
    from_addr = settings.SMTP_FROM or user
    if not (host and user and pwd):
        raise MailerNotConfigured(
            "SMTP not configured. Run: python3 mailer.py setup"
        )
    return host, port, user, pwd, from_addr


def send_email(
    to: list[str] | str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    attachments: list[str] | None = None,
) -> dict:
    host, port, user, pwd, from_addr = _require_smtp()
    to_list = [to] if isinstance(to, str) else list(to)
    cc_list = list(cc or [])

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    msg.set_content(body)

    for path in attachments or []:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"attachment not found: {p}")
        ctype, encoding = mimetypes.guess_type(p.name)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(
            p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name
        )

    ctx = ssl.create_default_context()
    recipients = to_list + cc_list
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg, to_addrs=recipients)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(user, pwd)
            s.send_message(msg, to_addrs=recipients)

    return {"sent": True, "from": from_addr, "to": recipients, "subject": subject}


def send_spec(spec_path: str) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    return send_email(
        to=spec["to"],
        cc=spec.get("cc"),
        subject=spec["subject"],
        body=spec["body"],
        attachments=spec.get("attachments"),
    )


def _update_env(updates: dict) -> None:
    """Rewrite /home/kali/payment-gateway/.env preserving order and unrelated keys."""
    env_path = Path(__file__).parent / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    keys_seen = set()
    out: list[str] = []
    for ln in lines:
        if "=" in ln and not ln.lstrip().startswith("#"):
            k = ln.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                keys_seen.add(k)
                continue
        out.append(ln)
    for k, v in updates.items():
        if k not in keys_seen:
            out.append(f"{k}={v}")
    env_path.write_text("\n".join(out) + "\n")


def cmd_setup() -> int:
    import getpass

    print("Gmail SMTP setup (App Password)")
    print("Prereqs: 2FA enabled on the Gmail account, then create an app password at")
    print("  https://myaccount.google.com/apppasswords")
    print()
    user = input("Gmail address [digifol83@gmail.com]: ").strip() or "digifol83@gmail.com"
    pw = getpass.getpass("App password (16 chars, no spaces): ").strip().replace(" ", "")
    if len(pw) != 16:
        print(f"warning: expected 16 chars, got {len(pw)}. proceeding anyway.")
    from_addr = input(f"From address [{user}]: ").strip() or user

    _update_env({
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": user,
        "SMTP_PASSWORD": pw,
        "SMTP_FROM": from_addr,
    })
    print(".env updated. Reloading settings and testing...")

    # reload settings module to pick up new env
    import importlib, config
    importlib.reload(config)
    globals()["settings"] = config.settings

    test_to = input(f"Send test email to [{user}]: ").strip() or user
    try:
        result = send_email(
            to=test_to,
            subject="BeastPay mailer test",
            body="This is a test from /home/kali/payment-gateway/mailer.py. If you can read this, SMTP is wired.\n",
        )
        print("OK:", result)
        return 0
    except Exception as e:
        print("FAIL:", e)
        return 1


def cmd_send_spec(path: str) -> int:
    try:
        result = send_spec(path)
        print("OK:", json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print("FAIL:", e)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="mailer")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="Interactive Gmail App Password setup + test send")
    sp = sub.add_parser("send-spec", help="Send an application from a JSON spec file")
    sp.add_argument("spec", help="Path to JSON spec (to, cc, subject, body, attachments)")
    args = ap.parse_args()
    if args.cmd == "setup":
        return cmd_setup()
    if args.cmd == "send-spec":
        return cmd_send_spec(args.spec)
    return 2


if __name__ == "__main__":
    sys.exit(main())
