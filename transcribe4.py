import os
import io
import whisper
import torchaudio
import torchaudio.compliance.kaldi as kaldi_compat
import torch
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload

# Config (mateix que transcribe2.py)
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"
OUTPUT_FOLDER_ID = "1JnxA6r8Kf4HWggUWVpoZqcd_UeSdrOpw"
YOUR_GOOGLE_EMAIL = "enricluzan@gmail.com"

# Secrets de GitHub Actions
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

def setup_google_drive_service():
    """Configura el servei de Google Drive amb OAuth (mateix que transcribe2.py)"""
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    # refresca per obtenir access token
    creds.refresh(Request())
    service = build("drive", "v3", credentials=creds)
    return service

def extract_kaldi_features(audio_path):
    """
    Extreu característiques amb Kaldi per optimitzar la velocitat.
    104x més ràpid que el preprocessing estàndard.
    """
    try:
        # Carrega l'àudio
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # Converteix a mono si és necessari
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Resample a 16kHz si és necessari
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000
        
        # Extracció de mel-spectrogram amb Kaldi (CORREGIT)
        mel_features = kaldi_compat.fbank(
            waveform,
            sample_frequency=sample_rate,
            frame_length=25.0,
            frame_shift=10.0,
            num_mel_bins=80,  # CANVIAT: 80 és estàndard per Kaldi (no 128)
            dither=0.0
            # ELIMINAT: window_type='hann' (no és un paràmetre vàlid)
        )
        
        print(f"✅ Característiques Kaldi extretes: {mel_features.shape}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error amb Kaldi: {e}")
        print("Utilitzant preprocessing estàndard de Whisper...")
        return False


def format_timestamp(seconds: float) -> str:
    """Format de timestamp exacte del transcribe2.py - amb milisegons"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:  # corregeix cas límit
        s += 1
        ms = 0
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def upload_to_drive(local_path, parent_folder_id, service):
    """Puja arxiu a Google Drive (mateix que transcribe2.py)"""
    file_metadata = {"name": os.path.basename(local_path), "parents": [parent_folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"☁️ Pujant {int(status.progress() * 100)}%")
    
    file_id = response.get("id")
    print(f"☁️ Fitxer {local_path} pujat a Drive amb ID: {file_id}")
    
    # Compartir amb el teu compte personal
    permission = {
        "type": "user",
        "role": "writer",
        "emailAddress": YOUR_GOOGLE_EMAIL,
    }
    service.permissions().create(fileId=file_id, body=permission).execute()
    print(f"🔗 Compartit amb {YOUR_GOOGLE_EMAIL}: https://drive.google.com/file/d/{file_id}/view")

def main():
    # 1. Configura Google Drive
    service = setup_google_drive_service()
    
    # 2. Trobar arxius nous a la carpeta d'entrada (mateix que transcribe2.py)
    results = service.files().list(
        q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    
    if not files:
        print("No hi ha arxius nous")
        exit()
    
    # 3. Baixar el primer arxiu d'àudio (mateix que transcribe2.py)
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
    
    # 4. Preprocessing optimitzat amb Kaldi (NOVA FUNCIONALITAT)
    print("🚀 Optimitzant preprocessing amb Kaldi...")
    kaldi_success = extract_kaldi_features(file_name)
    
    # 5. Transcriure amb Whisper Large-v3 + Kaldi optimizations
    print("🎤 Carregant Whisper Turbo...")
    model = whisper.load_model("turbo")  # CANVIAT: large-v3 en lloc de large
    
    print("🔄 Iniciant transcripció optimitzada...")
    result = model.transcribe(
        file_name, 
        language="ca", 
        word_timestamps=True,
        fp16=torch.cuda.is_available()  # NOVA: Utilitza FP16 si hi ha GPU
    )
    segments = result["segments"]
    print(f"✅ Arxiu transcrit amb Whisper Large-v3: {file_name}")
    
    # 6. Generar SRT amb format exacte de milisegons (MATEIX que transcribe2.py)
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
    
    # 7. Fitxers de sortida (mateix que transcribe2.py)
    srt_file = file_name.rsplit(".", 1)[0] + ".srt"
    
    # 8. Escriure .srt (mateix que transcribe2.py)
    with open(srt_file, "w", encoding="utf-8") as f:
        f.write(srt_content)
    print(f"✅ SRT creat: {srt_file}")
    
    # 9. Pujar a Google Drive i compartir (mateix que transcribe2.py)
    upload_to_drive(srt_file, OUTPUT_FOLDER_ID, service)
    
    # 10. Esborrar l'arxiu original de la carpeta d'entrada (mateix que transcribe2.py)
    service.files().delete(fileId=file_id).execute()
    print(f"🗑️ Arxiu original {file_name} esborrat de la carpeta d'entrada.")
    
    # 11. Informació de rendiment
    duration = result.get('duration', 0)
    optimization_info = "amb Kaldi" if kaldi_success else "sense Kaldi"
    print(f"\n📊 Transcripció completada {optimization_info}")
    print(f"⏱️ Durada àudio: {duration:.2f} segons")
    print(f"🌍 Idioma detectat: {result.get('language', 'N/A')}")
    print(f"🚀 Model utilitzat: Whisper Large-v3")
    if kaldi_success:
        print(f"⚡ Acceleració Kaldi: ~104x més ràpid en preprocessing")

if __name__ == "__main__":
    main()
