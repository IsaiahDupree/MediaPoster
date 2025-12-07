"""
Workspace Management API Endpoints
Create, read, update, delete workspaces and manage members
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from middleware.workspace_context import get_current_workspace_id

router = APIRouter()

# --- Pydantic Models ---

class WorkspaceCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    settings: Optional[dict] = None

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[dict] = None

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    settings: dict
    role: str  # user's role in this workspace
    created_at: datetime
    updated_at: datetime

class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime

# --- Endpoints ---

@router.get("/", response_model=List[WorkspaceResponse])
async def list_my_workspaces(db: AsyncSession = Depends(get_db)):
    """List all workspaces the current user has access to"""
    try:
        query = text("""
            SELECT 
                w.id, 
                w.name, 
                w.slug, 
                w.description, 
                w.settings,
                w.created_at,
                w.updated_at,
                wm.role
            FROM workspaces w
            JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE wm.user_id = public.safe_user_id()
            AND w.deleted_at IS NULL
            ORDER BY w.created_at DESC
        """)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        return [
            WorkspaceResponse(
                id=row.id,
                name=row.name,
                slug=row.slug,
                description=row.description,
                settings=row.settings or {},
                role=row.role,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(e)}")


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(workspace: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new workspace (user becomes owner)"""
    try:
        # Check slug uniqueness
        slug_check = text("SELECT 1 FROM workspaces WHERE slug = :slug")
        existing = await db.execute(slug_check, {"slug": workspace.slug})
        if existing.scalar():
            raise HTTPException(status_code=400, detail="Slug already exists")
        
        workspace_id = uuid4()
        
        # Insert workspace
        insert_workspace = text("""
            INSERT INTO workspaces (id, name, slug, description, settings, created_at, updated_at)
            VALUES (:id, :name, :slug, :description, :settings, NOW(), NOW())
            RETURNING id, created_at, updated_at
        """)
        
        result = await db.execute(insert_workspace, {
            "id": workspace_id,
            "name": workspace.name,
            "slug": workspace.slug,
            "description": workspace.description,
            "settings": workspace.settings or {}
        })
        
        row = result.fetchone()
        
        # Add current user as owner
        insert_member = text("""
            INSERT INTO workspace_members (workspace_id, user_id, role, joined_at)
            VALUES (:workspace_id, public.safe_user_id(), 'owner', NOW())
        """)
        
        await db.execute(insert_member, {"workspace_id": workspace_id})
        await db.commit()
        
        return WorkspaceResponse(
            id=row.id,
            name=workspace.name,
            slug=workspace.slug,
            description=workspace.description,
            settings=workspace.settings or {},
            role="owner",
            created_at=row.created_at,
            updated_at=row.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {str(e)}")


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get workspace details (user must be a member)"""
    try:
        query = text("""
            SELECT 
                w.id, 
                w.name, 
                w.slug, 
                w.description, 
                w.settings,
                w.created_at,
                w.updated_at,
                wm.role
            FROM workspaces w
            JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE w.id = :workspace_id 
            AND wm.user_id = public.safe_user_id()
            AND w.deleted_at IS NULL
        """)
        
        result = await db.execute(query, {"workspace_id": workspace_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return WorkspaceResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            settings=row.settings or {},
            role=row.role,
            created_at=row.created_at,
            updated_at=row.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {str(e)}")


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID, 
    updates: WorkspaceUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update workspace settings (admin or owner only)"""
    try:
        # Check user role
        role_check = text("""
            SELECT role FROM workspace_members 
            WHERE workspace_id = :workspace_id 
            AND user_id = public.safe_user_id()
        """)
        role_result = await db.execute(role_check, {"workspace_id": workspace_id})
        role_row = role_result.fetchone()
        
        if not role_row or role_row.role not in ['owner', 'admin']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Build update query dynamically
        update_fields = []
        params = {"workspace_id": workspace_id}
        
        if updates.name is not None:
            update_fields.append("name = :name")
            params["name"] = updates.name
        if updates.slug is not None:
            update_fields.append("slug = :slug")
            params["slug"] = updates.slug
        if updates.description is not None:
            update_fields.append("description = :description")
            params["description"] = updates.description
        if updates.settings is not None:
            update_fields.append("settings = :settings")
            params["settings"] = updates.settings
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        update_fields.append("updated_at = NOW()")
        
        query = text(f"""
            UPDATE workspaces 
            SET {', '.join(update_fields)}
            WHERE id = :workspace_id
            RETURNING id, name, slug, description, settings, created_at, updated_at
        """)
        
        result = await db.execute(query, params)
        row = result.fetchone()
        await db.commit()
        
        if not row:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return WorkspaceResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            settings=row.settings or {},
            role=role_row.role,
            created_at=row.created_at,
            updated_at=row.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update workspace: {str(e)}")


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete workspace (owner only)"""
    try:
        # Check user is owner
        role_check = text("""
            SELECT role FROM workspace_members 
            WHERE workspace_id = :workspace_id 
            AND user_id = public.safe_user_id()
        """)
        role_result = await db.execute(role_check, {"workspace_id": workspace_id})
        role_row = role_result.fetchone()
        
        if not role_row or role_row.role != 'owner':
            raise HTTPException(status_code=403, detail="Only workspace owners can delete workspaces")
        
        # Soft delete
        delete_query = text("""
            UPDATE workspaces 
            SET deleted_at = NOW()
            WHERE id = :workspace_id
        """)
        
        await db.execute(delete_query, {"workspace_id": workspace_id})
        await db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {str(e)}")


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all members of a workspace (must be a member)"""
    try:
        # Verify user has access to workspace
        verify_query = text("""
            SELECT 1 FROM workspace_members 
            WHERE workspace_id = :workspace_id 
            AND user_id = public.safe_user_id()
        """)
        verify_result = await db.execute(verify_query, {"workspace_id": workspace_id})
        if not verify_result.scalar():
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get members
        members_query = text("""
            SELECT id, workspace_id, user_id, role, joined_at
            FROM workspace_members
            WHERE workspace_id = :workspace_id
            ORDER BY joined_at ASC
        """)
        
        result = await db.execute(members_query, {"workspace_id": workspace_id})
        rows = result.fetchall()
        
        return [
            WorkspaceMemberResponse(
                id=row.id,
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                role=row.role,
                joined_at=row.joined_at
            )
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list members: {str(e)}")
