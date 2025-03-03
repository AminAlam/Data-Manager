import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

def send_email(receiver_email, sender_email, password, subject, html):
    smtp_server = "smtp.gmail.com"
    port = 465 
    context = ssl.create_default_context()

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    
    html = MIMEText(html, "html")
    message.attach(html)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            return True
    except Exception as e:
        print(e)
        return False

        

def send_welcome_mail(info):
    receiver_email = info['receiver_email']
    sender_email = info['sender_email']
    password = info['password']
    subject = info['subject']
    username = info['username']
    user_password = info['user_password']
    website_url = info['website_url']
    name = info['name']

    html = f"""
    <div>
    <p> Dear {name}, </p>
    <p> Welcome to the datamanager! </p>
    <p> You have been registered in the datamanager. You can login with the following credentials via this <a href="https://{website_url}">link</a>. </p>
    <p> Your username is: {username} </p>
    <p> Your password is: {user_password} </p>
    <br>
    <p> Please change your password after the first login. </p>
    <br>
    <p> Best regards, </p>
    <p> The datamanager team </p>
    </div>
    """
    send_email(receiver_email, sender_email, password, subject, html)

def send_report_mail(info):
    receiver_email = info['receiver_email']
    sender_email = info['sender_email']
    password = info['password']
    subject = info['subject']
    txt = info['txt']
    link2entry = info['link2entry']
    sender_username = info['sender_username']
    
    html = f"""
    <div>
    <p> You were notified by {sender_username} about the following entry in the datamanager: </p>
    <br>
    <a href="https://{link2entry}"> Link to entry</a>
    <br>
    <br>
    <p> Entry report: </p>
    <p> {txt} </p>

    </div>
    """
    return send_email(receiver_email, sender_email, password, subject, html)

def send_new_order_mail(info):
    receiver_email = info['receiver_email']
    sender_email = info['sender_email']
    password = info['password']
    subject = info['subject']
    txt = info['txt']
    link2entry = info['link2entry']
    sender_username = info['sender_username']

    html = f"""
    <div>
    <p> {txt} </p>
    <br>
    <a href="https://{link2entry}">View in Orders Dashboard</a>
    <br>
    <br>
    </div>
    """
    send_email(receiver_email, sender_email, password, subject, html)


def send_order_notification(info):
    receiver_email = info['receiver_email']
    sender_email = info['sender_email']
    password = info['password']
    subject = info['subject']
    txt = info['txt']
    link2entry = info['link2entry']
    sender_username = info['sender_username']
    
    html = f"""
    <div>
    <p>{txt}</p>
    <br>
    <a href="https://{link2entry}">View in Orders Dashboard</a>
    <br>
    <br>
    <p>Best regards,</p>
    <p>The datamanager team</p>
    </div>
    """
    send_email(receiver_email, sender_email, password, subject, html) 

def send_order_status_mail(info):
    receiver_email = info['receiver_email']
    sender_email = info['sender_email']
    password = info['password']
    subject = info['subject']
    txt = info['txt']
    link2entry = info['link2entry']
    sender_username = info['sender_username']

    html = f"""
    <div>
    <p>{txt}</p>
    <br>
    <a href="https://{link2entry}">View in Orders Dashboard</a>
    """
    send_email(receiver_email, sender_email, password, subject, html)
