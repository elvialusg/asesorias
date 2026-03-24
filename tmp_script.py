from asesorias_app.repositories.google_sheets_repository import GoogleSheetsRepository
from asesorias_app import config
config.GOOGLE_SHEETS_SPREADSHEET_ID = '1ccsY6H-PTrSNiGPadGvlA43YSk6awtRrYUuNfbomzXY'
config.GOOGLE_SHEETS_REGISTRO_RANGE = "'Registro'!A:ZZ"
repo = GoogleSheetsRepository()
print('Range', repo.registro_range)
print('Cred file', repo.credentials_file)
print('Using info', bool(config.SERVICE_ACCOUNT_INFO))
df = repo.load_registro()
print('Rows', len(df))
print(df.head())
