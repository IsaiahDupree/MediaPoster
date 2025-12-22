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


@router.post("/backlog/{idea_id}/promote")
async def promote_to_experiment(idea_id: str):
    """Promote a backlog idea to a new experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get the idea
        idea = conn.execute(text("""
            SELECT hypothesis, target_metric FROM experiment_backlog WHERE id = :id
        """), {'id': idea_id}).fetchone()
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        
        # Create experiment from idea
        result = conn.execute(text("""
            INSERT INTO experiments (
                name, hypothesis, type, primary_metric, status
            ) VALUES (
                :name, :hypothesis, 'general', :metric, 'draft'
            )
            RETURNING id
        """), {
            'name': idea[0][:50] + '...' if len(idea[0]) > 50 else idea[0],
            'hypothesis': idea[0],
            'metric': idea[1] or 'hook_rate_3s',
        })
        
        experiment_id = result.fetchone()[0]
        
        # Create default variants
        conn.execute(text("""
            INSERT INTO experiment_variants (experiment_id, name, description, is_control)
            VALUES (:exp_id, 'A', 'Control variant', true),
                   (:exp_id, 'B', 'Test variant', false)
        """), {'exp_id': experiment_id})
        
        # Mark idea as promoted
        conn.execute(text("""
            UPDATE experiment_backlog SET status = 'promoted' WHERE id = :id
        """), {'id': idea_id})
        
        conn.commit()
        
        return {'experiment_id': str(experiment_id), 'status': 'draft'}


@router.post("/sync-metrics")
async def sync_experiment_metrics():
    """Sync metrics from posted content to running experiments."""
    engine = get_engine()
    
    synced = 0
    
    with engine.connect() as conn:
        # Get running experiments with their variants
        experiments = conn.execute(text("""
            SELECT e.id, e.primary_metric, v.id as variant_id, v.media_id
            FROM experiments e
            JOIN experiment_variants v ON v.experiment_id = e.id
            WHERE e.status = 'running' AND v.media_id IS NOT NULL
        """)).fetchall()
        
        for exp in experiments:
            exp_id, metric, variant_id, media_id = exp
            
            # Get metrics from posted_content
            metrics = conn.execute(text("""
                SELECT 
                    SUM(views) as views,
                    SUM(likes) as likes,
                    SUM(comments) as comments,
                    SUM(shares) as shares,
                    AVG(engagement_rate) as engagement_rate
                FROM posted_content
                WHERE local_content_id = :media_id OR platform_post_id = :media_id
            """), {'media_id': str(media_id)}).fetchone()
            
            if metrics and metrics[0]:
                views = int(metrics[0]) if metrics[0] else 0
                likes = int(metrics[1]) if metrics[1] else 0
                comments = int(metrics[2]) if metrics[2] else 0
                
                # Calculate primary metric value based on metric type
                if metric == 'hook_rate_3s':
                    # Estimate hook rate from engagement
                    primary_value = min(100, (likes + comments) / max(views, 1) * 1000)
                elif metric == 'comment_rate':
                    primary_value = comments / max(views, 1) * 100
                elif metric == 'share_rate':
                    primary_value = int(metrics[3] or 0) / max(views, 1) * 100
                else:
                    primary_value = float(metrics[4]) if metrics[4] else 0
                
                conn.execute(text("""
                    UPDATE experiment_variants
                    SET views = :views, impressions = :views, 
                        primary_metric_value = :metric_value,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    'id': variant_id,
                    'views': views,
                    'metric_value': round(primary_value, 2),
                })
                synced += 1
        
        # Recalculate uplifts
        conn.execute(text("""
            UPDATE experiment_variants v
            SET uplift_vs_control = 
                CASE 
                    WHEN v.is_control THEN 0
                    ELSE COALESCE(
                        ((v.primary_metric_value - ctrl.primary_metric_value) / NULLIF(ctrl.primary_metric_value, 0)) * 100,
                        0
                    )
                END
            FROM experiment_variants ctrl
            WHERE ctrl.experiment_id = v.experiment_id 
              AND ctrl.is_control = true
              AND v.experiment_id IN (SELECT id FROM experiments WHERE status = 'running')
        """))
        
        conn.commit()
    
    return {'synced_variants': synced}


