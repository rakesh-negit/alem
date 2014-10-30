import httplib2
import logging
import time
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.http import MediaFileUpload, HttpError
from settings import KEY_FILE, ACCOUNT

logger = logging.getLogger(__name__)


class FusionTables:

    '''
    This class abstracts some of the API functions used in other modules
    '''

    def __init__(self):
        self.service = None
        self.http = None

    #Authenticates and build the fusion tables service
    def connect(self, keyFile=KEY_FILE, account=ACCOUNT):

        try:
            f = file(keyFile, 'rb')
        except IOError:
            logger.error('Could not find key file. Please verify settings.')
            return None

        key = f.read()
        f.close()
        credentials = SignedJwtAssertionCredentials(
            account,
            key,
            scope=[
              'https://www.googleapis.com/auth/fusiontables',
              'https://www.googleapis.com/auth/fusiontables.readonly',
            ]
        )

        self.http = httplib2.Http()
        self.http = credentials.authorize(self.http)

        i = 0
        while (not self.service and i < 10 and not time.sleep(10)):
            try:
                self.service = build('fusiontables', 'v1', http=self.http)
            except httplib2.ServerNotFoundError:
                logger.warning('Unable to find server for authentication.')
            except HttpError:
                logger.warning('HTTP error when trying to authenticate.')

        return self.service

    #Insert CSV rows in existing table
    def insert_csv(self, tableId, csvFilename, delimiter=','):
        media = MediaFileUpload(
            csvFilename,
            mimetype='application/octet-stream'
        )

        response = self.service.table().importRows(
            tableId=tableId,
            media_body=media,
            delimiter=delimiter
        ).execute(http=self.http)

        return response

    #Inserts rows from a list into a table
    #The first row of the list should be column names matching the
    #fusion table column names. The other rows are values.
    def insert_list(self, tableId, listIn):
        response = []
        columns = ' , '.join(listIn[0])

        for row in listIn[1:]:
            values = "'{}'".format("' , '".join(row))
            #values = ', '.join(row)
            sql = "INSERT INTO {0} ({1}) VALUES ({2})".format(tableId,
                columns, values)
            response.append(self.service.query().sql(sql=sql).execute())

        return response

    #The findId method may not be reliable as it returns the first table with
    #the given name; there might be multiple tables with the same name
    def find_id(self, name):
        response = self.service.table().list().execute()
        tableId = None
        for table in response['items']:
            if (table['name'] == name):
                tableId = table['tableId']
        return tableId

    def list_columns(self, tableId):
        response = self.service.column().list(tableId=tableId).execute()
        columns = []
        for item in response['items']:
            columns.append("'{0}'".format(item['name']))
        return columns
