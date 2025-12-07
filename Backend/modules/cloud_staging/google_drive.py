"""
Google Drive Uploader
Upload clips to Google Drive for staging and backup
"""
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
import json
import os


class GoogleDriveUploader:
    """Upload and manage files on Google Drive"""
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize Google Drive uploader
        
        Args:
            credentials_path: Path to Google credentials JSON
        """
        self.credentials_path = credentials_path or Path("./google_credentials.json")
        self.service = None
        self.folder_cache = {}
        
        logger.info("Google Drive uploader initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API
        
        Returns:
            True if authenticated successfully
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            
            creds = None
            token_path = Path('./token.pickle')
            
            # Load existing token
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh or get new token
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        logger.error(f"Credentials not found: {self.credentials_path}")
                        logger.info("Download credentials from Google Cloud Console")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save token
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.success("✓ Authenticated with Google Drive")
            return True
            
        except ImportError:
            logger.error("Google API packages not installed")
            logger.info("Install: pip install google-auth google-auth-oauthlib google-api-python-client")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name: Name of folder
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID or None if failed
        """
        if not self.service:
            logger.error("Not authenticated")
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.folder_cache[folder_name] = folder_id
            
            logger.success(f"✓ Created folder: {folder_name}")
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return None
    
    def get_or_create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> Optional[str]:
        """Get existing folder or create new one"""
        if folder_name in self.folder_cache:
            return self.folder_cache[folder_name]
        
        # Search for existing folder
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                self.folder_cache[folder_name] = folder_id
                logger.info(f"Found existing folder: {folder_name}")
                return folder_id
            
        except Exception as e:
            logger.warning(f"Folder search failed: {e}")
        
        # Create new folder
        return self.create_folder(folder_name, parent_id)
    
    def upload_file(
        self,
        file_path: Path,
        folder_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Upload file to Google Drive
        
        Args:
            file_path: Path to file
            folder_id: Destination folder ID
            description: File description
            
        Returns:
            File metadata or None if failed
        """
        if not self.service:
            logger.error("Not authenticated")
            return None
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_metadata = {
                'name': file_path.name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            if description:
                file_metadata['description'] = description
            
            media = MediaFileUpload(
                str(file_path),
                resumable=True
            )
            
            logger.info(f"Uploading {file_path.name}...")
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,size'
            ).execute()
            
            logger.success(f"✓ Uploaded: {file.get('name')}")
            logger.info(f"  Link: {file.get('webViewLink')}")
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'link': file.get('webViewLink'),
                'size': int(file.get('size', 0))
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None
    
    def upload_clip(
        self,
        clip_path: Path,
        metadata: Optional[Dict] = None,
        project_folder: str = "MediaPoster_Clips"
    ) -> Optional[Dict]:
        """
        Upload a generated clip with metadata
        
        Args:
            clip_path: Path to clip
            metadata: Clip metadata
            project_folder: Project folder name
            
        Returns:
            Upload result with link
        """
        if not self.service:
            if not self.authenticate():
                return None
        
        # Get or create project folder
        folder_id = self.get_or_create_folder(project_folder)
        if not folder_id:
            logger.error("Could not create project folder")
            return None
        
        # Create description from metadata
        description = self._build_description(metadata)
        
        # Upload clip
        result = self.upload_file(clip_path, folder_id, description)
        
        if result and metadata:
            # Also upload metadata JSON
            metadata_path = clip_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            self.upload_file(metadata_path, folder_id, "Clip metadata")
            metadata_path.unlink()  # Clean up temp file
        
        return result
    
    def _build_description(self, metadata: Optional[Dict]) -> str:
        """Build file description from metadata"""
        if not metadata:
            return "MediaPoster generated clip"
        
        parts = ["MediaPoster Clip"]
        
        if metadata.get('platform'):
            parts.append(f"Platform: {metadata['platform']}")
        
        if metadata.get('duration'):
            parts.append(f"Duration: {metadata['duration']:.1f}s")
        
        if metadata.get('hook_text'):
            parts.append(f"Hook: {metadata['hook_text']}")
        
        return " | ".join(parts)
    
    def list_files(
        self,
        folder_id: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """List files in folder"""
        if not self.service:
            return []
        
        try:
            query = "mimeType!='application/vnd.google-apps.folder'"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields='files(id,name,createdTime,size,webViewLink)'
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from Drive"""
        if not self.service:
            return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.success(f"✓ Deleted file: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def get_storage_quota(self) -> Dict:
        """Get Drive storage quota info"""
        if not self.service:
            return {}
        
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            total = int(quota.get('limit', 0))
            used = int(quota.get('usage', 0))
            remaining = total - used
            
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'remaining_gb': remaining / (1024**3),
                'percent_used': (used / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get quota: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("GOOGLE DRIVE UPLOADER")
    print("="*60)
    print("\nThis module uploads clips to Google Drive.")
    print("Requires: Google credentials JSON")
    print("\nSetup:")
    print("1. Create project in Google Cloud Console")
    print("2. Enable Google Drive API")
    print("3. Download credentials JSON")
    print("4. Save as 'google_credentials.json'")
    print("\nFor end-to-end testing, use test_phase4.py")
