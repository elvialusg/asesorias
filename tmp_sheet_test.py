from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import pathlib
import pandas as pd

json_path = pathlib.Path(r'c:\Users\elvia lucia\Downloads\asesorias-app-490519-f0c18001eb93.json')
info = json.loads(json_path.read_text())
creds = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
result = service.spreadsheets().values().get(spreadsheetId='1ccsY6H-PTrSNiGPadGvlA43YSk6awtRrYUuNfbomzXY', range="'Registro'!A:ZZ").execute()
print('values len', len(result.get('values', [])))
