import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.security import e, money


def send_mail(to: str, subject: str, html_body: str, to_name: str | None = None) -> dict:
    if not settings.MAIL_HOST or not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM_ADDRESS:
        return {"success": False, "error": "Mail configuration incomplete in .env"}
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_ADDRESS}>"
        msg["To"] = f"{to_name} <{to}>" if to_name else to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        if settings.MAIL_ENCRYPTION.lower() == "ssl" or settings.MAIL_PORT == 465:
            with smtplib.SMTP_SSL(settings.MAIL_HOST, settings.MAIL_PORT, context=context, timeout=15) as smtp:
                smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                smtp.sendmail(settings.MAIL_FROM_ADDRESS, [to], msg.as_string())
        else:
            with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT, timeout=15) as smtp:
                smtp.starttls(context=context)
                smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                smtp.sendmail(settings.MAIL_FROM_ADDRESS, [to], msg.as_string())
        return {"success": True, "message": "Email sent successfully"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def send_order_confirmation(order: dict, tenant, items: list) -> dict:
    currency = getattr(tenant, "currency", None) or "₹"
    subject = f"Order Confirmation #{order['order_number']} — {tenant.name}"
    rows = ""
    for it in items:
        rental_badge = ""
        if it.get("is_rental"):
            rental_badge = f"<span style='color:#6366f1;font-size:11px;'>[RENTAL: {e(it.get('rental_type'))}]</span>"
        rows += f"""
            <tr>
                <td style='padding:10px;border-bottom:1px solid #e2e8f0;'><strong>{e(it.get('name') or it.get('product_name'))}</strong> {rental_badge}</td>
                <td style='padding:10px;border-bottom:1px solid #e2e8f0;text-align:center;'>{int(it.get('qty') or it.get('quantity') or 1)}</td>
                <td style='padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;'>{currency}{money(it.get('unit_price'))}</td>
                <td style='padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;'><strong>{currency}{money(it.get('line_total'))}</strong></td>
            </tr>
        """
    html = f"""
        <div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;'>
            <div style='background:#0f172a;padding:24px;text-align:center;color:#fff;'>
                <h2 style='margin:0;'>{e(tenant.name)}</h2>
                <p style='margin:5px 0 0;color:#94a3b8;font-size:13px;'>Order Confirmation & Receipt</p>
            </div>
            <div style='padding:24px;'>
                <p>Hello <strong>{e(order['customer_name'])}</strong>,</p>
                <p style='color:#64748b;'>Thank you for your order! Your request has been received and is being processed by our store.</p>
                <div style='background:#f8fafc;border-radius:8px;padding:14px;margin:18px 0;border:1px solid #edf2f7;font-size:13px;'>
                    <div><strong>Order Number:</strong> {e(order['order_number'])}</div>
                    <div><strong>Payment Method:</strong> {e(str(order.get('payment_method','')).upper())}</div>
                    <div><strong>Payment Status:</strong> {e(str(order.get('payment_status','')).upper())}</div>
                </div>
                <table style='width:100%;border-collapse:collapse;font-size:13px;'>
                    <thead>
                        <tr style='background:#f1f5f9;color:#475569;'>
                            <th style='padding:10px;text-align:left;'>Item</th>
                            <th style='padding:10px;text-align:center;'>Qty</th>
                            <th style='padding:10px;text-align:right;'>Price</th>
                            <th style='padding:10px;text-align:right;'>Total</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                    <tfoot>
                        <tr>
                            <td colspan='3' style='padding:12px 10px;text-align:right;font-weight:bold;'>Grand Total:</td>
                            <td style='padding:12px 10px;text-align:right;font-weight:bold;'>{currency}{money(order.get('total_amount'))}</td>
                        </tr>
                    </tfoot>
                </table>
                <p style='font-size:12px;color:#94a3b8;text-align:center;margin-top:30px;'>Sent securely by Metohub SaaS Platform on behalf of {e(tenant.name)}.</p>
            </div>
        </div>
    """
    return send_mail(order["customer_email"], subject, html, order["customer_name"])
