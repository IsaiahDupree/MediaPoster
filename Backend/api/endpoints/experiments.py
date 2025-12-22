"""
Experiments API Endpoints
Handles experiment management, variant tracking, and results analysis
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os
import json

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

def get_engine():
    return create_engine(DATABASE_URL)


# =============================================================================
# MODELS
# =============================================================================

class ExperimentVariant(BaseModel):
    name: str
    description: str
    media_id: Optional[str] = None
    is_control: bool = False

class CreateExperiment(BaseModel):
    name: str
    hypothesis: str
    type: str  # 'hook', 'caption', 'cta', 'length', etc.
    primary_metric: str
    guardrail_metrics: List[str] = []
    variants: List[ExperimentVariant]
    traffic_split: str = 'even'  # 'even', 'rotation'
    platform_type: str = 'organic'  # 'organic', 'paid'
    platforms: List[str] = ['tiktok', 'instagram']
    min_sample_size: int = 1000

class UpdateExperiment(BaseModel):
    status: Optional[str] = None
    winner_variant_id: Optional[str] = None
    notes: Optional[str] = None

class BacklogIdea(BaseModel):
    hypothesis: str
    target_metric: str
    expected_impact: str  # 'S', 'M', 'L'
    effort: str  # 'S', 'M', 'L'
    confidence: str  # 'S', 'M', 'L'


# =============================================================================
# DATABASE SCHEMA MIGRATION
# =============================================================================

def ensure_tables():
    """Ensure experiment tables exist."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Experiments table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS experiments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                hypothesis TEXT,
                type TEXT NOT NULL,
                primary_metric TEXT NOT NULL,
                guardrail_metrics TEXT[] DEFAULT '{}',
                traffic_split TEXT DEFAULT 'even',
                platform_type TEXT DEFAULT 'organic',
                platforms TEXT[] DEFAULT '{}',
                min_sample_size INTEGER DEFAULT 1000,
                status TEXT DEFAULT 'draft',
                winner_variant_id UUID,
                uplift NUMERIC(8,2),
                confidence NUMERIC(5,2),
                notes TEXT,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        # Experiment variants table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS experiment_variants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                media_id UUID,
                is_control BOOLEAN DEFAULT false,
                impressions BIGINT DEFAULT 0,
                views BIGINT DEFAULT 0,
                primary_metric_value NUMERIC(10,4) DEFAULT 0,
                uplift_vs_control NUMERIC(8,2) DEFAULT 0,
                is_winner BOOLEAN DEFAULT false,
                metrics_json JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        # Experiment backlog table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS experiment_backlog (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                hypothesis TEXT NOT NULL,
                target_metric TEXT,
                expected_impact TEXT,
                effort TEXT,
                confidence TEXT,
                priority_score INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        # Experiment learnings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS experiment_learnings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                experiment_id UUID REFERENCES experiments(id),
                category TEXT,
                insight TEXT NOT NULL,
                metric TEXT,
                uplift NUMERIC(8,2),
                applies_to TEXT[] DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        conn.commit()


# Run migration on module load
try:
    ensure_tables()
except Exception as e:
    print(f"Warning: Could not ensure experiment tables: {e}")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/stats")
async def get_experiment_stats():
    """Get dashboard statistics for experiments."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get counts
        stats = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'running') as active,
                COUNT(*) FILTER (WHERE status = 'completed' AND completed_at > NOW() - INTERVAL '7 days') as completed_7d,
                COUNT(*) FILTER (WHERE status = 'completed' AND completed_at > NOW() - INTERVAL '30 days') as completed_30d,
                COUNT(*) FILTER (WHERE status = 'completed' AND uplift > 0) as wins,
                COUNT(*) FILTER (WHERE status = 'completed') as total_completed,
                AVG(uplift) FILTER (WHERE status = 'completed' AND uplift > 0) as avg_uplift
            FROM experiments
        """)).fetchone()
        
        # Get biggest winners
        winners = conn.execute(text("""
            SELECT name, uplift, primary_metric
            FROM experiments
            WHERE status = 'completed' AND uplift > 0
            ORDER BY uplift DESC
            LIMIT 3
        """)).fetchall()
        
        win_rate = (stats[3] / stats[4] * 100) if stats[4] and stats[4] > 0 else 0
        
        return {
            'active': stats[0] or 0,
            'completed_last_7': stats[1] or 0,
            'completed_last_30': stats[2] or 0,
            'win_rate': round(win_rate, 1),
            'avg_uplift': round(float(stats[5]), 1) if stats[5] else 0,
            'biggest_winners': [
                {'name': w[0], 'uplift': float(w[1]), 'metric': w[2]}
                for w in winners
            ]
        }


