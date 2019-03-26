# WMS_PatronExtend

Python script to renew WMS library patrons. 

Set activity and renewal periods by *borrowerCategory* in rules.py

The script makes use of the OCLC sftp server to download the borrower report and upload the xml with changes. Rename config.template.py to config.py and set the correct paths and authentication for your library.
