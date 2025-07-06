# emailer.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def send_email_report(products):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    recipient = os.environ.get("EMAIL_TO")

    subject = "Sale Notification - Liquor Mart Products"

    html = """
    <html>
    <head>
        <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h3>The following products are currently on sale:</h3>
        <table>
            <tr>
                <th>Product</th>
                <th>Regular Price</th>
                <th>Sale Price</th>
            </tr>
    """

    for p in products:
        html += f"""
            <tr>
                <td><a href='{p['url']}'>{p['title']}</a></td>
                <td>{p.get('regular_price', 'N/A')}</td>
                <td>{p.get('sale_price', 'N/A')}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
            print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