@router.get("/list")
async def list_experiments(
    status: Optional[str] = None,
    limit: int = 20
):
    """List all experiments with optional status filter."""
    engine = get_engine()
    
    with engine.connect() as conn:
        query = """
            SELECT 
                e.id, e.name, e.hypothesis, e.type, e.status,
                e.primary_metric, e.uplift, e.confidence,
                e.started_at, e.completed_at, e.winner_variant_id,
                (
                    SELECT json_agg(json_build_object(
                        'id', v.id,
                        'name', v.name,
                        'description', v.description,
                        'is_control', v.is_control,
                        'impressions', v.impressions,
                        'views', v.views,
                        'primary_metric_value', v.primary_metric_value,
                        'uplift_vs_control', v.uplift_vs_control,
                        'is_winner', v.is_winner
                    ))
                    FROM experiment_variants v
                    WHERE v.experiment_id = e.id
                ) as variants
            FROM experiments e
            WHERE (:status IS NULL OR e.status = :status)
            ORDER BY 
                CASE e.status 
                    WHEN 'running' THEN 1 
                    WHEN 'draft' THEN 2 
                    ELSE 3 
                END,
                e.created_at DESC
            LIMIT :limit
        """
        
        result = conn.execute(text(query), {'status': status, 'limit': limit}).fetchall()
        
        experiments = []
        for row in result:
            experiments.append({
                'id': str(row[0]),
                'name': row[1],
                'hypothesis': row[2],
                'type': row[3],
                'status': row[4],
                'primary_metric': row[5],
                'uplift': float(row[6]) if row[6] else None,
                'confidence': float(row[7]) if row[7] else None,
                'started_at': str(row[8]) if row[8] else None,
                'completed_at': str(row[9]) if row[9] else None,
                'winner_variant_id': str(row[10]) if row[10] else None,
                'variants': row[11] or [],
            })
        
        return {'experiments': experiments, 'total': len(experiments)}


# =============================================================================
# LEARNINGS ENDPOINTS (must be before /{experiment_id} route)
# =============================================================================

@router.get("/learnings")
async def get_learnings():
    """Get compiled learnings from completed experiments."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get learnings
        learnings = conn.execute(text("""
            SELECT category, insight, metric, uplift, applies_to
            FROM experiment_learnings
            ORDER BY uplift DESC NULLS LAST
        """)).fetchall()
        
        # Get best performers by category
        best_hooks = conn.execute(text("""
            SELECT e.name, e.uplift, e.primary_metric
            FROM experiments e
            WHERE e.status = 'completed' AND e.type = 'hook' AND e.uplift > 0
            ORDER BY e.uplift DESC
            LIMIT 3
        """)).fetchall()
        
        return {
            'learnings': [
                {
                    'category': l[0],
                    'insight': l[1],
                    'metric': l[2],
                    'uplift': float(l[3]) if l[3] else None,
                    'applies_to': l[4] or [],
                }
                for l in learnings
            ],
            'best_hooks': [
                {'name': h[0], 'uplift': float(h[1]), 'metric': h[2]}
                for h in best_hooks
            ],
        }


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get detailed experiment data."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get experiment
        exp = conn.execute(text("""
            SELECT 
                id, name, hypothesis, type, status, primary_metric,
                guardrail_metrics, traffic_split, platform_type, platforms,
                min_sample_size, uplift, confidence, notes,
                started_at, completed_at, created_at
            FROM experiments
            WHERE id = :id
        """), {'id': experiment_id}).fetchone()
        
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        # Get variants
        variants = conn.execute(text("""
            SELECT 
                id, name, description, media_id, is_control,
                impressions, views, primary_metric_value,
                uplift_vs_control, is_winner, metrics_json
            FROM experiment_variants
            WHERE experiment_id = :id
            ORDER BY is_control DESC, name
        """), {'id': experiment_id}).fetchall()
        
        return {
            'id': str(exp[0]),
            'name': exp[1],
            'hypothesis': exp[2],
            'type': exp[3],
            'status': exp[4],
            'primary_metric': exp[5],
            'guardrail_metrics': exp[6] or [],
            'traffic_split': exp[7],
            'platform_type': exp[8],
            'platforms': exp[9] or [],
            'min_sample_size': exp[10],
            'uplift': float(exp[11]) if exp[11] else None,
            'confidence': float(exp[12]) if exp[12] else None,
            'notes': exp[13],
            'started_at': str(exp[14]) if exp[14] else None,
            'completed_at': str(exp[15]) if exp[15] else None,
            'created_at': str(exp[16]) if exp[16] else None,
            'variants': [
                {
                    'id': str(v[0]),
                    'name': v[1],
                    'description': v[2],
                    'media_id': str(v[3]) if v[3] else None,
                    'is_control': v[4],
                    'impressions': v[5],
                    'views': v[6],
                    'primary_metric_value': float(v[7]) if v[7] else 0,
                    'uplift_vs_control': float(v[8]) if v[8] else 0,
                    'is_winner': v[9],
                    'metrics': v[10] or {},
                }
                for v in variants
            ]
        }


@router.post("/create")
async def create_experiment(data: CreateExperiment):
    """Create a new experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Create experiment
        result = conn.execute(text("""
            INSERT INTO experiments (
                name, hypothesis, type, primary_metric, guardrail_metrics,
                traffic_split, platform_type, platforms, min_sample_size, status
            ) VALUES (
                :name, :hypothesis, :type, :metric, :guardrails,
                :split, :platform_type, :platforms, :sample_size, 'draft'
            )
            RETURNING id
        """), {
            'name': data.name,
            'hypothesis': data.hypothesis,
            'type': data.type,
            'metric': data.primary_metric,
            'guardrails': data.guardrail_metrics,
            'split': data.traffic_split,
            'platform_type': data.platform_type,
            'platforms': data.platforms,
            'sample_size': data.min_sample_size,
        })
        
        experiment_id = result.fetchone()[0]
        
        # Create variants
        for i, variant in enumerate(data.variants):
            conn.execute(text("""
                INSERT INTO experiment_variants (
                    experiment_id, name, description, media_id, is_control
                ) VALUES (
                    :exp_id, :name, :desc, :media_id, :is_control
                )
            """), {
                'exp_id': experiment_id,
                'name': variant.name,
                'desc': variant.description,
                'media_id': variant.media_id,
                'is_control': variant.is_control or (i == 0),  # First variant is control by default
            })
        
        conn.commit()
        
        return {'id': str(experiment_id), 'status': 'draft'}