@router.post("/seed-demo-data")
async def seed_demo_data():
    """Seed demo experiments for testing."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if we already have experiments
        count = conn.execute(text("SELECT COUNT(*) FROM experiments")).scalar()
        if count and count > 0:
            return {'message': 'Demo data already exists', 'count': count}
        
        # Create demo experiments
        demos = [
            {
                'name': 'Pain Point Cold Open Test',
                'hypothesis': 'Starting with a specific pain point will increase hook rate by 20%',
                'type': 'hook',
                'metric': 'hook_rate_3s',
                'status': 'running',
                'variants': [
                    {'name': 'A', 'desc': 'Original hook', 'views': 12500, 'value': 65, 'control': True},
                    {'name': 'B', 'desc': 'Pain Point Hook', 'views': 12800, 'value': 78, 'control': False},
                ],
            },
            {
                'name': 'Caption Length Test',
                'hypothesis': 'Shorter captions (under 100 chars) will increase save rate',
                'type': 'caption',
                'metric': 'save_rate',
                'status': 'completed',
                'winner': 'B',
                'uplift': 52,
                'variants': [
                    {'name': 'A', 'desc': 'Long Caption (250+ chars)', 'views': 15000, 'value': 2.1, 'control': True},
                    {'name': 'B', 'desc': 'Short Caption (<100 chars)', 'views': 14800, 'value': 3.2, 'control': False},
                ],
            },
            {
                'name': 'CTA Keyword vs Link',
                'hypothesis': 'Comment keyword CTA will drive more engagement than link CTA',
                'type': 'cta',
                'metric': 'comment_rate',
                'status': 'running',
                'variants': [
                    {'name': 'A', 'desc': 'Link in Bio CTA', 'views': 8200, 'value': 1.8, 'control': True},
                    {'name': 'B', 'desc': 'Comment TIPS for...', 'views': 8100, 'value': 4.2, 'control': False},
                ],
            },
        ]
        
        created = 0
        for demo in demos:
            # Create experiment
            result = conn.execute(text("""
                INSERT INTO experiments (
                    name, hypothesis, type, primary_metric, status,
                    started_at, completed_at, uplift, confidence
                ) VALUES (
                    :name, :hypothesis, :type, :metric, :status,
                    NOW() - INTERVAL '7 days',
                    CASE WHEN :status = 'completed' THEN NOW() ELSE NULL END,
                    :uplift, 
                    CASE WHEN :status = 'completed' THEN 95 ELSE NULL END
                )
                RETURNING id
            """), {
                'name': demo['name'],
                'hypothesis': demo['hypothesis'],
                'type': demo['type'],
                'metric': demo['metric'],
                'status': demo['status'],
                'uplift': demo.get('uplift'),
            })
            
            exp_id = result.fetchone()[0]
            winner_variant_id = None
            
            # Create variants
            for v in demo['variants']:
                vresult = conn.execute(text("""
                    INSERT INTO experiment_variants (
                        experiment_id, name, description, is_control,
                        impressions, views, primary_metric_value, uplift_vs_control
                    ) VALUES (
                        :exp_id, :name, :desc, :control,
                        :views, :views, :value,
                        CASE WHEN :control THEN 0 ELSE ((:value - :control_value) / NULLIF(:control_value, 0)) * 100 END
                    )
                    RETURNING id
                """), {
                    'exp_id': exp_id,
                    'name': v['name'],
                    'desc': v['desc'],
                    'control': v['control'],
                    'views': v['views'],
                    'value': v['value'],
                    'control_value': demo['variants'][0]['value'],
                })
                
                variant_id = vresult.fetchone()[0]
                if demo.get('winner') == v['name']:
                    winner_variant_id = variant_id
            
            # Set winner if completed
            if winner_variant_id:
                conn.execute(text("""
                    UPDATE experiments SET winner_variant_id = :winner WHERE id = :id
                """), {'winner': winner_variant_id, 'id': exp_id})
                
                conn.execute(text("""
                    UPDATE experiment_variants SET is_winner = true WHERE id = :id
                """), {'id': winner_variant_id})
            
            created += 1
        
        # Add backlog ideas
        backlog_ideas = [
            ('Adding subtitles will increase avg % viewed by 15%', 'avg_percent_viewed', 'M', 'S', 'L', 90),
            ('Faster cold open will boost hook rate by 25%', 'hook_rate_3s', 'L', 'M', 'M', 75),
            ('"Send to a friend" CTA will increase shares', 'share_rate', 'M', 'S', 'M', 67),
            ('Posting at 6PM vs 9AM will improve engagement', 'save_rate', 'S', 'S', 'S', 33),
        ]
        
        for idea in backlog_ideas:
            conn.execute(text("""
                INSERT INTO experiment_backlog (
                    hypothesis, target_metric, expected_impact, effort, confidence, priority_score, source
                ) VALUES (:h, :m, :i, :e, :c, :p, 'ai')
            """), {'h': idea[0], 'm': idea[1], 'i': idea[2], 'e': idea[3], 'c': idea[4], 'p': idea[5]})
        
        # Add learnings
        learnings = [
            ('hooks', 'Pain point hooks outperform generic intros', 'hook_rate_3s', 20, ['tiktok', 'instagram']),
            ('captions', 'Shorter captions drive higher save rates', 'save_rate', 52, ['instagram']),
            ('cta', 'Comment-based CTAs drive 2x more engagement', 'comment_rate', 133, ['tiktok']),
        ]
        
        for l in learnings:
            conn.execute(text("""
                INSERT INTO experiment_learnings (category, insight, metric, uplift, applies_to)
                VALUES (:cat, :insight, :metric, :uplift, :applies)
            """), {'cat': l[0], 'insight': l[1], 'metric': l[2], 'uplift': l[3], 'applies': l[4]})
        
        conn.commit()
        
        return {'created_experiments': created, 'backlog_ideas': len(backlog_ideas), 'learnings': len(learnings)}


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


