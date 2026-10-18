"""
Permission Gate Service
=======================
Role-based access control (RBAC) for MediaPoster features.

Implements TEST-018 permission requirements:
- User role-based permissions
- Feature flags
- Workspace permissions
- API key validation
- Platform account authorization
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from loguru import logger


class UserRole(Enum):
    """User roles with increasing permission levels"""
    VIEWER = "viewer"        # Read-only access
    EDITOR = "editor"        # Create/edit content
    ADMIN = "admin"          # Full access
    SUPER_ADMIN = "super_admin"  # System-level access


class Permission(Enum):
    """Granular permissions"""
    # Content permissions
    VIEW_CONTENT = "view_content"
    CREATE_CONTENT = "create_content"
    EDIT_CONTENT = "edit_content"
    DELETE_CONTENT = "delete_content"
    PUBLISH_CONTENT = "publish_content"

    # User management
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"

    # Settings
    VIEW_SETTINGS = "view_settings"
    CONFIGURE_SETTINGS = "configure_settings"

    # Analytics
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_ANALYTICS = "export_analytics"

    # Platform accounts
    CONNECT_PLATFORMS = "connect_platforms"
    MANAGE_PLATFORMS = "manage_platforms"

    # Templates
    CREATE_TEMPLATES = "create_templates"
    EDIT_TEMPLATES = "edit_templates"
    DELETE_TEMPLATES = "delete_templates"

    # API access
    API_READ = "api_read"
    API_WRITE = "api_write"
    API_DELETE = "api_delete"


class PermissionGate:
    """
    Permission gate for role-based access control.

    Usage:
        gate = PermissionGate()
        user = {"id": "user123", "role": UserRole.EDITOR}
        can_publish = await gate.can_publish(user)
    """

    def __init__(self):
        # Map roles to their permissions
        self._role_permissions = {
            UserRole.VIEWER: {
                Permission.VIEW_CONTENT,
                Permission.VIEW_USERS,
                Permission.VIEW_SETTINGS,
                Permission.VIEW_ANALYTICS,
                Permission.API_READ,
            },
            UserRole.EDITOR: {
                Permission.VIEW_CONTENT,
                Permission.CREATE_CONTENT,
                Permission.EDIT_CONTENT,
                Permission.PUBLISH_CONTENT,
                Permission.VIEW_ANALYTICS,
                Permission.CONNECT_PLATFORMS,
                Permission.CREATE_TEMPLATES,
                Permission.EDIT_TEMPLATES,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            UserRole.ADMIN: {
                Permission.VIEW_CONTENT,
                Permission.CREATE_CONTENT,
                Permission.EDIT_CONTENT,
                Permission.DELETE_CONTENT,
                Permission.PUBLISH_CONTENT,
                Permission.VIEW_USERS,
                Permission.MANAGE_USERS,
                Permission.VIEW_SETTINGS,
                Permission.CONFIGURE_SETTINGS,
                Permission.VIEW_ANALYTICS,
                Permission.EXPORT_ANALYTICS,
                Permission.CONNECT_PLATFORMS,
                Permission.MANAGE_PLATFORMS,
                Permission.CREATE_TEMPLATES,
                Permission.EDIT_TEMPLATES,
                Permission.DELETE_TEMPLATES,
                Permission.API_READ,
                Permission.API_WRITE,
                Permission.API_DELETE,
            },
            UserRole.SUPER_ADMIN: set(Permission),  # All permissions
        }

        # Feature flags (can be toggled at runtime)
        self._feature_flags: Dict[str, bool] = {
            "content_generation": True,
            "auto_publishing": True,
            "ai_templates": True,
            "analytics_export": True,
            "multi_platform": True,
            "dm_automation": False,  # Disabled by default
            "comment_automation": False,  # Disabled by default
        }

    def _get_user_role(self, user: Dict[str, Any]) -> UserRole:
        """Extract user role from user dict"""
        role = user.get("role")
        if isinstance(role, UserRole):
            return role
        if isinstance(role, str):
            return UserRole(role)
        # Default to viewer if no role specified
        logger.warning(f"No role found for user {user.get('id')}, defaulting to VIEWER")
        return UserRole.VIEWER

    def _has_permission(self, user: Dict[str, Any], permission: Permission) -> bool:
        """Check if user has specific permission"""
        role = self._get_user_role(user)
        permissions = self._role_permissions.get(role, set())
        return permission in permissions

    # Content permissions
    async def can_view_content(self, user: Dict[str, Any]) -> bool:
        """Check if user can view content"""
        return self._has_permission(user, Permission.VIEW_CONTENT)

    async def can_create_content(self, user: Dict[str, Any]) -> bool:
        """Check if user can create content"""
        return self._has_permission(user, Permission.CREATE_CONTENT)

    async def can_edit_content(self, user: Dict[str, Any]) -> bool:
        """Check if user can edit content"""
        return self._has_permission(user, Permission.EDIT_CONTENT)

    async def can_delete_content(self, user: Dict[str, Any]) -> bool:
        """Check if user can delete content"""
        return self._has_permission(user, Permission.DELETE_CONTENT)

    async def can_publish(self, user: Dict[str, Any]) -> bool:
        """Check if user can publish content"""
        return self._has_permission(user, Permission.PUBLISH_CONTENT)

    # User management permissions
    async def can_view_users(self, user: Dict[str, Any]) -> bool:
        """Check if user can view other users"""
        return self._has_permission(user, Permission.VIEW_USERS)

    async def can_manage_users(self, user: Dict[str, Any]) -> bool:
        """Check if user can manage users"""
        return self._has_permission(user, Permission.MANAGE_USERS)

    # Settings permissions
    async def can_view_settings(self, user: Dict[str, Any]) -> bool:
        """Check if user can view settings"""
        return self._has_permission(user, Permission.VIEW_SETTINGS)

    async def can_configure_settings(self, user: Dict[str, Any]) -> bool:
        """Check if user can configure settings"""
        return self._has_permission(user, Permission.CONFIGURE_SETTINGS)

    # Analytics permissions
    async def can_access_analytics(self, user: Dict[str, Any]) -> bool:
        """Check if user can access analytics"""
        return self._has_permission(user, Permission.VIEW_ANALYTICS)

    async def can_export_analytics(self, user: Dict[str, Any]) -> bool:
        """Check if user can export analytics"""
        return self._has_permission(user, Permission.EXPORT_ANALYTICS)

    # Platform permissions
    async def can_connect_platforms(self, user: Dict[str, Any]) -> bool:
        """Check if user can connect platform accounts"""
        return self._has_permission(user, Permission.CONNECT_PLATFORMS)

    async def can_manage_platforms(self, user: Dict[str, Any]) -> bool:
        """Check if user can manage platform accounts"""
        return self._has_permission(user, Permission.MANAGE_PLATFORMS)

    # Template permissions
    async def can_create_templates(self, user: Dict[str, Any]) -> bool:
        """Check if user can create templates"""
        return self._has_permission(user, Permission.CREATE_TEMPLATES)

    async def can_edit_templates(self, user: Dict[str, Any]) -> bool:
        """Check if user can edit templates"""
        return self._has_permission(user, Permission.EDIT_TEMPLATES)

    async def can_delete_templates(self, user: Dict[str, Any]) -> bool:
        """Check if user can delete templates"""
        return self._has_permission(user, Permission.DELETE_TEMPLATES)

    # Feature flag checks
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled"""
        return self._feature_flags.get(feature_name, False)

    def enable_feature(self, feature_name: str) -> None:
        """Enable a feature flag"""
        self._feature_flags[feature_name] = True
        logger.info(f"Feature enabled: {feature_name}")

    def disable_feature(self, feature_name: str) -> None:
        """Disable a feature flag"""
        self._feature_flags[feature_name] = False
        logger.info(f"Feature disabled: {feature_name}")

    def get_user_permissions(self, user: Dict[str, Any]) -> List[str]:
        """Get list of all permissions for a user"""
        role = self._get_user_role(user)
        permissions = self._role_permissions.get(role, set())
        return [p.value for p in permissions]

    def get_role_name(self, user: Dict[str, Any]) -> str:
        """Get the role name for a user"""
        role = self._get_user_role(user)
        return role.value
