"""
YTP-008: Thumbnail Upload to Google Drive
Uploads video thumbnails and assets to Google Drive.
"""
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GoogleDriveUploader:
    """
    Uploads files to Google Drive.

    Used for:
    - Video thumbnails
    - Generated blog images
    - Pipeline artifacts
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        self._service = None

    async def upload(
        self,
        file_path: str,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local file path
            filename: Override filename
            mime_type: MIME type (auto-detected if not provided)
            folder_id: Target folder ID (uses default if not provided)

        Returns:
            Dict with file_id and web_view_link
        """
        path = Path(file_path)
        name = filename or path.name
        target_folder = folder_id or self.folder_id

        if not mime_type:
            mime_type = self._guess_mime_type(path.suffix)

        try:
            service = self._get_service()
            if service is None:
                logger.warning("Google Drive service not available")
                return {"file_id": None, "error": "Service not available"}

            from googleapiclient.http import MediaFileUpload

            file_metadata = {"name": name}
            if target_folder:
                file_metadata["parents"] = [target_folder]

            media = MediaFileUpload(file_path, mimetype=mime_type)
            result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
            ).execute()

            logger.info("Uploaded %s to Drive: %s", name, result.get("id"))
            return {
                "file_id": result.get("id"),
                "web_view_link": result.get("webViewLink"),
                "filename": name,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Drive upload failed for %s: %s", file_path, e)
            return {"file_id": None, "error": str(e)}

    async def upload_thumbnail(
        self,
        thumbnail_url: str,
        video_id: str,
    ) -> Dict[str, Any]:
        """
        Download and upload a YouTube thumbnail to Drive.

        Args:
            thumbnail_url: URL of the thumbnail
            video_id: Video ID for naming

        Returns:
            Upload result dict
        """
        try:
            import aiohttp
            import tempfile

            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail_url) as resp:
                    if resp.status != 200:
                        return {"error": f"Failed to download thumbnail: {resp.status}"}

                    content = await resp.read()

            # Save to temp file
            tmp_path = Path(tempfile.gettempdir()) / f"thumb_{video_id}.jpg"
            tmp_path.write_bytes(content)

            result = await self.upload(
                str(tmp_path),
                filename=f"thumbnail_{video_id}.jpg",
                mime_type="image/jpeg",
            )

            # Cleanup temp file
            tmp_path.unlink(missing_ok=True)

            return result

        except Exception as e:
            logger.error("Thumbnail upload failed: %s", e)
            return {"error": str(e)}

    def _get_service(self):
        """Get or create Google Drive service."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/drive.file"],
            )
            self._service = build("drive", "v3", credentials=creds)
            return self._service

        except Exception as e:
            logger.warning("Google Drive service not available: %s", e)
            return None

    def _guess_mime_type(self, extension: str) -> str:
        """Guess MIME type from file extension."""
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".md": "text/markdown",
            ".txt": "text/plain",
        }
        return mime_map.get(extension.lower(), "application/octet-stream")
