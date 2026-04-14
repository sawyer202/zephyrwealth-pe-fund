"""
Email notifications service — ZephyrWealth
Sends transactional emails via SendGrid.
All errors are caught and logged — never blocks the main operation.
"""
import os
import asyncio
import logging
from datetime import datetime, timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, MailSettings, SandBoxMode

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@zephyrtrustai.com")
SANDBOX = os.environ.get("SENDGRID_SANDBOX", "false").lower() == "true"
PORTAL_URL = os.environ.get("PORTAL_URL", "https://zephyrtrustai.com/portal/login")
FUND_NAME = "Zephyr Caribbean Growth Fund I"


# ─── Shared HTML helpers ──────────────────────────────────────────────────────
def _header() -> str:
    return """
    <div style="font-family: 'Inter', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background-color: #111110; padding: 28px 36px; border-radius: 4px 4px 0 0;">
        <span style="font-size: 22px; font-weight: 500; letter-spacing: -0.5px; color: #ffffff;">Zephyr</span><span style="font-size: 22px; font-weight: 500; letter-spacing: -0.5px; color: #00A8C6;">Wealth</span>
      </div>
      <div style="background-color: #ffffff; padding: 36px 36px 0 36px; border-left: 1px solid #E8E6E0; border-right: 1px solid #E8E6E0;">
    """


def _footer() -> str:
    return """
      </div>
      <div style="background-color: #FAFAF8; padding: 20px 36px; border: 1px solid #E8E6E0; border-top: none; border-radius: 0 0 4px 4px; text-align: center;">
        <p style="margin: 0; font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 11px; color: #888880; line-height: 1.6;">
          Zephyr Asset Management Ltd &nbsp;|&nbsp; SCB Licensed Fund SCB-2024-PE-0042<br>
          This email is confidential and intended solely for the named recipient.
        </p>
      </div>
    </div>
    """


def _cta_button(label: str, url: str) -> str:
    return f"""
    <div style="text-align: center; margin: 32px 0;">
      <a href="{url}"
         style="display: inline-block; background-color: #00A8C6; color: #ffffff; font-family: 'Inter', Helvetica, Arial, sans-serif;
                font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 3px; text-decoration: none; letter-spacing: 0.2px;">
        {label}
      </a>
    </div>
    """


def _table_row(label: str, value: str, bold: bool = False) -> str:
    val_style = "font-weight: 700; color: #00A8C6; font-size: 16px;" if bold else "color: #0F0F0E;"
    return f"""
    <tr>
      <td style="padding: 10px 14px; font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 13px;
                 color: #888880; border-bottom: 1px solid #F3F4F6; font-weight: 600;
                 text-transform: uppercase; letter-spacing: 0.5px; width: 40%;">{label}</td>
      <td style="padding: 10px 14px; font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 13px;
                 {val_style} border-bottom: 1px solid #F3F4F6;">{value}</td>
    </tr>
    """


def _payment_box(fund_profile: dict, investor_name: str, call_name: str) -> str:
    bank = fund_profile.get("bank_name", "Bank of The Bahamas") if fund_profile else "Bank of The Bahamas"
    account = fund_profile.get("account_number") or fund_profile.get("bank_account_number", "4521-9900-0087") if fund_profile else "4521-9900-0087"
    swift = fund_profile.get("swift") or fund_profile.get("swift_code", "BAHABSNA") if fund_profile else "BAHABSNA"
    reference = f"{investor_name} — {call_name}"
    return f"""
    <div style="background-color: #FAFAF8; border: 1px solid #E8E6E0; border-radius: 4px; padding: 20px 20px 8px 20px; margin: 24px 0;">
      <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 11px; font-weight: 700;
                color: #888880; text-transform: uppercase; letter-spacing: 0.8px; margin: 0 0 12px 0;">
        Payment Instructions
      </p>
      <table style="width: 100%; border-collapse: collapse;">
        {_table_row("Bank Name", bank)}
        {_table_row("Account Number", account)}
        {_table_row("SWIFT Code", swift)}
        {_table_row("Payment Reference", reference)}
      </table>
    </div>
    """


# ─── Capital Call Email ───────────────────────────────────────────────────────
def _build_capital_call_html(
    investor_name: str,
    call_name: str,
    issue_date: str,
    due_date: str,
    amount_due: float,
    fund_profile: dict,
) -> str:
    formatted_amount = f"${amount_due:,.2f}"
    return f"""
    {_header()}
    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 15px; color: #0F0F0E; margin: 0 0 16px 0;">
      Dear {investor_name},
    </p>
    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 14px; color: #888880; margin: 0 0 24px 0; line-height: 1.7;">
      A capital call has been issued for <strong style="color: #0F0F0E;">{FUND_NAME}</strong>.
      Please review the details below and arrange payment by the due date.
    </p>

    <table style="width: 100%; border-collapse: collapse; border: 1px solid #E8E6E0; border-radius: 4px; overflow: hidden; margin-bottom: 0;">
      {_table_row("Call Name", call_name)}
      {_table_row("Issue Date", issue_date)}
      {_table_row("Due Date", due_date)}
      {_table_row("Your Amount Due", formatted_amount, bold=True)}
    </table>

    {_payment_box(fund_profile, investor_name, call_name)}

    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 13px; color: #888880; margin: 24px 0 0 0; line-height: 1.6;">
      You can download your formal Capital Call Notice from your investor portal.
    </p>

    {_cta_button("View Your Portal", PORTAL_URL)}

    <div style="border-top: 1px solid #F3F4F6; padding: 20px 0 24px 0;">
      <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 12px; color: #888880; margin: 0; line-height: 1.6;">
        If you have questions, please contact your relationship manager at
        <a href="mailto:compliance@zephyrwealth.ai" style="color: #00A8C6;">compliance@zephyrwealth.ai</a>.
      </p>
    </div>
    {_footer()}
    """


