from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import socket
import smtplib
import pysftp
import os
import paramiko
import base64
import csv
from config import *
from rules import CATEGORY_RULES
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pprint import pprint
from lxml import etree as ET
# from ElementTree_pretty import prettify
import logging

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


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


class SftpDocklands():
    def __init__(self):
        self.host = SFTP_HOST
        self.user = SFTP_USER
        self.password = SFTP_PASSWORD
        self.connection = None
        key = paramiko.RSAKey(data=base64.decodebytes(SFTP_KEY))
        self.cnopts = pysftp.CnOpts()
        self.cnopts.hostkeys.add(SFTP_HOST, 'ssh-rsa', key)
        self.latest_patron_report = False
        self.result_report = False
        self.exception_report = False

    def _close(self):
        logger.debug('close connection to %s' % (self.host))
        self.connection.close()

    def _connect(self):
        logger.info('open connection to %s' % (self.host))
        self.connection = pysftp.Connection(self.host, username=self.user, password=self.password, cnopts=self.cnopts)

    def _download(self, path, filename, local_path):
        logger.info('attempting download of %s%s' % (path, filename))
        self._connect()
        self.connection.get('%s%s' % (path, filename), local_path + filename)
        self._close()
        return filename

    def _upload(self, path, file, local_path):
        logger.info('attempting upload of %s%s to %s' % (local_path, file, path))
        self._connect()
        with self.connection.cd(path):
            self.connection.put('%s%s' % (local_path, file))
        self._close()

    def _dir(self, path):
        logger.info('attempting retrieve directory listing of %s' % (path))
        self._connect()
        dir = self.connection.listdir(path)
        self._close()
        return dir

    def get_latest_patron_report(self):
        filedate = datetime.strptime('20000101', '%Y%m%d')
        filename = ''
        reports_path = '%s%s' % (ROOT_PATH, REPORTS_PATH)
        for f in self._dir(reports_path):
            p = re.compile(PATRON_REPORT_PATTERN)
            m = p.match(f)
            if m:
                d = datetime.strptime(m.group('date'), '%Y%m%d')
                if d > filedate:
                    filedate = d
                    filename = f
        if diff_month(datetime.now(), filedate) <= 1:
            self.latest_patron_report = self._download(reports_path, filename, PATRON_REPORT_LPATH)
        else:
            raise ValueError('No recent patron report found in %s' % reports_path)
            self.latest_patron_report = False

    def get_result_report(self, xml_file):
        report_path = '%s%s' % (ROOT_PATH, REPORTS_PATH)
        self.result_report = False
        for f in self._dir(report_path):
            p = re.compile(RESULT_REPORT_PATTERN % (os.path.splitext(xml_file)[0], today.strftime('%Y-%m-%d')))
            m = p.match(f)
            pe = re.compile(EXCEPTION_REPORT_PATTERN % (os.path.splitext(xml_file)[0], today.strftime('%Y-%m-%d')))
            me = pe.match(f)
            print(me, f)
            if m:
                self.result_report = self._download('%s%s' % (ROOT_PATH, REPORTS_PATH), f, RESULT_LPATH)
            if me:
                self.exception_report = self._download('%s%s' % (ROOT_PATH, REPORTS_PATH), f, RESULT_LPATH)

    def upload_patron_xml(self, xml_file):
        self._upload('%s%s' % (ROOT_PATH, IN_PATH), xml_file, XML_LPATH)


class Patron():
    def __init__(self):
        self.expiration_date = ''
        self.given_name = ''
        self.family_name = ''
        self.barcode = ''
        self.category = ''
        self.branch = ''
        self.last_activity = ''
        self.institution = '67271'

    def _is_correct_category(self):
        if self.category in CATEGORY_RULES:
            return True
        else:
            return False

    def _is_active(self):
        if diff_month(datetime.now(), self.last_activity) <= CATEGORY_RULES[self.category]['last_activity']:
            return True
        else:
            return False

    def _is_expiring(self):
        # if 0<= diff_month(self.expiration_date, datetime.now()) <=3: print(self.expiration_date, diff_month(self.expiration_date, datetime.now()))
        if (1 <= diff_month(self.expiration_date, datetime.now()) <= CATEGORY_RULES[self.category]['expires_in']) and (
                self.expiration_date > datetime.now()):
            return True
        else:
            return False

    def move_expiration(self):
        self.expiration_date = self.expiration_date + relativedelta(months=CATEGORY_RULES[self.category]['expire_add'])

    def extended(self):
        if self._is_correct_category():
            if self._is_active() and self._is_expiring():
                self.move_expiration()
                return True
        return False


