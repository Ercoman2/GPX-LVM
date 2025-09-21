import os
import io
import whisper
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# CONFIGURACIÓ
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

# Autenticació Google Drive
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)

print("🔍 Buscant arxius a la carpeta d'entrada...")

# 1. Trobar arxius nous a la carpeta d'entrada
try:
    results = service.files().list(
        q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    print(f"✅ Trobats {len(files)} arxius")
except HttpError as e:
    print(f"❌ Error accedint a Google Drive: {e}")
    exit(1)

if not files:
    print("No hi ha arxius nous")
    exit()

# 2. Baixar el primer arxiu d'àudio
file_id = files[0]["id"]
file_name = files[0]["name"]
print(f"📁 Arxiu trobat: {file_name}")

try:
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    print(f"✅ Arxiu baixat: {file_name}")
except Exception as e:
    print(f"❌ Error baixant l'arxiu: {e}")
    exit(1)

# 3. Transcriure amb Whisper
print("🎙️ Iniciant transcripció...")
try:
    model = whisper.load_model("large")
    result = model.transcribe(file_name, language="ca", word_timestamps=True)
    segments = result["segments"]
    print(f"✅ Arxiu transcrit: {file_name}")
except Exception as e:
    print(f"❌ Error en la transcripció: {e}")
    exit(1)

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# 4. Generar SRT
print("📝 Generant fitxer SRT...")
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

# 5. Crear carpeta "transcript" i guardar
os.makedirs("transcript", exist_ok=True)
srt_file = f"transcript/{file_name.rsplit('.', 1)[0]}.srt"

with open(srt_file, "w", encoding="utf-8") as f:
    f.write(srt_content)

print(f"✅ SRT creat i guardat a: {srt_file}")

# 6. Netejar fitxer local
try:
    os.remove(file_name)
    print(f"🧹 Fitxer local {file_name} esborrat del runner.")
except Exception as e:
    print(f"⚠️ No s'ha pogut esborrar el fitxer local: {e}")

print("✅ Transcripció completada i guardada a la carpeta 'transcript/'.")
