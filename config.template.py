import os

SFTP_HOST = '<oclc sftp host>'
SFTP_USER = '<user>'
SFTP_PASSWORD = '******'
SFTP_KEY = b"""1234567890"""

ROOT_PATH = '/xfer/wms/'
REPORTS_PATH = 'reports/'
IN_PATH = 'in/patron/'
OUT_PATH = 'out/'

dirname = os.path.dirname(__file__)
LOCAL_PATH = os.path.join(dirname, 'data/')
LOG_LPATH = '%s%s' % (LOCAL_PATH, 'log/')
PATRON_REPORT_LPATH = '%s%s' % (LOCAL_PATH, 'patron_reports/')
PATRON_REPORT_ARCHIVE_LPATH = '%s%s' % (PATRON_REPORT_LPATH, 'archive/')
RESULT_LPATH = '%s%s' % (LOCAL_PATH, 'result_reports/')
XML_LPATH = '%s%s' % (LOCAL_PATH, 'xml/')

PATRON_REPORT_PATTERN = r'^VU@\.Circulation_Patron_Report_Full\.(?P<date>\d{8})\.txt$'
RESULT_REPORT_PATTERN = r'^VU_64\.D\d{8}\.T\d{4}\.%s\.report.%s_\d{6}\.txt$'  # % (<'%Y%m%d'>,<upload xml without extension>,<'%Y-%m-%d'>)
EXCEPTION_REPORT_PATTERN = r'^VU_64\.D\d{8}\.T\d{4}\.%s\.exception.%s_\d{6}\.txt$'  # % (<'%Y%m%d'>,<upload xml without extension>,<'%Y-%m-%d'>)

PATRON_XML_NAME = 'patron_extensions-%s.xml'  # % <'%Y%m%d'>
PATRON_XML_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
PATRON_REPORT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

CATEGORY_RULES = {
    'VU Employee': {
        'expires_in': 2,  # 1 <= expiration date month number - today month number <= X
        'last_activity': 6,  # today month - last activity date month <= X
        'expire_add': 12  # add X months to the existing expiration date)
    },
    'VUmc Employee': {
        'expires_in': 2,
        'last_activity': 6,
        'expire_add': 12
    },
    'VU Student': {
        'expires_in': 2,
        'last_activity': 6,
        'expire_add': 12
    },
    'ILL': {
        'expires_in': 3,
        'last_activity': 6,
        'expire_add': 12
    }
}

MAIL_FROM = '<email-address>'
MAIL_BCC = '<email-address>'
MAIL_TO = '<email-address>'
