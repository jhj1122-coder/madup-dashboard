# drive_uploader.py
import io
import json
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_drive_service():
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, folder_name: str) -> str:
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    result = service.files().list(q=query, fields="files(id)").execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_screenshot(png_bytes: bytes, filename: str, folder_name: str) -> str:
    """PNG bytes를 Drive에 업로드하고 공개 IMAGE URL 반환"""
    service = _get_drive_service()
    folder_id = _get_or_create_folder(service, folder_name)

    media = MediaIoBaseUpload(io.BytesIO(png_bytes), mimetype="image/png")
    meta = {"name": filename, "parents": [folder_id]}
    file = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = file["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    return f"https://drive.google.com/uc?id={file_id}"
