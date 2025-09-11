import os
import io
import whisper
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Config
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"

# Autenticació
creds = service_account.Credentials.from_service_account_info(
    eval(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
    scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)

# 1. Trobar arxius nous a la carpeta d'entrada
results = service.files().list(
    q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()
files = results.get("files", [])

if not files:
    print("No hi ha arxius nous")
    exit()

# 2. Baixar el primer arxiu d'àudio
file_id = files[0]["id"]
file_name = files[0]["name"]
request = service.files().get_media(fileId=file_id)
fh = io.FileIO(file_name, "wb")
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    status, done = downloader.next_chunk()
fh.close()
print(f"✅ Arxiu baixat: {file_name}")

# 3. Transcriure amb Whisper
model = whisper.load_model("small")
result = model.transcribe(file_name, language="ca")
print(f"✅ Arxiu transcrit: {file_name}")

# 4. Guardar SRT i debug al repo
srt_file = file_name.rsplit(".", 1)[0] + ".srt"
with open(srt_file, "w", encoding="utf-8") as f:
    f.write(result["text"])

debug_file = "debug_transcript.txt"
with open(debug_file, "w", encoding="utf-8") as f:
    f.write(result["text"])
print(f"✅ Text guardat a {debug_file} per debugging i a {srt_file}")
