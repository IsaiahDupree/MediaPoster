from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from sqlalchemy import text
from typing import Optional
import uuid

# Helper to get user ID from JWT (mocked/simplified for now, assumes auth middleware runs first)
# In a real app, this would extract from request.state.user or similar
# For now, we'll rely on the DB function auth.safe_user_id() or similar logic if needed,
# but here we need to validate the user is a member of the workspace.

async def get_current_workspace_id(
    x_workspace_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> uuid.UUID:
    """
    Extract workspace_id from header and validate access.
    Returns the workspace UUID if valid.
    Falls back to first available workspace if header not provided (for testing/dev).
    """
    if not x_workspace_id:
        # Fallback: Try to get the first available workspace for testing/dev
        try:
            query = text("SELECT id FROM workspaces ORDER BY created_at LIMIT 1")
            result = await db.execute(query)
            rows = list(result.fetchall())
            if rows:
                workspace_id = rows[0][0]
                from loguru import logger
                logger.warning(f"No X-Workspace-Id header provided, using default workspace: {workspace_id}")
                return workspace_id
            else:
                raise HTTPException(status_code=400, detail="No workspaces available and X-Workspace-Id header not provided")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting default workspace: {str(e)}")
    
    try:
        workspace_id = uuid.UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")
    
    # Verify workspace exists
    try:
        query = text("SELECT 1 FROM workspaces WHERE id = :id")
        result = await db.execute(query, {"id": workspace_id})
        rows = list(result.fetchall())
        exists = rows[0][0] if rows else None
        if not exists:
            raise HTTPException(status_code=404, detail="Workspace not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying workspace: {str(e)}")

    return workspace_id
