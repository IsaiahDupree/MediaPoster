"""
YTP-006: Google Sheet Sync
Syncs pipeline data (videos processed, transcripts, analytics) to Google Sheets.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class SheetRow:
    """A row of data to sync to Google Sheets."""
    video_id: str
    title: str
    channel: str
    processed_at: str
    transcript_length: int = 0
    summary: str = ""
    blog_url: str = ""
    social_posts: int = 0
    status: str = "completed"


class GoogleSheetsSync:
    """
    Syncs YouTube pipeline data to Google Sheets.

    Maintains a log of all processed videos with their status,
    transcript summaries, and distribution results.
    """

    def __init__(
        self,
        spreadsheet_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID", "")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self._service = None

    async def sync_row(self, row: SheetRow) -> bool:
        """
        Append a row to the Google Sheet.

        Args:
            row: SheetRow data to append

        Returns:
            True if successful
        """
        values = [
            row.video_id,
            row.title,
            row.channel,
            row.processed_at,
            row.transcript_length,
            row.summary[:200],
            row.blog_url,
            row.social_posts,
            row.status,
        ]

        try:
            service = self._get_service()
            if service is None:
                logger.warning("Google Sheets service not available")
                return False

            body = {"values": [values]}
            service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Pipeline Log!A:I",
                valueInputOption="RAW",
                body=body,
            ).execute()

            logger.info("Synced row for video %s to Google Sheet", row.video_id)
            return True

        except Exception as e:
            logger.error("Failed to sync to Google Sheet: %s", e)
            return False

    async def sync_batch(self, rows: List[SheetRow]) -> int:
        """Sync multiple rows. Returns count of successful syncs."""
        success = 0
        for row in rows:
            if await self.sync_row(row):
                success += 1
        return success

    async def get_processed_video_ids(self) -> List[str]:
        """Get list of already-processed video IDs from the sheet."""
        try:
            service = self._get_service()
            if service is None:
                return []

            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Pipeline Log!A:A",
            ).execute()

            values = result.get("values", [])
            return [row[0] for row in values if row]

        except Exception as e:
            logger.error("Failed to get processed video IDs: %s", e)
            return []

    def _get_service(self):
        """Get or create Google Sheets service."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self._service = build("sheets", "v4", credentials=creds)
            return self._service

        except Exception as e:
            logger.warning("Google Sheets service not available: %s", e)
            return None