@router.post("/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """Start an experiment (change status to running)."""
    engine = get_engine()
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE experiments
            SET status = 'running', started_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status = 'draft'
        """), {'id': experiment_id})
        conn.commit()
        
        return {'status': 'running', 'started_at': datetime.now().isoformat()}


@router.post("/{experiment_id}/stop")
async def stop_experiment(experiment_id: str):
    """Stop a running experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE experiments
            SET status = 'stopped', updated_at = NOW()
            WHERE id = :id AND status = 'running'
        """), {'id': experiment_id})
        conn.commit()
        
        return {'status': 'stopped'}


@router.post("/{experiment_id}/complete")
async def complete_experiment(
    experiment_id: str,
    winner_variant_id: Optional[str] = None
):
    """Complete an experiment and optionally declare a winner."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get variants to calculate uplift
        variants = conn.execute(text("""
            SELECT id, primary_metric_value, is_control
            FROM experiment_variants
            WHERE experiment_id = :id
        """), {'id': experiment_id}).fetchall()
        
        control_value = None
        winner_value = None
        
        for v in variants:
            if v[2]:  # is_control
                control_value = float(v[1]) if v[1] else 0
            if winner_variant_id and str(v[0]) == winner_variant_id:
                winner_value = float(v[1]) if v[1] else 0
        
        uplift = None
        if control_value and winner_value and control_value > 0:
            uplift = ((winner_value - control_value) / control_value) * 100
        
        # Update experiment
        conn.execute(text("""
            UPDATE experiments
            SET status = 'completed', 
                completed_at = NOW(), 
                winner_variant_id = :winner,
                uplift = :uplift,
                confidence = 95,
                updated_at = NOW()
            WHERE id = :id
        """), {
            'id': experiment_id,
            'winner': winner_variant_id,
            'uplift': uplift,
        })
        
        # Mark winner
        if winner_variant_id:
            conn.execute(text("""
                UPDATE experiment_variants
                SET is_winner = (id = :winner)
                WHERE experiment_id = :exp_id
            """), {'winner': winner_variant_id, 'exp_id': experiment_id})
        
        conn.commit()
        
        return {'status': 'completed', 'uplift': uplift, 'winner': winner_variant_id}


@router.put("/{experiment_id}/variant/{variant_id}/metrics")
async def update_variant_metrics(
    experiment_id: str,
    variant_id: str,
    impressions: int = 0,
    views: int = 0,
    primary_metric_value: float = 0
):
    """Update metrics for a variant."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get control value for uplift calculation
        control = conn.execute(text("""
            SELECT primary_metric_value
            FROM experiment_variants
            WHERE experiment_id = :exp_id AND is_control = true
        """), {'exp_id': experiment_id}).fetchone()
        
        control_value = float(control[0]) if control and control[0] else None
        
        uplift = 0
        if control_value and control_value > 0:
            uplift = ((primary_metric_value - control_value) / control_value) * 100
        
        conn.execute(text("""
            UPDATE experiment_variants
            SET impressions = :impressions,
                views = :views,
                primary_metric_value = :metric,
                uplift_vs_control = :uplift,
                updated_at = NOW()
            WHERE id = :id AND experiment_id = :exp_id
        """), {
            'id': variant_id,
            'exp_id': experiment_id,
            'impressions': impressions,
            'views': views,
            'metric': primary_metric_value,
            'uplift': uplift,
        })
        conn.commit()
        
        return {'uplift': round(uplift, 2)}


