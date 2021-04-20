import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import socket
import smtplib
from config import *
from patron_helpers import PatronReportParser, PatronXml
from datetime import datetime
import logging

from sftp_helper import SftpDocklands

today = datetime.now()
today_str = today.strftime('%Y%m%d')
LOGFILE = '%spatron_extend-%s.log' % (LOG_LPATH, today_str)
logger = logging.getLogger('patron_extend')
hdlr = logging.FileHandler(LOGFILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def handle_exception():
    send_mail(LOGFILE, 'ERROR: WMS Patron Extension script encountered an error!')
    raise SystemExit(0)


def send_mail(logfile, subject, attachments=[]):
    SUBJECT = subject

    message = MIMEMultipart()
    with open(logfile) as fp:
        # Create a text/plain message
        message.attach(MIMEText(fp.read()))
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
        s = smtplib.SMTP(SMTP_HOST)
        #s.send_message(message)
        s.quit()
        logger.info("successfully sent email")
    except Exception as e:
        logger.error("unable to send email %s" % e)


def housekeeping(days):
    # remove files older than X days
    pass


def get_last_processed():
    try:
        with open('%s%s' % (LOCAL_PATH, 'lastpatronreport'), 'r') as f:
            return f.read()
    except:
        return False


def store_last_processed(report):
    # store the name of the report we are working on so we don't run it again
    with open('%s%s' % (LOCAL_PATH, 'lastpatronreport'), 'w') as f:
        f.write(report)


def get_patron_report(testfile, force):
    s = SftpDocklands()
    if testfile == '':
        try:
            s.get_latest_patron_report()
        except Exception as e:
            logger.error('could not get latest patron report:' + str(e))
            handle_exception()
    else:
        # --> TEST
        logger.info('TEST mode: importing test file')
        s.latest_patron_report = testfile

    if s.latest_patron_report:
        if get_last_processed() == s.latest_patron_report or force:
            logger.info('report %s already processed' % s.latest_patron_report)
        else:
            return s.latest_patron_report
    else:
        logger.info('no report')
        handle_exception()
    return False

def upload_xml_file(xml_filename):
    s=SftpDocklands()
    logger.info('upload xml file %s' % (xml_filename))
    try:
        s.upload_patron_xml(xml_filename)
    except Exception as e:
        logger.error('could not upload xml file:' + str(e))
        handle_exception()

def process_patron_report(testfile='', do_upload=True, force=False):
    changed = False

    latest_patron_report=get_patron_report(testfile, force)
    if latest_patron_report:
        store_last_processed(latest_patron_report)
        p = PatronReportParser()
        res = p.parse_report(latest_patron_report)
        if not res:
            logger.error('patron report could not be parsed, columns have changed?')
            handle_exception()
        else:
            logger.info('%s patrons in report file %s' % (len(p.patron_list), latest_patron_report))
            patrons_to_extend = []
            for patron in p.patron_list:
                if patron.extended():
                    logger.info('%s|%s|%s|%s' % (
                        patron.barcode, patron.category, patron.expiration_date.strftime(PATRON_XML_DATE_FORMAT),
                        patron.last_activity.strftime(PATRON_XML_DATE_FORMAT)))
                    patrons_to_extend.append(patron)

            logger.info('found %s patrons to update' % len(patrons_to_extend))
            if len(patrons_to_extend) > 1000:
                logger.error('more than 1000 patrons to extend, suspect something is wrong')
                handle_exception()
            if len(patrons_to_extend) > 0:
                x = PatronXml()
                x.patron_list = patrons_to_extend
                xml_filename = PATRON_XML_NAME % today_str
                try:
                    with open('%s%s' % (XML_LPATH, xml_filename), 'wb') as f:
                        f.write(x.create())
                except Exception as e:
                    logger.error('could not write xml: %s' % e)
                    handle_exception()

                if do_upload:
                    upload_xml_file(xml_filename)
                    store_last_processed(latest_patron_report)
                else:
                    logger.info('TEST mode: skipping upload')
                changed = True
    return changed


def get_reports():
    s = SftpDocklands()
    try:
        logger.info('retrieving result report')
        s.get_result_report(xml_file=PATRON_XML_NAME % today_str)
    except Exception as e:
        logger.error('could not download xml file:' + str(e))
        handle_exception()
    if s.result_report:
        with open('%s%s' % (RESULT_LPATH, s.result_report), 'r') as myfile:
            data = myfile.read()
        logger.info('result report:\n%s' % data)
    else:
        logger.warning('no result report found')
    return s.result_report, s.exception_report


logger.info('Starting script %s on server %s' % (os.path.realpath(__file__), socket.gethostname()))
changed = process_patron_report(do_upload=False)
if changed:
    counter=1
    report_fetched=False
    while not report_fetched and counter<=5:
        #time.sleep(30*60)
        time.sleep(10)
        result_report, exception_report=get_reports()
        if exception_report:
            report_fetched=True
            with open('%s%s' % (RESULT_LPATH, exception_report), 'r') as myfile:
                data = myfile.read()
                logger.warning('exception report:\n%s' % data)
                send_mail(LOGFILE, 'ATTENTION: WMS Patron Extension script finished with exceptions',
                          attachments=['%s%s' % (XML_LPATH, PATRON_XML_NAME % today_str),
                                       '%s%s' % (RESULT_LPATH, exception_report), '%s%s' % (RESULT_LPATH, result_report)])
        else:
            if result_report:
                report_fetched=True
                send_mail(LOGFILE, 'SUCCESS: WMS Patron Extension script finished with changes',
                          attachments=['%s%s' % (XML_LPATH, PATRON_XML_NAME % today_str),
                                       '%s%s' % (RESULT_LPATH, result_report)])
        counter=counter+1
else:
    send_mail(LOGFILE, 'SUCCESS: WMS Patron Extension script finished with no changes')