class PatronReportParser():
    def __init__(self):
        self.patron_list = []
        self.header = 'Inst_Symbol|Patron_Given_Name|Patron_Family_Name|Patron_Gender|Patron_Date_of_Birth|Patron_Barcode|Patron_Borrower_Category|Patron_Home_Branch_ID|Patron_Street_Address1|Patron_Street_Address2|Patron_City_or_Locality|Patron_State_or_Province|Patron_Postal_Code|Patron_Phone_Number|Patron_Email_Address|Patron_Verified_Flag|Patron_Total_Fines|Patron_Created_Date|Patron_Source_System|Patron_Expiration_Date|Patron_User_ID_At_Source|Patron_Blocked_Flag|Patron_Username|Patron_Last_Activity_Date|Patron_Last_Modified_Date'

    def parse_report(self, report):
        file = '%s%s' % (PATRON_REPORT_LPATH, report)
        lol = list(csv.reader(open(file, 'rt', encoding='utf8'), delimiter='|'))
        if lol[0] != self.header.split('|'):
            return False
        header = True
        for line in lol:
            if header:
                header = False
            else:
                patron = Patron()
                patron.expiration_date = datetime.strptime(line[lol[0].index('Patron_Expiration_Date')],
                                                           PATRON_REPORT_DATE_FORMAT)
                patron.given_name = line[lol[0].index('Patron_Given_Name')]
                patron.family_name = line[lol[0].index('Patron_Family_Name')]
                patron.barcode = line[lol[0].index('Patron_Barcode')]
                patron.category = line[lol[0].index('Patron_Borrower_Category')]
                patron.branch = line[lol[0].index('Patron_Home_Branch_ID')]
                patron.last_activity = datetime.strptime(line[lol[0].index('Patron_Last_Activity_Date')],
                                                         PATRON_REPORT_DATE_FORMAT)
                self.patron_list.append(patron)


