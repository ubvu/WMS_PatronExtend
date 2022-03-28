import csv
from resources.config import PATRON_REPORT_LPATH, PATRON_REPORT_DATE_FORMAT, PATRON_XML_DATE_FORMAT
from resources.rules import CATEGORY_RULES
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree as ET
from resources.tools import diff_month


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
        self.header = 'Inst_Symbol|Patron_Given_Name|Patron_Family_Name|Patron_Gender|Patron_Date_of_Birth|Patron_Barcode|Patron_Borrower_Category|Patron_Home_Branch_ID|Patron_Street_Address1|Patron_Street_Address2|Patron_City_or_Locality|Patron_State_or_Province|Patron_Postal_Code|Patron_Phone_Number|Patron_Email_Address|Patron_Verified_Flag|Patron_Total_Fines|Patron_Created_Date|Patron_Source_System|Patron_Expiration_Date|Patron_User_ID_At_Source|Patron_Blocked_Flag|Patron_Username|Patron_Last_Activity_Date|Patron_Last_Modified_Date|Patron_Custom_Category_1|Patron_Custom_Category_2|Patron_Custom_Category_3|Patron_Custom_Category_4|Patron_Country|Patron_Public_Notes|Patron_Staff_Notes'

    def parse_report(self, report):
        file = '%s%s' % (PATRON_REPORT_LPATH, report)
        lol = list(csv.reader(open(file, 'rt', encoding='utf8'), delimiter='|'))
        if lol[0] != self.header.split('|'):
            return False
        for line in lol[1:]:
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
        return True


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