# ─── Distribution Email ───────────────────────────────────────────────────────
def _build_distribution_html(
    investor_name: str,
    distribution_name: str,
    dist_type: str,
    deal_name: str,
    gross_amount: float,
    net_amount: float,
    payment_date: str,
) -> str:
    return f"""
    {_header()}
    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 15px; color: #0F0F0E; margin: 0 0 16px 0;">
      Dear {investor_name},
    </p>
    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 14px; color: #888880; margin: 0 0 24px 0; line-height: 1.7;">
      A distribution has been processed to your account from
      <strong style="color: #0F0F0E;">{FUND_NAME}</strong>.
    </p>

    <table style="width: 100%; border-collapse: collapse; border: 1px solid #E8E6E0; border-radius: 4px; overflow: hidden;">
      {_table_row("Distribution Name", distribution_name)}
      {_table_row("Type", dist_type.replace("_", " ").title())}
      {_table_row("Deal", deal_name or "—")}
      {_table_row("Gross Amount", f"${gross_amount:,.2f}")}
      {_table_row("Net Amount", f"${net_amount:,.2f}", bold=True)}
      {_table_row("Payment Date", payment_date)}
    </table>

    <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 13px; color: #888880; margin: 24px 0 0 0; line-height: 1.6;">
      Please allow 3–5 business days for funds to appear in your registered account.
    </p>

    {_cta_button("View Your Portal", PORTAL_URL)}

    <div style="border-top: 1px solid #F3F4F6; padding: 20px 0 24px 0;">
      <p style="font-family: 'Inter', Helvetica, Arial, sans-serif; font-size: 12px; color: #888880; margin: 0; line-height: 1.6;">
        Questions? Contact us at
        <a href="mailto:compliance@zephyrwealth.ai" style="color: #00A8C6;">compliance@zephyrwealth.ai</a>.
      </p>
    </div>
    {_footer()}
    """


# ─── Core send function ───────────────────────────────────────────────────────
def _send_email_sync(to_email: str, subject: str, html_content: str) -> bool:
    """Synchronous send — run via asyncio.to_thread to avoid blocking the event loop."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping email to %s", to_email)
        return False
    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )
        if SANDBOX:
            mail_settings = MailSettings()
            mail_settings.sandbox_mode = SandBoxMode(enable=True)
            message.mail_settings = mail_settings

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        mode = "SANDBOX" if SANDBOX else "LIVE"
        logger.info("Email sent [%s] to %s | status %s", mode, to_email, response.status_code)
        return True
    except Exception as exc:
        logger.error("SendGrid error sending to %s: %s", to_email, exc)
        return False


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Non-blocking email send — never raises, errors are logged only."""
    try:
        return await asyncio.to_thread(_send_email_sync, to_email, subject, html_content)
    except Exception as exc:
        logger.error("Async email dispatch error: %s", exc)
        return False


# ─── Public triggers ──────────────────────────────────────────────────────────
async def notify_capital_call_issued(db, call: dict) -> None:
    """
    Send capital call notification to each investor line item that has a portal account.
    Fires independently — failure never surfaces to the caller.
    """
    fund_profile = await db.fund_profile.find_one({})
    call_name = call.get("call_name", "")
    issue_dt = call.get("call_date") or call.get("created_at") or datetime.now(timezone.utc)
    due_dt = call.get("due_date") or issue_dt
    issue_str = issue_dt.strftime("%b %d, %Y") if isinstance(issue_dt, datetime) else str(issue_dt)[:10]
    due_str = due_dt.strftime("%b %d, %Y") if isinstance(due_dt, datetime) else str(due_dt)[:10]

    for li in call.get("line_items", []):
        investor_id = li.get("investor_id")
        investor_name = li.get("investor_name", "Investor")
        amount_due = li.get("call_amount", 0)
        if not investor_id:
            continue
        # Look up investor's portal email
        portal_user = await db.investor_users.find_one({"investor_id": investor_id})
        if not portal_user or not portal_user.get("email"):
            continue
        to_email = portal_user["email"]
        subject = f"Capital Call Notice — {call_name} | {FUND_NAME}"
        html = _build_capital_call_html(investor_name, call_name, issue_str, due_str, amount_due, fund_profile)
        await send_email(to_email, subject, html)


async def notify_distribution_paid(db, distribution: dict, investor_id: str, line_item: dict) -> None:
    """
    Send distribution paid notification to the specific investor.
    Fires independently — failure never surfaces to the caller.
    """
    portal_user = await db.investor_users.find_one({"investor_id": investor_id})
    if not portal_user or not portal_user.get("email"):
        return

    to_email = portal_user["email"]
    investor_name = line_item.get("investor_name", "Investor")
    dist_name = distribution.get("distribution_name", "Distribution")
    dist_type = distribution.get("type", "income")
    deal_name = distribution.get("deal_name", "")
    gross = line_item.get("gross_amount", 0)
    net = line_item.get("net_amount", 0)
    payment_dt = distribution.get("payment_date") or datetime.now(timezone.utc)
    payment_str = payment_dt.strftime("%b %d, %Y") if isinstance(payment_dt, datetime) else str(payment_dt)[:10]

    subject = f"Distribution Notice — {dist_name} | {FUND_NAME}"
    html = _build_distribution_html(investor_name, dist_name, dist_type, deal_name, gross, net, payment_str)
    await send_email(to_email, subject, html)
