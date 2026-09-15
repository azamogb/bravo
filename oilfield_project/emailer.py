import os
import time
import logging
import mimetypes
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email import encoders

from dotenv import load_dotenv

from config import (
    SENDER_EMAIL,
    EMAIL_PASS,
    SMTP_HOST,
    SMTP_PORT,
    MAX_ATTACHMENT_BYTES,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)


load_dotenv() 


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("emailer.log"),
    ],
)
logger = logging.getLogger(__name__)


def _build_attachment_part(path):
    """Read a single file from disk and return it as a MIME part,
    auto-detecting its content type instead of forcing octet-stream."""

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Attachment not found: {path}")

    size = os.path.getsize(path)
    if size > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachment too large: {path} is {size / (1024*1024):.1f}MB "
            f"(limit is {MAX_ATTACHMENT_BYTES / (1024*1024):.0f}MB)"
        )

    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        # Fallback for unknown/compressed types
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(path, "rb") as f:
        data = f.read()

    if maintype == "image":
        part = MIMEImage(data, _subtype=subtype)
    elif maintype == "audio":
        part = MIMEAudio(data, _subtype=subtype)
    else:
        part = MIMEBase(maintype, subtype)
        part.set_payload(data)
        encoders.encode_base64(part)

    part.add_header(
        "Content-Disposition", f"attachment; filename={os.path.basename(path)}"
    )
    return part


def send_email(
    to_email,
    subject,
    body,
    attachment_path=None,
    attachment_paths=None,
    cc_email=None,
    bcc_email=None,
):
    """Send an email via Gmail SMTP.

    Args:
        to_email: str, single recipient or comma-separated list.
        subject: str
        body: str, plain-text body.
        attachment_path: str, single file path. Matches the team's agreed
            interface (send_email(to_email, subject, body, attachment_path=None)).
        attachment_paths: str, or list of str file paths. Optional extra —
            use this if you need to attach more than one file.
        cc_email: str, single or comma-separated CC recipients. Optional.
        bcc_email: str, single or comma-separated BCC recipients. Optional.
    """
    # 1. Get password from config (sourced from EMAIL_PASS env var / .env)
    if not EMAIL_PASS:
        raise ValueError("Set EMAIL_PASS env variable (or add it to a .env file)!")

    # 2. Build message
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc_email:
        msg["Cc"] = cc_email
    # Note: BCC is deliberately NOT added as a header -- it's only
    # included in the actual envelope recipient list below, otherwise
    # it wouldn't be "blind" anymore.
    msg.attach(MIMEText(body, "plain"))

    # 3. Merge the singular (team contract) and plural attachment args
    #    into one list, then attach each file if provided.
    all_attachments = []
    if attachment_path:
        all_attachments.append(attachment_path)
    if attachment_paths:
        if isinstance(attachment_paths, str):
            all_attachments.append(attachment_paths)
        else:
            all_attachments.extend(attachment_paths)

    for path in all_attachments:
        try:
            part = _build_attachment_part(path)
            msg.attach(part)
            logger.info(f"Attached file: {path}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            raise

    # 4. Work out the full envelope recipient list (To + Cc + Bcc)
    recipients = [addr.strip() for addr in to_email.split(",")]
    if cc_email:
        recipients += [addr.strip() for addr in cc_email.split(",")]
    if bcc_email:
        recipients += [addr.strip() for addr in bcc_email.split(",")]

    # 5. Connect & send, with retries for transient failures
    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SENDER_EMAIL, EMAIL_PASS)
                server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
            logger.info(f"Email sent to {to_email} (cc={cc_email}, bcc={bcc_email})")
            return
        except smtplib.SMTPAuthenticationError as e:
            # No point retrying bad credentials
            logger.error(f"Authentication failed: {e}")
            raise
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, OSError) as e:
            logger.warning(
                f"Attempt {attempt}/{MAX_RETRIES} failed to connect/send: {e}"
            )
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.error("Max retries reached. Email not sent.")
                raise
        except smtplib.SMTPException as e:
            # Any other SMTP-level error -- not necessarily worth retrying
            logger.error(f"SMTP error: {e}")
            raise