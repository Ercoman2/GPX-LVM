import os
import io
import whisper
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload

# Config
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"
OUTPUT_FOLDER_ID = "1JnxA6r8Kf4HWggUWVpoZqcd_UeSdrOpw"

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
srt_content = whisper.utils.write_srt(result["segments"])
print(f"✅ Arxiu transcrit: {file_name}")

# 4. Guardar SRT i debug al repo
srt_file = file_name.rsplit(".", 1)[0] + ".srt"
with open(srt_file, "w", encoding="utf-8") as f:
    f.write(srt_content)

debug_file = "debug_transcript.txt"
with open(debug_file, "w", encoding="utf-8") as f:
    f.write(result["text"])
print(f"✅ Text guardat a {debug_file} per debugging i a {srt_file}")

# 4. Pujar el .srt a la carpeta de sortida
if os.path.exists(srt_file) and os.path.getsize(srt_file) > 0:
    file_metadata = {"name": srt_file, "parents": [OUTPUT_FOLDER_ID]}
    media = MediaFileUpload(srt_file, mimetype="text/plain", resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields="id")
    
    response = None
    max_retries = 5
    retry = 0
    
    while response is None:
        try:
            status, response = request.next_chunk()
            if response is not None:
                print(f"✅ {srt_file} pujat a la carpeta de sortida!")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                if retry < max_retries:
                    sleep_time = 2 ** retry
                    print(f"Retry {retry + 1} after {sleep_time}s due to error {e.resp.status}")
                    time.sleep(sleep_time)
                    retry += 1
                else:
                    print("Exceeded maximum retries. Upload failed.")
                    raise
            else:
                raise
else:
    print(f"❌ Error: {srt_file} no existeix o està buit")
