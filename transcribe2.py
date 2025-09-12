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
segments = result["segments"]
print(f"✅ Arxiu transcrit: {file_name}")

def format_timestamp(seconds: float):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# 4. Generar SRT i TXT
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
print(f"✅ Arxiu transcrit: {file_name}")

# Fitxers de sortida
srt_file = file_name.rsplit(".", 1)[0] + ".srt"
txt_file = file_name.rsplit(".", 1)[0] + "_debug.txt"

# Escriure .srt
with open(srt_file, "w", encoding="utf-8") as f:
    f.write(srt_content)

# Escriure debug complet (text + segments)
with open(txt_file, "w", encoding="utf-8") as f:
    f.write(result["text"] + "\n\n")
    for seg in segments:
        f.write(f"{seg}\n")

print(f"✅ SRT creat: {srt_file}")
print(f"✅ Debug creat: {txt_file}")

# 5. Pujar a Google Drive
def upload_to_drive(local_path, parent_folder_id):
    file_metadata = {"name": os.path.basename(local_path), "parents": [parent_folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    print(f"☁️ Fitxer {local_path} pujat a Drive amb ID: {uploaded.get('id')}")

upload_to_drive(srt_file, OUTPUT_FOLDER_ID)
upload_to_drive(txt_file, OUTPUT_FOLDER_ID)