class PatronXml():
    def __init__(self):
        self.patron_list = []
        self.xml = None

    def create(self):
        nsmap = {
            None: 'http://worldcat.org/xmlschemas/IDMPersonas-2.2',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

        root = ET.Element('oclcPersonas', nsmap=nsmap)
        root.attrib['{{{pre}}}schemaLocation'.format(pre=nsmap[
            'xsi'])] = 'http://worldcat.org/xmlschemas/IDMPersonas-2.2 http://worldcat.org/xmlschemas/IDMPersonas/2.2/IDMPersonas-2.2.xsd'

        for patron in self.patron_list:
            person = ET.SubElement(root, 'persona', institutionId=patron.institution)
            ed = ET.SubElement(person, 'oclcExpirationDate')
            ed.text = patron.expiration_date.strftime(PATRON_XML_DATE_FORMAT)

            ni = ET.SubElement(person, 'nameInfo')
            gn = ET.SubElement(ni, 'givenName')
            gn.text = patron.given_name
            fn = ET.SubElement(ni, 'familyName')
            fn.text = patron.family_name

            wc = ET.SubElement(person, 'wmsCircPatronInfo')
            bc = ET.SubElement(wc, 'barcode')
            bc.text = patron.barcode
            ba = ET.SubElement(wc, 'borrowerCategory')
            ba.text = patron.category
            hb = ET.SubElement(wc, 'homeBranch')
            hb.text = patron.branch

        return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')


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
        s.send_message(message)
        s.quit()
        logger.info("successfully sent email")
    except Exception as e:
        logger.error("unable to send email %s" % e)


def housekeeping(days):
    # remove files older than X days
    pass


def last_processed():
    try:
        with open('%s%s' % (LOCAL_PATH, 'lastpatronreport'), 'r') as f:
            return f.read()
    except:
        return False


def store_last_processed(report):
    with open('%s%s' % (LOCAL_PATH, 'lastpatronreport'), 'w') as f:
        f.write(report)


def run1(testfile='', do_upload=True, force=False):
    changed = False
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

    process = False
    if s.latest_patron_report:
        if last_processed() == s.latest_patron_report or force:
            logger.info('report %s already processed' % s.latest_patron_report)
        else:
            process = True
    else:
        logger.info('no report')
        handle_exception()

    if process:
        with open('%s%s' % (LOCAL_PATH, 'lastpatronreport'), 'w') as f:
            f.write(s.latest_patron_report)

        p = PatronReportParser()
        p.parse_report(s.latest_patron_report)

        logger.info('%s patrons in report file %s' % (len(p.patron_list), s.latest_patron_report))

        patrons_to_extend = []
        for patron in p.patron_list:
            # if patron.expiration_date < patron.last_activity:  print(patron.barcode, patron.category, patron.expiration_date, patron.last_activity)
            d1 = patron.expiration_date.strftime(PATRON_XML_DATE_FORMAT)
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
                logger.info('upload xml file %s' % (xml_filename))
                try:
                    s.upload_patron_xml(xml_filename)
                    store_last_processed(s.latest_patron_report)
                except Exception as e:
                    logger.error('could not upload xml file:' + str(e))
                    handle_exception()
            else:
                logger.info('TEST mode: skipping upload')
            changed = True

        return changed


def run2():
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
        report = True
    else:
        report = False
        logger.warning('no result report found')
        # retry in 30 minutes?
        # run2()
    if s.exception_report:
        with open('%s%s' % (RESULT_LPATH, s.exception_report), 'r') as myfile:
            data = myfile.read()
        logger.warning('exception report:\n%s' % data)
        send_mail(LOGFILE, 'ATTENTION: WMS Patron Extension script finished with exceptions',
                  attachments=['%s%s' % (XML_LPATH, PATRON_XML_NAME % today_str),
                               '%s%s' % (RESULT_LPATH, s.exception_report), '%s%s' % (RESULT_LPATH, s.result_report)])
    else:
        if report:
            send_mail(LOGFILE, 'SUCCESS: WMS Patron Extension script finished with changes',
                      attachments=['%s%s' % (XML_LPATH, PATRON_XML_NAME % today_str),
                                   '%s%s' % (RESULT_LPATH, s.result_report)])
        else:
            send_mail(LOGFILE, 'ATTENTION: WMS Patron Extension script finished without report',
                      attachments=['%s%s' % (XML_LPATH, PATRON_XML_NAME % today_str)])


logger.info('Starting script %s on server %s.ubvu.vu.nl' % (os.path.realpath(__file__), socket.gethostname()))
checkfile1 = '%s%s' % (LOCAL_PATH, 'run1')
checkfile2 = '%s%s' % (LOCAL_PATH, 'run2')
if os.path.isfile(checkfile2):
    with open(checkfile2, 'r') as f:
        data = f.read()
    try:
        os.remove(checkfile2)
    except:
        logger.error('could not remove %s quitting' % checkfile2)
        handle_exception()
    logger.info('start run2')
    if data == 'run':
        run2()
    else:
        logger.info('nothing uploaded in first run, skip run2')
        send_mail(LOGFILE, 'SUCCESS: WMS Patron Extension script finished with no changes')
    logger.info('end run2')
elif os.path.isfile(checkfile1):
    logger.error('first run did not finish, skip second run')
    try:
        os.remove(checkfile1)
    except:
        logger.error('could not remove %s quitting' % checkfile1)
else:  # first run
    with open(checkfile1, 'w') as f:
        f.write('')
    logger.info('start run1')
    # changed = run1(testfile='VU@.Circulation_Patron_Report_Test.20180724.txt', do_upload=False)
    # changed = run1(do_upload=False)
    changed = run1()
    try:
        os.remove(checkfile1)
    except:
        logger.error('could not remove %s quitting' % checkfile1)
        handle_exception()
    if changed:
        with open(checkfile2, 'w') as f:
            f.write('run')
    else:
        with open(checkfile2, 'w') as f:
            f.write('skip')
    logger.info('end run1')
