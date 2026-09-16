"""
Email sending for the dashboard (alerts and reports).

    send_email(to, subject, body, attachments=None)

    to           one address or a list of addresses
    attachments  optional list of file paths to attach

Uses the SMTP settings in config.py. The password is read from the
EMAIL_PASS environment variable (config.EMAIL_PASS); for Gmail this
must be an App Password, not the normal account password:
    Google Account -> Security -> 2-Step Verification -> App passwords

Set it before launching the app, e.g. in PowerShell:
    $env:EMAIL_USER = "you@gmail.com"
    $env:EMAIL_PASS = "abcd efgh ijkl mnop"
"""

import os
import ssl
import time
import smtplib
import mimetypes
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from config import (
    SENDER_EMAIL, EMAIL_PASS, SMTP_HOST, SMTP_PORT,
    MAX_ATTACHMENT_BYTES, MAX_RETRIES, RETRY_DELAY_SECONDS, FLEET_NAME,
)


class EmailConfigError(RuntimeError):
    """Raised when the email settings are incomplete."""


def _normalise_recipients(to):
    if isinstance(to, str):
        to = [to]
    recipients = [address.strip() for address in to if address and address.strip()]
    if not recipients:
        raise ValueError("No recipient address given.")
    return recipients


def build_message(to, subject, body, attachments=None, high_priority=True):
    """Builds the EmailMessage (separate from sending so it can be tested)."""

    recipients = _normalise_recipients(to)

    message = EmailMessage()
    message["From"] = f"{FLEET_NAME} Oilfield Monitor <{SENDER_EMAIL}>"
    message["To"] = ", ".join(recipients)
    message["Reply-To"] = SENDER_EMAIL
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=SENDER_EMAIL.split("@")[-1])

    if high_priority:
        # Understood by Gmail, Outlook and Apple Mail: shows the
        # red "!" / "High importance" marker.
        message["X-Priority"] = "1 (Highest)"
        message["X-MSMail-Priority"] = "High"
        message["Importance"] = "High"

    message.set_content(body)

    total_bytes = 0
    for path in attachments or []:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Attachment not found: {path}")

        size = os.path.getsize(path)
        total_bytes += size
        if total_bytes > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachments exceed the {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB "
                f"limit (adding {os.path.basename(path)})."
            )

        mime_type, _ = mimetypes.guess_type(path)
        main_type, sub_type = (mime_type or "application/octet-stream").split("/", 1)

        with open(path, "rb") as handle:
            message.add_attachment(
                handle.read(), maintype=main_type, subtype=sub_type,
                filename=os.path.basename(path),
            )

    return message, recipients


def send_email(to, subject, body, attachments=None, high_priority=True):
    """
    Sends the email, retrying transient SMTP/network failures up to
    MAX_RETRIES times. Raises on configuration problems or if every
    attempt fails, so callers can show the reason to the user.
    """

    if not SENDER_EMAIL:
        raise EmailConfigError("SENDER_EMAIL / EMAIL_USER is not set.")
    if not EMAIL_PASS:
        raise EmailConfigError(
            "EMAIL_PASS environment variable is not set. For Gmail, create an "
            "App Password and set EMAIL_PASS before starting the app."
        )

    message, recipients = build_message(to, subject, body, attachments,
                                        high_priority)
    context = ssl.create_default_context()
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SENDER_EMAIL, EMAIL_PASS)
                server.send_message(message, from_addr=SENDER_EMAIL,
                                    to_addrs=recipients)
            return True

        except smtplib.SMTPAuthenticationError as error:
            # Wrong password / app password: retrying will not help.
            raise EmailConfigError(
                "SMTP login was rejected. Check EMAIL_USER and EMAIL_PASS "
                "(Gmail requires an App Password)."
            ) from error

        except (smtplib.SMTPException, OSError) as error:
            last_error = error
            print(f"emailer: attempt {attempt}/{MAX_RETRIES} failed: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Could not send email after {MAX_RETRIES} attempts: {last_error}"
    )


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else SENDER_EMAIL
    print(f"Sending test email to {target} ...")
    send_email(target, "[Oilfield Monitor] Test email",
               "If you can read this, emailer.py is configured correctly.")
    print("Sent.")