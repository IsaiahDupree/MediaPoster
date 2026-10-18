"""
OAuth Integration Manager
Phase 4: Handles OAuth flows for all social media platforms
"""
import os
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlencode
import json
import httpx


class OAuthProvider(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    FACEBOOK = "facebook"


@dataclass
class OAuthConfig:
    """OAuth configuration for a platform"""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]
    auth_url: str
    token_url: str
    refresh_url: Optional[str] = None
    revoke_url: Optional[str] = None
    extra_params: Dict[str, str] = field(default_factory=dict)


@dataclass
class OAuthToken:
    """OAuth token data"""
    provider: OAuthProvider
    access_token: str
    refresh_token: Optional[str]
    token_type: str
    expires_at: datetime
    scopes: List[str]
    user_id: Optional[str] = None
    username: Optional[str] = None
    raw_response: Dict = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> int:
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


@dataclass
class OAuthState:
    """State for OAuth flow"""
    state_key: str
    provider: OAuthProvider
    user_id: str
    redirect_after: str
    created_at: datetime
    code_verifier: Optional[str] = None  # For PKCE


class OAuthManager:
    """
    Manages OAuth flows for all social media platforms.
    Supports OAuth 2.0 with PKCE where required.
    """
    
    # Platform-specific configurations
    PLATFORM_CONFIGS = {
        OAuthProvider.TIKTOK: {
            'auth_url': 'https://www.tiktok.com/v2/auth/authorize/',
            'token_url': 'https://open.tiktokapis.com/v2/oauth/token/',
            'refresh_url': 'https://open.tiktokapis.com/v2/oauth/token/',
            'scopes': ['user.info.basic', 'video.publish', 'video.upload'],
            'uses_pkce': True,
        },
        OAuthProvider.INSTAGRAM: {
            'auth_url': 'https://api.instagram.com/oauth/authorize',
            'token_url': 'https://api.instagram.com/oauth/access_token',
            'refresh_url': 'https://graph.instagram.com/refresh_access_token',
            'scopes': ['user_profile', 'user_media'],
            'uses_pkce': False,
        },
        OAuthProvider.YOUTUBE: {
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'refresh_url': 'https://oauth2.googleapis.com/token',
            'revoke_url': 'https://oauth2.googleapis.com/revoke',
            'scopes': [
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/youtube.readonly',
            ],
            'uses_pkce': True,
        },
        OAuthProvider.TWITTER: {
            'auth_url': 'https://twitter.com/i/oauth2/authorize',
            'token_url': 'https://api.twitter.com/2/oauth2/token',
            'refresh_url': 'https://api.twitter.com/2/oauth2/token',
            'revoke_url': 'https://api.twitter.com/2/oauth2/revoke',
            'scopes': ['tweet.read', 'tweet.write', 'users.read', 'offline.access'],
            'uses_pkce': True,
        },
        OAuthProvider.LINKEDIN: {
            'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
            'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
            'refresh_url': 'https://www.linkedin.com/oauth/v2/accessToken',
            'scopes': ['r_liteprofile', 'w_member_social'],
            'uses_pkce': False,
        },
        OAuthProvider.THREADS: {
            'auth_url': 'https://threads.net/oauth/authorize',
            'token_url': 'https://graph.threads.net/oauth/access_token',
            'refresh_url': 'https://graph.threads.net/refresh_access_token',
            'scopes': ['threads_basic', 'threads_content_publish'],
            'uses_pkce': False,
        },
    }
    
    def __init__(self):
        self.configs: Dict[OAuthProvider, OAuthConfig] = {}
        self.tokens: Dict[str, OAuthToken] = {}  # user_id:provider -> token
        self.pending_states: Dict[str, OAuthState] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    def configure_provider(
        self,
        provider: OAuthProvider,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        extra_scopes: Optional[List[str]] = None
    ):
        """Configure OAuth for a specific provider"""
        platform_config = self.PLATFORM_CONFIGS.get(provider, {})
        
        scopes = platform_config.get('scopes', []).copy()
        if extra_scopes:
            scopes.extend(extra_scopes)
        
        self.configs[provider] = OAuthConfig(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            auth_url=platform_config.get('auth_url', ''),
            token_url=platform_config.get('token_url', ''),
            refresh_url=platform_config.get('refresh_url'),
            revoke_url=platform_config.get('revoke_url'),
        )
    
    def _generate_state(self) -> str:
        """Generate cryptographically secure state parameter"""
        return secrets.token_urlsafe(32)
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier"""
        return secrets.token_urlsafe(64)[:128]
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        import base64
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    
    def get_authorization_url(
        self,
        provider: OAuthProvider,
        user_id: str,
        redirect_after: str = '/'
    ) -> str:
        """
        Generate OAuth authorization URL for a provider.
        
        Args:
            provider: The OAuth provider
            user_id: Internal user ID for state management
            redirect_after: URL to redirect to after OAuth completion
        
        Returns:
            Authorization URL to redirect user to
        """
        if provider not in self.configs:
            raise ValueError(f"Provider {provider} not configured")
        
        config = self.configs[provider]
        platform_config = self.PLATFORM_CONFIGS.get(provider, {})
        
        # Generate state
        state_key = self._generate_state()
        
        # Generate PKCE if required
        code_verifier = None
        if platform_config.get('uses_pkce'):
            code_verifier = self._generate_code_verifier()
        
        # Store state
        self.pending_states[state_key] = OAuthState(
            state_key=state_key,
            provider=provider,
            user_id=user_id,
            redirect_after=redirect_after,
            created_at=datetime.utcnow(),
            code_verifier=code_verifier
        )
        
        # Build authorization URL
        params = {
            'client_id': config.client_id,
            'redirect_uri': config.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(config.scopes),
            'state': state_key,
        }
        
        # Add PKCE challenge if required
        if code_verifier:
            params['code_challenge'] = self._generate_code_challenge(code_verifier)
            params['code_challenge_method'] = 'S256'
        
        # Platform-specific params
        if provider == OAuthProvider.YOUTUBE:
            params['access_type'] = 'offline'
            params['prompt'] = 'consent'
        elif provider == OAuthProvider.TWITTER:
            params['code_challenge_method'] = 'S256'
        
        return f"{config.auth_url}?{urlencode(params)}"
    
    async def handle_callback(
        self,
        provider: OAuthProvider,
        code: str,
        state: str
    ) -> OAuthToken:
        """
        Handle OAuth callback and exchange code for tokens.
        
        Args:
            provider: The OAuth provider
            code: Authorization code from callback
            state: State parameter for validation
        
        Returns:
            OAuthToken with access and refresh tokens
        """
        # Validate state
        if state not in self.pending_states:
            raise ValueError("Invalid or expired state parameter")
        
        oauth_state = self.pending_states.pop(state)
        
        # Check state is not too old (10 minute expiry)
        if datetime.utcnow() - oauth_state.created_at > timedelta(minutes=10):
            raise ValueError("State parameter expired")
        
        if oauth_state.provider != provider:
            raise ValueError("Provider mismatch")
        
        config = self.configs[provider]
        
        # Exchange code for token
        token_data = {
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'code': code,
            'redirect_uri': config.redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        # Add PKCE verifier if used
        if oauth_state.code_verifier:
            token_data['code_verifier'] = oauth_state.code_verifier
        
        client = await self.get_client()
        
        # Platform-specific token request
        if provider == OAuthProvider.INSTAGRAM:
            # Instagram uses form data
            response = await client.post(config.token_url, data=token_data)
        else:
            # Most use JSON
            response = await client.post(
                config.token_url,
                json=token_data,
                headers={'Content-Type': 'application/json'}
            )
        
        if response.status_code != 200:
            raise ValueError(f"Token exchange failed: {response.text}")
        
        token_response = response.json()
        
        # Parse token response
        expires_in = token_response.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        token = OAuthToken(
            provider=provider,
            access_token=token_response['access_token'],
            refresh_token=token_response.get('refresh_token'),
            token_type=token_response.get('token_type', 'Bearer'),
            expires_at=expires_at,
            scopes=token_response.get('scope', '').split(' '),
            raw_response=token_response
        )
        
        # Store token
        token_key = f"{oauth_state.user_id}:{provider.value}"
        self.tokens[token_key] = token
        
        return token
    
    async def refresh_token(
        self,
        user_id: str,
        provider: OAuthProvider
    ) -> OAuthToken:
        """Refresh an expired access token"""
        token_key = f"{user_id}:{provider.value}"
        
        if token_key not in self.tokens:
            raise ValueError("No token found for user/provider")
        
        current_token = self.tokens[token_key]
        
        if not current_token.refresh_token:
            raise ValueError("No refresh token available")
        
        config = self.configs[provider]
        
        if not config.refresh_url:
            raise ValueError("Refresh not supported for this provider")
        
        refresh_data = {
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'refresh_token': current_token.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        client = await self.get_client()
        response = await client.post(config.refresh_url, json=refresh_data)
        
        if response.status_code != 200:
            raise ValueError(f"Token refresh failed: {response.text}")
        
        token_response = response.json()
        
        expires_in = token_response.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        new_token = OAuthToken(
            provider=provider,
            access_token=token_response['access_token'],
            refresh_token=token_response.get('refresh_token', current_token.refresh_token),
            token_type=token_response.get('token_type', 'Bearer'),
            expires_at=expires_at,
            scopes=current_token.scopes,
            user_id=current_token.user_id,
            username=current_token.username,
            raw_response=token_response
        )
        
        self.tokens[token_key] = new_token
        return new_token
    
    async def get_valid_token(
        self,
        user_id: str,
        provider: OAuthProvider
    ) -> OAuthToken:
        """Get a valid (non-expired) token, refreshing if necessary"""
        token_key = f"{user_id}:{provider.value}"
        
        if token_key not in self.tokens:
            raise ValueError("No token found for user/provider")
        
        token = self.tokens[token_key]
        
        # Refresh if expired or expiring soon (within 5 minutes)
        if token.expires_in_seconds < 300:
            if token.refresh_token:
                token = await self.refresh_token(user_id, provider)
            else:
                raise ValueError("Token expired and cannot be refreshed")
        
        return token
    
    async def revoke_token(
        self,
        user_id: str,
        provider: OAuthProvider
    ) -> bool:
        """Revoke tokens for a user/provider"""
        token_key = f"{user_id}:{provider.value}"
        
        if token_key not in self.tokens:
            return True  # Already revoked
        
        token = self.tokens[token_key]
        config = self.configs.get(provider)
        
        if config and config.revoke_url:
            try:
                client = await self.get_client()
                await client.post(
                    config.revoke_url,
                    data={'token': token.access_token}
                )
            except Exception:
                pass  # Best effort revocation
        
        del self.tokens[token_key]
        return True
    
    def get_connected_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of connected OAuth accounts for a user"""
        accounts = []
        
        for key, token in self.tokens.items():
            if key.startswith(f"{user_id}:"):
                accounts.append({
                    'provider': token.provider.value,
                    'username': token.username,
                    'connected': True,
                    'expires_at': token.expires_at.isoformat(),
                    'scopes': token.scopes,
                })
        
        return accounts


# Singleton instance
oauth_manager = OAuthManager()