# =============================================================================
# BACKLOG ENDPOINTS
# =============================================================================

@router.get("/backlog/list")
async def list_backlog():
    """Get experiment backlog sorted by priority."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, hypothesis, target_metric, expected_impact, effort, 
                   confidence, priority_score, source, status, created_at
            FROM experiment_backlog
            WHERE status = 'pending'
            ORDER BY priority_score DESC, created_at DESC
        """)).fetchall()
        
        return {
            'ideas': [
                {
                    'id': str(r[0]),
                    'hypothesis': r[1],
                    'target_metric': r[2],
                    'expected_impact': r[3],
                    'effort': r[4],
                    'confidence': r[5],
                    'priority_score': r[6],
                    'source': r[7],
                    'status': r[8],
                    'created_at': str(r[9]) if r[9] else None,
                }
                for r in result
            ]
        }


@router.post("/backlog/add")
async def add_to_backlog(idea: BacklogIdea):
    """Add an idea to the experiment backlog."""
    engine = get_engine()
    
    # Calculate priority score: Impact * Confidence / Effort
    impact_map = {'S': 1, 'M': 2, 'L': 3}
    effort_map = {'S': 1, 'M': 2, 'L': 3}
    conf_map = {'S': 1, 'M': 2, 'L': 3}
    
    priority = (
        impact_map.get(idea.expected_impact, 1) * 
        conf_map.get(idea.confidence, 1) * 33 / 
        effort_map.get(idea.effort, 1)
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO experiment_backlog (
                hypothesis, target_metric, expected_impact, effort,
                confidence, priority_score, source
            ) VALUES (
                :hypothesis, :metric, :impact, :effort, :conf, :priority, 'manual'
            )
            RETURNING id
        """), {
            'hypothesis': idea.hypothesis,
            'metric': idea.target_metric,
            'impact': idea.expected_impact,
            'effort': idea.effort,
            'conf': idea.confidence,
            'priority': int(priority),
        })
        
        conn.commit()
        
        return {'id': str(result.fetchone()[0]), 'priority_score': int(priority)}


@router.post("/backlog/generate-ideas")
async def generate_ideas():
    """Generate experiment ideas based on analytics and sentiment data."""
    engine = get_engine()
    
    ideas = []
    
    with engine.connect() as conn:
        # Check for retention issues
        retention = conn.execute(text("""
            SELECT AVG(pre_social_score)
            FROM video_analysis
            WHERE pre_social_score IS NOT NULL
        """)).scalar()
        
        if retention and retention < 50:
            ideas.append({
                'hypothesis': f'Content score averaging {round(retention)}% - test faster hook delivery',
                'target_metric': 'hook_rate_3s',
                'expected_impact': 'L',
                'effort': 'S',
                'confidence': 'L',
                'priority_score': 100,
                'source': 'ai',
            })
        
        # Check for posting patterns
        posts = conn.execute(text("""
            SELECT COUNT(*) FROM posted_content WHERE views > 0
        """)).scalar()
        
        if posts and posts > 5:
            ideas.append({
                'hypothesis': 'Test subtitle on/off impact on avg % viewed',
                'target_metric': 'avg_percent_viewed',
                'expected_impact': 'M',
                'effort': 'S',
                'confidence': 'L',
                'priority_score': 90,
                'source': 'ai',
            })
        
        # Add to backlog
        for idea in ideas:
            try:
                conn.execute(text("""
                    INSERT INTO experiment_backlog (
                        hypothesis, target_metric, expected_impact, effort,
                        confidence, priority_score, source
                    ) VALUES (
                        :hypothesis, :metric, :impact, :effort, :conf, :priority, :source
                    )
                """), {
                    'hypothesis': idea['hypothesis'],
                    'metric': idea['target_metric'],
                    'impact': idea['expected_impact'],
                    'effort': idea['effort'],
                    'conf': idea['confidence'],
                    'priority': idea['priority_score'],
                    'source': idea['source'],
                })
            except:
                pass
        
        conn.commit()
    
    return {'generated': len(ideas), 'ideas': ideas}


