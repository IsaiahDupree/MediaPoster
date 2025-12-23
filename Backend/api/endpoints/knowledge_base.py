"""
Knowledge Base API
==================
Endpoints for managing rules, templates, constraints, and playbooks.
These are the learnings produced by Experiments and consumed by Narrative Builder.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
import logging
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

def get_db_connection():
    """Get a database connection from the engine."""
    try:
        engine = get_engine()
        return engine.connect()
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}")
        return None

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class RuleConditions(BaseModel):
    platform: Optional[List[str]] = None
    niche: Optional[List[str]] = None
    format: Optional[List[str]] = None
    hook_type: Optional[str] = None
    length_range: Optional[List[int]] = None  # [min, max] seconds


class RuleCreate(BaseModel):
    rule_type: str = Field(..., description="Type: hook, format, timing, caption, cta, thumbnail")
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: RuleConditions = Field(default_factory=RuleConditions)
    recommendation: str
    expected_lift: Optional[float] = None
    confidence: Optional[float] = None
    sample_size: Optional[int] = None
    source_experiment_id: Optional[str] = None


class RuleResponse(BaseModel):
    id: str
    rule_type: str
    name: Optional[str]
    description: Optional[str]
    conditions: Dict[str, Any]
    recommendation: str
    expected_lift: Optional[float]
    confidence: Optional[float]
    sample_size: Optional[int]
    last_validated: Optional[datetime]
    status: str
    created_at: datetime


class TemplateCreate(BaseModel):
    template_type: str = Field(..., description="Type: hook, caption, cta, thumbnail_text")
    name: str
    description: Optional[str] = None
    content: str
    variables: List[str] = Field(default_factory=list)
    best_for: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    id: str
    template_type: str
    name: str
    description: Optional[str]
    content: str
    variables: List[str]
    performance_score: Optional[float]
    usage_count: int
    status: str
    created_at: datetime


class ConstraintCreate(BaseModel):
    constraint_type: str = Field(..., description="Type: fatigue, cooldown, frequency, timing")
    name: str
    description: Optional[str] = None
    scope: str = Field(..., description="Scope: platform, topic, format, template, global")
    scope_value: Optional[str] = None
    threshold_value: float
    threshold_unit: Optional[str] = None
    window_days: Optional[int] = None
    priority: int = 50


class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    use_case: Optional[str] = None
    rule_ids: List[str] = Field(default_factory=list)
    template_ids: List[str] = Field(default_factory=list)
    constraint_ids: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# HELPER: Ensure tables exist
# =============================================================================

async def ensure_kb_tables():
    """Create KB tables if they don't exist."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Check if kb_rules exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'kb_rules'
                )
            """)).fetchone()
            
            if not result[0]:
                # Tables will be created by migration, create minimal versions for now
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS kb_rules (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        rule_type VARCHAR(50) NOT NULL,
                        name VARCHAR(255),
                        description TEXT,
                        conditions JSONB DEFAULT '{}'::jsonb,
                        recommendation TEXT NOT NULL,
                        expected_lift DECIMAL(5,2),
                        confidence DECIMAL(3,2),
                        sample_size INTEGER,
                        last_validated TIMESTAMPTZ,
                        source_experiment_id UUID,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS kb_templates (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        template_type VARCHAR(50) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        content TEXT NOT NULL,
                        variables JSONB DEFAULT '[]'::jsonb,
                        performance_score DECIMAL(5,2),
                        usage_count INTEGER DEFAULT 0,
                        best_for JSONB DEFAULT '{}'::jsonb,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS kb_constraints (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        constraint_type VARCHAR(50) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        scope VARCHAR(50) NOT NULL,
                        scope_value VARCHAR(255),
                        threshold_value DECIMAL(10,2) NOT NULL,
                        threshold_unit VARCHAR(50),
                        window_days INTEGER,
                        priority INTEGER DEFAULT 50,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS kb_playbooks (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        use_case VARCHAR(50),
                        rule_ids UUID[] DEFAULT '{}',
                        template_ids UUID[] DEFAULT '{}',
                        constraint_ids UUID[] DEFAULT '{}',
                        config JSONB DEFAULT '{}'::jsonb,
                        usage_count INTEGER DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                
                conn.commit()
                logger.info("Created KB tables")
    except Exception as e:
        logger.error(f"Error ensuring KB tables: {e}")


# =============================================================================
# RULES ENDPOINTS
# =============================================================================

@router.get("/kb/rules")
async def list_rules(
    rule_type: Optional[str] = None,
    status: str = "active",
    min_confidence: Optional[float] = None,
    limit: int = 50
):
    """List knowledge base rules with optional filtering."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        return {"rules": [], "count": 0}
    
    try:
        query = """
            SELECT id, rule_type, name, description, conditions, recommendation,
                   expected_lift, confidence, sample_size, last_validated,
                   source_experiment_id, status, created_at
            FROM kb_rules
            WHERE status = :status
        """
        params = {"status": status, "limit": limit}
        
        if rule_type:
            query += " AND rule_type = :rule_type"
            params["rule_type"] = rule_type
        
        if min_confidence:
            query += " AND confidence >= :min_confidence"
            params["min_confidence"] = min_confidence
        
        query += " ORDER BY confidence DESC NULLS LAST, created_at DESC LIMIT :limit"
        
        result = conn.execute(text(query), params).fetchall()
        
        rules = []
        for row in result:
            rules.append({
                "id": str(row[0]),
                "rule_type": row[1],
                "name": row[2],
                "description": row[3],
                "conditions": row[4] or {},
                "recommendation": row[5],
                "expected_lift": float(row[6]) if row[6] else None,
                "confidence": float(row[7]) if row[7] else None,
                "sample_size": row[8],
                "last_validated": row[9].isoformat() if row[9] else None,
                "source_experiment_id": str(row[10]) if row[10] else None,
                "status": row[11],
                "created_at": row[12].isoformat() if row[12] else None
            })
        
        return {"rules": rules, "count": len(rules)}
    
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        return {"rules": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/kb/rules")
async def create_rule(rule: RuleCreate):
    """Create a new knowledge base rule."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        rule_id = str(uuid.uuid4())
        
        conn.execute(text("""
            INSERT INTO kb_rules (id, rule_type, name, description, conditions, 
                                  recommendation, expected_lift, confidence, 
                                  sample_size, source_experiment_id)
            VALUES (:id, :rule_type, :name, :description, :conditions::jsonb,
                    :recommendation, :expected_lift, :confidence,
                    :sample_size, :source_experiment_id)
        """), {
            "id": rule_id,
            "rule_type": rule.rule_type,
            "name": rule.name,
            "description": rule.description,
            "conditions": rule.conditions.model_dump_json() if rule.conditions else "{}",
            "recommendation": rule.recommendation,
            "expected_lift": rule.expected_lift,
            "confidence": rule.confidence,
            "sample_size": rule.sample_size,
            "source_experiment_id": rule.source_experiment_id
        })
        conn.commit()
        
        logger.info(f"Created rule {rule_id}: {rule.name or rule.rule_type}")
        
        return {
            "id": rule_id,
            "rule_type": rule.rule_type,
            "name": rule.name,
            "status": "active",
            "message": "Rule created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/kb/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get a specific rule by ID."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        result = conn.execute(text("""
            SELECT id, rule_type, name, description, conditions, recommendation,
                   expected_lift, confidence, sample_size, last_validated,
                   source_experiment_id, status, created_at, updated_at
            FROM kb_rules WHERE id = :id
        """), {"id": rule_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {
            "id": str(result[0]),
            "rule_type": result[1],
            "name": result[2],
            "description": result[3],
            "conditions": result[4] or {},
            "recommendation": result[5],
            "expected_lift": float(result[6]) if result[6] else None,
            "confidence": float(result[7]) if result[7] else None,
            "sample_size": result[8],
            "last_validated": result[9].isoformat() if result[9] else None,
            "source_experiment_id": str(result[10]) if result[10] else None,
            "status": result[11],
            "created_at": result[12].isoformat() if result[12] else None,
            "updated_at": result[13].isoformat() if result[13] else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.patch("/kb/rules/{rule_id}/deprecate")
async def deprecate_rule(rule_id: str):
    """Mark a rule as deprecated."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        conn.execute(text("""
            UPDATE kb_rules SET status = 'deprecated', updated_at = NOW()
            WHERE id = :id
        """), {"id": rule_id})
        conn.commit()
        
        return {"id": rule_id, "status": "deprecated", "message": "Rule deprecated"}
    
    except Exception as e:
        logger.error(f"Error deprecating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# TEMPLATES ENDPOINTS
# =============================================================================

@router.get("/kb/templates")
async def list_templates(
    template_type: Optional[str] = None,
    status: str = "active",
    limit: int = 50
):
    """List knowledge base templates."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        return {"templates": [], "count": 0}
    
    try:
        query = """
            SELECT id, template_type, name, description, content, variables,
                   performance_score, usage_count, best_for, status, created_at
            FROM kb_templates
            WHERE status = :status
        """
        params = {"status": status, "limit": limit}
        
        if template_type:
            query += " AND template_type = :template_type"
            params["template_type"] = template_type
        
        query += " ORDER BY performance_score DESC NULLS LAST, usage_count DESC LIMIT :limit"
        
        result = conn.execute(text(query), params).fetchall()
        
        templates = []
        for row in result:
            templates.append({
                "id": str(row[0]),
                "template_type": row[1],
                "name": row[2],
                "description": row[3],
                "content": row[4],
                "variables": row[5] or [],
                "performance_score": float(row[6]) if row[6] else None,
                "usage_count": row[7] or 0,
                "best_for": row[8] or {},
                "status": row[9],
                "created_at": row[10].isoformat() if row[10] else None
            })
        
        return {"templates": templates, "count": len(templates)}
    
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return {"templates": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/kb/templates")
async def create_template(template: TemplateCreate):
    """Create a new template."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        template_id = str(uuid.uuid4())
        import json
        
        conn.execute(text("""
            INSERT INTO kb_templates (id, template_type, name, description, content, 
                                      variables, best_for)
            VALUES (:id, :template_type, :name, :description, :content,
                    :variables::jsonb, :best_for::jsonb)
        """), {
            "id": template_id,
            "template_type": template.template_type,
            "name": template.name,
            "description": template.description,
            "content": template.content,
            "variables": json.dumps(template.variables),
            "best_for": json.dumps(template.best_for or {})
        })
        conn.commit()
        
        logger.info(f"Created template {template_id}: {template.name}")
        
        return {
            "id": template_id,
            "template_type": template.template_type,
            "name": template.name,
            "status": "active",
            "message": "Template created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# CONSTRAINTS ENDPOINTS
# =============================================================================

@router.get("/kb/constraints")
async def list_constraints(
    constraint_type: Optional[str] = None,
    scope: Optional[str] = None,
    status: str = "active"
):
    """List knowledge base constraints."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        return {"constraints": [], "count": 0}
    
    try:
        query = """
            SELECT id, constraint_type, name, description, scope, scope_value,
                   threshold_value, threshold_unit, window_days, priority, status, created_at
            FROM kb_constraints
            WHERE status = :status
        """
        params = {"status": status}
        
        if constraint_type:
            query += " AND constraint_type = :constraint_type"
            params["constraint_type"] = constraint_type
        
        if scope:
            query += " AND scope = :scope"
            params["scope"] = scope
        
        query += " ORDER BY priority DESC, created_at DESC"
        
        result = conn.execute(text(query), params).fetchall()
        
        constraints = []
        for row in result:
            constraints.append({
                "id": str(row[0]),
                "constraint_type": row[1],
                "name": row[2],
                "description": row[3],
                "scope": row[4],
                "scope_value": row[5],
                "threshold_value": float(row[6]) if row[6] else None,
                "threshold_unit": row[7],
                "window_days": row[8],
                "priority": row[9],
                "status": row[10],
                "created_at": row[11].isoformat() if row[11] else None
            })
        
        return {"constraints": constraints, "count": len(constraints)}
    
    except Exception as e:
        logger.error(f"Error listing constraints: {e}")
        return {"constraints": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/kb/constraints")
async def create_constraint(constraint: ConstraintCreate):
    """Create a new constraint."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        constraint_id = str(uuid.uuid4())
        
        conn.execute(text("""
            INSERT INTO kb_constraints (id, constraint_type, name, description, scope,
                                        scope_value, threshold_value, threshold_unit,
                                        window_days, priority)
            VALUES (:id, :constraint_type, :name, :description, :scope,
                    :scope_value, :threshold_value, :threshold_unit,
                    :window_days, :priority)
        """), {
            "id": constraint_id,
            "constraint_type": constraint.constraint_type,
            "name": constraint.name,
            "description": constraint.description,
            "scope": constraint.scope,
            "scope_value": constraint.scope_value,
            "threshold_value": constraint.threshold_value,
            "threshold_unit": constraint.threshold_unit,
            "window_days": constraint.window_days,
            "priority": constraint.priority
        })
        conn.commit()
        
        return {
            "id": constraint_id,
            "constraint_type": constraint.constraint_type,
            "name": constraint.name,
            "status": "active",
            "message": "Constraint created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating constraint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# PLAYBOOKS ENDPOINTS
# =============================================================================

@router.get("/kb/playbooks")
async def list_playbooks(
    use_case: Optional[str] = None,
    status: str = "active"
):
    """List knowledge base playbooks."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        return {"playbooks": [], "count": 0}
    
    try:
        query = """
            SELECT id, name, description, use_case, rule_ids, template_ids,
                   constraint_ids, config, usage_count, status, created_at
            FROM kb_playbooks
            WHERE status = :status
        """
        params = {"status": status}
        
        if use_case:
            query += " AND use_case = :use_case"
            params["use_case"] = use_case
        
        query += " ORDER BY usage_count DESC, created_at DESC"
        
        result = conn.execute(text(query), params).fetchall()
        
        playbooks = []
        for row in result:
            playbooks.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "use_case": row[3],
                "rule_ids": [str(r) for r in (row[4] or [])],
                "template_ids": [str(t) for t in (row[5] or [])],
                "constraint_ids": [str(c) for c in (row[6] or [])],
                "config": row[7] or {},
                "usage_count": row[8] or 0,
                "status": row[9],
                "created_at": row[10].isoformat() if row[10] else None
            })
        
        return {"playbooks": playbooks, "count": len(playbooks)}
    
    except Exception as e:
        logger.error(f"Error listing playbooks: {e}")
        return {"playbooks": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/kb/playbooks")
async def create_playbook(playbook: PlaybookCreate):
    """Create a new playbook."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        playbook_id = str(uuid.uuid4())
        import json
        
        conn.execute(text("""
            INSERT INTO kb_playbooks (id, name, description, use_case, rule_ids,
                                      template_ids, constraint_ids, config)
            VALUES (:id, :name, :description, :use_case, :rule_ids::uuid[],
                    :template_ids::uuid[], :constraint_ids::uuid[], :config::jsonb)
        """), {
            "id": playbook_id,
            "name": playbook.name,
            "description": playbook.description,
            "use_case": playbook.use_case,
            "rule_ids": "{" + ",".join(playbook.rule_ids) + "}" if playbook.rule_ids else "{}",
            "template_ids": "{" + ",".join(playbook.template_ids) + "}" if playbook.template_ids else "{}",
            "constraint_ids": "{" + ",".join(playbook.constraint_ids) + "}" if playbook.constraint_ids else "{}",
            "config": json.dumps(playbook.config)
        })
        conn.commit()
        
        return {
            "id": playbook_id,
            "name": playbook.name,
            "use_case": playbook.use_case,
            "status": "active",
            "message": "Playbook created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# SEED DATA ENDPOINT
# =============================================================================

@router.post("/kb/seed-demo-data")
async def seed_demo_data():
    """Seed demo knowledge base data for testing."""
    await ensure_kb_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        import json
        
        # Seed demo rules
        demo_rules = [
            {
                "rule_type": "hook",
                "name": "Pain Point Cold Open",
                "description": "Start with a specific pain point to increase hook rate",
                "conditions": {"platform": ["tiktok", "instagram"], "format": ["vertical"]},
                "recommendation": "Open with 'Are you still struggling with...' or similar pain-focused hook",
                "expected_lift": 34.0,
                "confidence": 0.92,
                "sample_size": 2500
            },
            {
                "rule_type": "caption",
                "name": "Short Caption Wins",
                "description": "Captions under 100 chars perform better",
                "conditions": {"platform": ["tiktok", "instagram"]},
                "recommendation": "Keep captions punchy and under 100 characters",
                "expected_lift": 22.0,
                "confidence": 0.88,
                "sample_size": 1800
            },
            {
                "rule_type": "timing",
                "name": "Evening Prime Time",
                "description": "Posts between 6-9 PM get higher engagement",
                "conditions": {"platform": ["tiktok", "instagram", "youtube"]},
                "recommendation": "Schedule posts for 6-9 PM in target audience timezone",
                "expected_lift": 18.0,
                "confidence": 0.85,
                "sample_size": 3200
            },
            {
                "rule_type": "format",
                "name": "15-22 Second Sweet Spot",
                "description": "Videos in this length range have best completion rates",
                "conditions": {"platform": ["tiktok", "instagram"], "length_range": [15, 22]},
                "recommendation": "Aim for 15-22 second videos for optimal completion",
                "expected_lift": 28.0,
                "confidence": 0.90,
                "sample_size": 2100
            }
        ]
        
        for rule in demo_rules:
            conn.execute(text("""
                INSERT INTO kb_rules (rule_type, name, description, conditions, 
                                      recommendation, expected_lift, confidence, sample_size)
                VALUES (:rule_type, :name, :description, :conditions::jsonb,
                        :recommendation, :expected_lift, :confidence, :sample_size)
                ON CONFLICT DO NOTHING
            """), {
                **rule,
                "conditions": json.dumps(rule["conditions"])
            })
        
        # Seed demo templates
        demo_templates = [
            {
                "template_type": "hook",
                "name": "Pain Point Hook",
                "content": "Are you still struggling with {{pain_point}}? Here's what changed everything...",
                "variables": ["pain_point"],
                "best_for": {"niche": ["business", "productivity"]}
            },
            {
                "template_type": "hook",
                "name": "Question Hook",
                "content": "Why do 90% of {{subject}} fail at {{goal}}?",
                "variables": ["subject", "goal"],
                "best_for": {"niche": ["education", "business"]}
            },
            {
                "template_type": "cta",
                "name": "Comment Keyword CTA",
                "content": "Comment '{{keyword}}' and I'll send you the full guide",
                "variables": ["keyword"],
                "best_for": {"goal": "engagement"}
            },
            {
                "template_type": "caption",
                "name": "Minimal Caption",
                "content": "{{hook}} 👇",
                "variables": ["hook"],
                "best_for": {"platform": ["tiktok"]}
            }
        ]
        
        for template in demo_templates:
            conn.execute(text("""
                INSERT INTO kb_templates (template_type, name, content, variables, best_for)
                VALUES (:template_type, :name, :content, :variables::jsonb, :best_for::jsonb)
                ON CONFLICT DO NOTHING
            """), {
                **template,
                "variables": json.dumps(template["variables"]),
                "best_for": json.dumps(template["best_for"])
            })
        
        conn.commit()
        
        return {
            "message": "Demo data seeded successfully",
            "rules_created": len(demo_rules),
            "templates_created": len(demo_templates)
        }
    
    except Exception as e:
        logger.error(f"Error seeding demo data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
