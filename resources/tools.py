from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import logging
import os
from resources.config import MAIL_FROM, MAIL_TO, MAIL_BCC, SMTP_HOST

logger = logging.getLogger('patron_extend')
def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month

def send_mail(logfile, subject, attachments=[]):
    SUBJECT = subject

    message = MIMEMultipart()
    with open(logfile) as fp:
        # Create a text/plain message
        text = fp.read().replace("@", "[at]")
        message.attach(MIMEText(text))
    message['From'] = MAIL_FROM
    message['To'] = MAIL_TO
    message['Bcc'] = MAIL_BCC
    message['Subject'] = SUBJECT

    for path in attachments:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename="{}"'.format(os.path.basename(path)))
        message.attach(part)

    try:
        s = smtplib.SMTP(SMTP_HOST, source_address=("130.37.194.20", 0))
        s.send_message(message)
        s.quit()
        logger.info("successfully sent email")
    except Exception as e:
        logger.error("unable to send email %s" % e)