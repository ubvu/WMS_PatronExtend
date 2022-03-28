import pysftp
import paramiko
import base64
import re
from datetime import datetime
import logging
import os
from resources.config import SFTP_HOST, SFTP_USER, SFTP_PASSWORD, SFTP_KEY, ROOT_PATH, REPORTS_PATH, PATRON_REPORT_PATTERN, \
    PATRON_REPORT_LPATH, RESULT_REPORT_PATTERN, EXCEPTION_REPORT_PATTERN, RESULT_LPATH, IN_PATH, XML_LPATH
from resources.tools import diff_month

today = datetime.now()
logger = logging.getLogger('patron_extend')

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
        logger.debug('open connection to %s' % (self.host))
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
        self.exception_report = False
        for f in self._dir(report_path):
            p = re.compile(RESULT_REPORT_PATTERN % (os.path.splitext(xml_file)[0], today.strftime('%Y-%m-%d')))
            m = p.match(f)
            pe = re.compile(EXCEPTION_REPORT_PATTERN % (os.path.splitext(xml_file)[0], today.strftime('%Y-%m-%d')))
            me = pe.match(f)
            if m:
                self.result_report = self._download('%s%s' % (ROOT_PATH, REPORTS_PATH), f, RESULT_LPATH)
            if me:
                self.exception_report = self._download('%s%s' % (ROOT_PATH, REPORTS_PATH), f, RESULT_LPATH)

    def upload_patron_xml(self, xml_file):
        self._upload('%s%s' % (ROOT_PATH, IN_PATH), xml_file, XML_LPATH)