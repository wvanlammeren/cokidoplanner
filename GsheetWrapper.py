import gspread
from oauth2client.service_account import ServiceAccountCredentials

"""
wrapper for google sheet operations (authentication).
returns a gsheet object
"""


class GsheetWrapper:

    def __init__(self):
        # Initiate connection to a specific google sheet & load the data
        self.SAMPLE_SPREADSHEET_ID = "1O9JeqxwKyCNotiuyewdQUgi-6WZX2dHPx_hvL7_H8lY"
        self.scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name("gs_credentials.json", self.scope)
        print('created gsheet object')

    def get_document(self):
        print('connect gsheetwrapper object')
        client = gspread.authorize(self.credentials)
        return client.open_by_key(self.SAMPLE_SPREADSHEET_ID)
