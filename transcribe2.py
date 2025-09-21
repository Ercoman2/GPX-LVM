import os
import io
import whisper
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# CONFIGURACIÓ
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

# Autenticació Google Drive (només per baixar i esborrar)
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
creds = Credentials.from_service_account_info(
    service_account_info,
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
model = whisper.load_model("large")
result = model.transcribe(file_name, language="ca", word_timestamps=True)
segments = result["segments"]
print(f"✅ Arxiu transcrit: {file_name}")

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:  # corregeix cas límit
        s += 1
        ms = 0
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# 4. Generar SRT
srt_lines = []
for i, seg in enumerate(segments, start=1):
    start_ts = format_timestamp(seg["start"])
    end_ts = format_timestamp(seg["end"])
    text = seg["text"].lstrip()
    srt_lines.append(f"{i}")
    srt_lines.append(f"{start_ts} --> {end_ts}")
    srt_lines.append(text)
    srt_lines.append("")

srt_content = "\n".join(srt_lines)

# 5. Crear carpeta "transcript" si no existeix
os.makedirs("transcript", exist_ok=True)

# Guardar fitxer SRT a la carpeta transcript
srt_file = f"transcript/{file_name.rsplit('.', 1)[0]}.srt"

with open(srt_file, "w", encoding="utf-8") as f:
    f.write(srt_content)

print(f"✅ SRT creat i guardat a: {srt_file}")

# 6. Esborrar l'arxiu original de la carpeta d'entrada
service.files().delete(fileId=file_id).execute()
print(f"🗑️ Arxiu original {file_name} esborrat de la carpeta d'entrada.")

print("✅ Transcripció completada i guardada a la carpeta 'transcript/'.")
