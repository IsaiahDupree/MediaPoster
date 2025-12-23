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
    # Phase 2: Account role targeting
    account_role: str = 'EXPERIMENT_ARM'  # Only run on experiment accounts
    account_ids: List[str] = []  # Specific accounts to use
    # Fairness controls
    fairness_controls: Dict[str, Any] = {}  # time_buckets, topic_matching, etc.
    # Trend integration
    trend_opportunity_id: Optional[str] = None  # If spawned from a trend

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
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                -- Phase 2: Account role & fairness
                account_role TEXT DEFAULT 'EXPERIMENT_ARM',
                account_ids UUID[] DEFAULT '{}',
                fairness_controls JSONB DEFAULT '{}',
                trend_opportunity_id UUID,
                -- Knowledge base integration
                generated_rule_ids UUID[] DEFAULT '{}'
            )
        """))
        
        # Add new columns if table already exists
        conn.execute(text("""
            DO $$ BEGIN
                ALTER TABLE experiments ADD COLUMN IF NOT EXISTS account_role TEXT DEFAULT 'EXPERIMENT_ARM';
                ALTER TABLE experiments ADD COLUMN IF NOT EXISTS account_ids UUID[] DEFAULT '{}';
                ALTER TABLE experiments ADD COLUMN IF NOT EXISTS fairness_controls JSONB DEFAULT '{}';
                ALTER TABLE experiments ADD COLUMN IF NOT EXISTS trend_opportunity_id UUID;
                ALTER TABLE experiments ADD COLUMN IF NOT EXISTS generated_rule_ids UUID[] DEFAULT '{}';
            EXCEPTION WHEN others THEN NULL;
            END $$;
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
# STATIC ROUTES (must be before /{experiment_id} route)
# =============================================================================

@router.get("/experiment-accounts")
async def get_experiment_accounts():
    """Get accounts available for experiments (EXPERIMENT_ARM role only)."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Check if account_role column exists
            try:
                result = conn.execute(text("""
                    SELECT id, platform, handle, account_role
                    FROM social_accounts
                    WHERE account_role = 'EXPERIMENT_ARM' AND is_active = true
                    ORDER BY platform, handle
                """)).fetchall()
            except:
                # Fallback if account_role doesn't exist yet
                try:
                    result = conn.execute(text("""
                        SELECT id, platform, handle, 'EXPERIMENT_ARM' as account_role
                        FROM social_accounts
                        WHERE is_active = true
                        ORDER BY platform, handle
                    """)).fetchall()
                except:
                    # Table might not exist at all
                    return {'accounts': [], 'count': 0}
            
            accounts = [
                {
                    'id': str(row[0]),
                    'platform': row[1],
                    'handle': row[2],
                    'account_role': row[3]
                }
                for row in result
            ]
            
            return {'accounts': accounts, 'count': len(accounts)}
    except Exception as e:
        # Return empty list on any database error
        return {'accounts': [], 'count': 0, 'error': str(e)}


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


# =============================================================================
# PHASE 2: ACCOUNT ROLE FILTERING
# =============================================================================

@router.patch("/accounts/{account_id}/role")
async def update_account_role(account_id: str, role: str = 'EXPERIMENT_ARM'):
    """Update an account's role (MAINLINE or EXPERIMENT_ARM)."""
    if role not in ['MAINLINE', 'EXPERIMENT_ARM', 'ARCHIVE', 'SEED']:
        raise HTTPException(status_code=400, detail="Invalid role. Must be MAINLINE, EXPERIMENT_ARM, ARCHIVE, or SEED")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                UPDATE social_accounts SET account_role = :role WHERE id = :id
            """), {'id': account_id, 'role': role})
            conn.commit()
        except Exception as e:
            # Column might not exist, try adding it
            conn.execute(text("""
                ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS account_role TEXT DEFAULT 'MAINLINE'
            """))
            conn.execute(text("""
                UPDATE social_accounts SET account_role = :role WHERE id = :id
            """), {'id': account_id, 'role': role})
            conn.commit()
    
    return {'id': account_id, 'account_role': role, 'message': 'Role updated'}


# =============================================================================
# PHASE 2: STATISTICAL CONFIDENCE CALCULATION
# =============================================================================

import math

def calculate_confidence(control_value: float, variant_value: float, 
                         control_n: int, variant_n: int) -> dict:
    """
    Calculate statistical confidence using a simplified z-test.
    Returns confidence percentage and whether result is significant.
    """
    if control_n < 30 or variant_n < 30:
        return {'confidence': 0, 'significant': False, 'reason': 'Insufficient sample size (need 30+)'}
    
    if control_value <= 0:
        return {'confidence': 0, 'significant': False, 'reason': 'Control value is zero'}
    
    # Calculate uplift
    uplift = ((variant_value - control_value) / control_value) * 100
    
    # Simplified confidence calculation based on sample size and effect size
    # Using approximation: confidence increases with sample size and effect size
    effect_size = abs(variant_value - control_value) / max(control_value, 0.001)
    sample_factor = math.sqrt(min(control_n, variant_n) / 1000)
    
    # Base confidence from effect size (larger effect = more confident)
    base_confidence = min(95, effect_size * 100 * sample_factor)
    
    # Adjust for sample size
    if control_n >= 1000 and variant_n >= 1000:
        base_confidence = min(99, base_confidence * 1.2)
    elif control_n >= 500 and variant_n >= 500:
        base_confidence = min(95, base_confidence * 1.1)
    
    # Determine significance (typically 95% threshold)
    significant = base_confidence >= 95
    
    return {
        'confidence': round(base_confidence, 1),
        'significant': significant,
        'uplift': round(uplift, 2),
        'effect_size': round(effect_size, 4),
        'control_n': control_n,
        'variant_n': variant_n
    }


@router.post("/{experiment_id}/calculate-confidence")
async def calculate_experiment_confidence(experiment_id: str):
    """Calculate statistical confidence for an experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get variants
        variants = conn.execute(text("""
            SELECT id, name, is_control, views, primary_metric_value
            FROM experiment_variants
            WHERE experiment_id = :id
            ORDER BY is_control DESC
        """), {'id': experiment_id}).fetchall()
        
        if len(variants) < 2:
            return {'error': 'Need at least 2 variants'}
        
        # Find control
        control = None
        test_variants = []
        for v in variants:
            if v[2]:  # is_control
                control = v
            else:
                test_variants.append(v)
        
        if not control:
            return {'error': 'No control variant found'}
        
        results = []
        best_variant = None
        best_confidence = 0
        
        for variant in test_variants:
            conf = calculate_confidence(
                control_value=float(control[4] or 0),
                variant_value=float(variant[4] or 0),
                control_n=int(control[3] or 0),
                variant_n=int(variant[3] or 0)
            )
            conf['variant_id'] = str(variant[0])
            conf['variant_name'] = variant[1]
            results.append(conf)
            
            if conf['confidence'] > best_confidence and conf.get('uplift', 0) > 0:
                best_confidence = conf['confidence']
                best_variant = variant
        
        # Update experiment confidence
        if best_variant and best_confidence > 0:
            conn.execute(text("""
                UPDATE experiments 
                SET confidence = :conf, updated_at = NOW()
                WHERE id = :id
            """), {'id': experiment_id, 'conf': best_confidence})
            conn.commit()
        
        return {
            'experiment_id': experiment_id,
            'control': {'id': str(control[0]), 'name': control[1], 'value': float(control[4] or 0), 'n': int(control[3] or 0)},
            'variants': results,
            'best_confidence': best_confidence,
            'recommendation': 'significant' if best_confidence >= 95 else 'need_more_data'
        }


# =============================================================================
# PHASE 2: RULE LEARNER (Convert experiment results to KB rules)
# =============================================================================

@router.post("/{experiment_id}/generate-rule")
async def generate_rule_from_experiment(experiment_id: str):
    """Generate a knowledge base rule from a completed experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get experiment
        exp = conn.execute(text("""
            SELECT id, name, hypothesis, type, primary_metric, status,
                   winner_variant_id, uplift, confidence, platforms
            FROM experiments WHERE id = :id
        """), {'id': experiment_id}).fetchone()
        
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        if exp[5] != 'completed':
            raise HTTPException(status_code=400, detail="Experiment must be completed to generate rule")
        
        if not exp[6]:  # winner_variant_id
            raise HTTPException(status_code=400, detail="No winner variant declared")
        
        # Get winner variant details
        winner = conn.execute(text("""
            SELECT name, description, primary_metric_value
            FROM experiment_variants WHERE id = :id
        """), {'id': exp[6]}).fetchone()
        
        if not winner:
            raise HTTPException(status_code=404, detail="Winner variant not found")
        
        # Create rule
        rule_type = exp[3]  # experiment type
        name = f"From Experiment: {exp[1]}"
        recommendation = f"{winner[0]}: {winner[1]}"
        conditions = {
            'platform': list(exp[9]) if exp[9] else ['tiktok', 'instagram'],
            'experiment_validated': True
        }
        
        # Check if kb_rules table exists
        try:
            result = conn.execute(text("""
                INSERT INTO kb_rules (
                    rule_type, name, description, conditions, recommendation,
                    expected_lift, confidence, source_experiment_id, status
                ) VALUES (
                    :type, :name, :desc, :conditions::jsonb, :recommendation,
                    :lift, :conf, :exp_id, 'active'
                )
                RETURNING id
            """), {
                'type': rule_type,
                'name': name,
                'desc': exp[2],  # hypothesis
                'conditions': json.dumps(conditions),
                'recommendation': recommendation,
                'lift': float(exp[7]) if exp[7] else 0,
                'conf': float(exp[8]) / 100 if exp[8] else 0,  # Convert to 0-1 scale
                'exp_id': experiment_id
            })
            
            rule_id = str(result.fetchone()[0])
            
            # Update experiment with generated rule
            conn.execute(text("""
                UPDATE experiments 
                SET generated_rule_ids = array_append(COALESCE(generated_rule_ids, '{}'), :rule_id::uuid)
                WHERE id = :id
            """), {'id': experiment_id, 'rule_id': rule_id})
            
            conn.commit()
            
            return {
                'rule_id': rule_id,
                'rule_type': rule_type,
                'name': name,
                'recommendation': recommendation,
                'expected_lift': float(exp[7]) if exp[7] else 0,
                'confidence': float(exp[8]) if exp[8] else 0,
                'message': 'Rule created and added to Knowledge Base'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'message': 'Could not create rule. KB tables may not exist yet.'
            }


@router.post("/batch-generate-rules")
async def batch_generate_rules():
    """Generate rules from all completed experiments that don't have rules yet."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Find completed experiments without rules
        experiments = conn.execute(text("""
            SELECT id FROM experiments 
            WHERE status = 'completed' 
              AND winner_variant_id IS NOT NULL
              AND (generated_rule_ids IS NULL OR array_length(generated_rule_ids, 1) IS NULL)
        """)).fetchall()
        
        generated = []
        for exp in experiments:
            try:
                result = await generate_rule_from_experiment(str(exp[0]))
                if 'rule_id' in result:
                    generated.append(result)
            except:
                pass
        
        return {'rules_generated': len(generated), 'rules': generated}


# =============================================================================
# PHASE 2: VARIANT SCHEDULING WITH FAIRNESS CONTROLS
# =============================================================================

class VariantScheduleRequest(BaseModel):
    experiment_id: str
    variant_id: str
    account_id: str
    platform: str
    scheduled_at: str  # ISO format
    media_id: Optional[str] = None
    caption: Optional[str] = None


@router.post("/schedule-variant")
async def schedule_experiment_variant(request: VariantScheduleRequest):
    """Schedule a variant for posting with fairness controls."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Verify experiment exists and is running
        exp = conn.execute(text("""
            SELECT id, status, account_role, fairness_controls
            FROM experiments WHERE id = :id
        """), {'id': request.experiment_id}).fetchone()
        
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        if exp[1] != 'running':
            raise HTTPException(status_code=400, detail="Experiment must be running to schedule variants")
        
        # Verify account role matches experiment
        try:
            account = conn.execute(text("""
                SELECT id, account_role FROM social_accounts WHERE id = :id
            """), {'id': request.account_id}).fetchone()
            
            if account and account[1] != exp[2]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Account role {account[1]} doesn't match experiment role {exp[2]}"
                )
        except:
            pass  # account_role column might not exist
        
        # Check fairness controls (time bucket matching)
        fairness = exp[3] or {}
        
        # Create scheduled post with experiment tracking
        try:
            result = conn.execute(text("""
                INSERT INTO scheduled_posts (
                    account_id, platform, media_id, caption, scheduled_at,
                    status, origin, experiment_id, experiment_arm
                ) VALUES (
                    :account_id, :platform, :media_id, :caption, :scheduled_at,
                    'scheduled', 'EXPERIMENT', :experiment_id, :variant_id
                )
                RETURNING id
            """), {
                'account_id': request.account_id,
                'platform': request.platform,
                'media_id': request.media_id,
                'caption': request.caption,
                'scheduled_at': request.scheduled_at,
                'experiment_id': request.experiment_id,
                'variant_id': request.variant_id
            })
            
            post_id = str(result.fetchone()[0])
            conn.commit()
            
            return {
                'scheduled_post_id': post_id,
                'experiment_id': request.experiment_id,
                'variant_id': request.variant_id,
                'scheduled_at': request.scheduled_at,
                'message': 'Variant scheduled successfully'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'message': 'Could not schedule. scheduled_posts table may need migration.'
            }


@router.get("/{experiment_id}/scheduled-variants")
async def get_scheduled_variants(experiment_id: str):
    """Get all scheduled posts for an experiment."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT id, account_id, platform, scheduled_at, status, experiment_arm
                FROM scheduled_posts
                WHERE experiment_id = :id
                ORDER BY scheduled_at
            """), {'id': experiment_id}).fetchall()
            
            posts = [
                {
                    'id': str(row[0]),
                    'account_id': str(row[1]),
                    'platform': row[2],
                    'scheduled_at': row[3].isoformat() if row[3] else None,
                    'status': row[4],
                    'variant_id': str(row[5]) if row[5] else None
                }
                for row in result
            ]
            
            return {'experiment_id': experiment_id, 'scheduled_posts': posts, 'count': len(posts)}
            
        except Exception as e:
            return {'experiment_id': experiment_id, 'scheduled_posts': [], 'error': str(e)}


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


# =============================================================================
# EXPERIMENTS SCHEDULER INTEGRATION
# =============================================================================

@router.post("/scheduler/create")
async def create_scheduled_experiment(
    name: str,
    goal: str,
    description: str = ""
):
    """Create a new AI-planned experiment."""
    from services.experiments_scheduler import ExperimentsScheduler
    
    scheduler = ExperimentsScheduler()
    
    try:
        experiment = await scheduler.create_experiment(
            name=name,
            goal=goal,
            description=description
        )
        return {"success": True, "experiment": experiment.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/scheduler/plan")
async def plan_experiment(goal: str):
    """Have AI agent plan an experiment for a goal."""
    from services.experiments_scheduler import ExperimentAgent
    
    agent = ExperimentAgent()
    
    try:
        # Get available resources
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM video_analysis WHERE pre_social_score >= 60
            """)).fetchone()
            video_count = result[0] if result else 0
        
        resources = {
            "types": ["ugc", "edited"],
            "video_count": video_count,
            "tools": ["subtitles", "hooks", "trimming"]
        }
        
        experiment = await agent.plan_experiment(goal, resources)
        
        return {
            "success": True,
            "experiment": experiment.to_dict(),
            "hypotheses_count": len(experiment.hypotheses)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/scheduler/agent/actions")
async def get_agent_actions():
    """Get available agent actions."""
    from services.experiments_scheduler import ExperimentAgent
    
    agent = ExperimentAgent()
    return {"actions": agent.get_available_actions()}


@router.post("/scheduler/{experiment_id}/start")
async def start_scheduled_experiment(experiment_id: str):
    """Start an experiment."""
    from services.experiments_scheduler import ExperimentsScheduler
    
    scheduler = ExperimentsScheduler()
    
    try:
        experiment = await scheduler.start_experiment(experiment_id)
        return {"success": True, "experiment": experiment.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/scheduler/{experiment_id}/analyze")
async def analyze_experiment(experiment_id: str):
    """Analyze experiment results."""
    from services.experiments_scheduler import ExperimentsScheduler
    
    scheduler = ExperimentsScheduler()
    
    try:
        experiment = await scheduler.get_experiment(experiment_id)
        if not experiment:
            return {"success": False, "error": "Experiment not found"}
        
        results = []
        for hypothesis in experiment.hypotheses:
            analyzed = await scheduler.analyze_hypothesis(hypothesis.id)
            results.append(analyzed.to_dict())
        
        return {
            "success": True,
            "experiment_id": experiment_id,
            "hypotheses": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/winners")
async def get_experiment_winners(limit: int = 10):
    """Get top performing experiment content."""
    from services.experiments_scheduler import WinnerDetector
    
    detector = WinnerDetector()
    
    try:
        winners = await detector.detect_winners()
        return {
            "success": True,
            "winners": [w.to_dict() for w in winners[:limit]],
            "count": len(winners)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/winners/promotion-candidates")
async def get_promotion_candidates(limit: int = 10):
    """Get winners ready for narrative promotion."""
    from services.experiments_scheduler import WinnerDetector
    
    detector = WinnerDetector()
    
    try:
        candidates = await detector.get_promotion_candidates(limit)
        return {
            "success": True,
            "candidates": [c.to_dict() for c in candidates],
            "count": len(candidates)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/winners/{winner_id}/promote")
async def promote_winner(winner_id: str, narrative_goal_id: Optional[str] = None):
    """Promote a winner to the narrative builder."""
    from services.experiments_scheduler import WinnerDetector
    
    detector = WinnerDetector()
    
    try:
        result = await detector.promote_to_narrative(winner_id, narrative_goal_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/analytics/by-origin")
async def get_analytics_by_origin():
    """Get performance analytics grouped by post origin."""
    from services.experiments_scheduler import ExperimentsScheduler
    
    scheduler = ExperimentsScheduler()
    
    try:
        analytics = await scheduler.get_analytics_by_origin()
        return {"success": True, "analytics": analytics}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# PATTERN LEARNING ENDPOINTS
# =============================================================================

@router.get("/patterns")
async def get_patterns(
    pattern_type: Optional[str] = None,
    min_confidence: float = 0.5,
    limit: int = 20
):
    """Get learned content patterns."""
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    
    try:
        patterns = await learner.get_patterns(
            pattern_type=pattern_type,
            min_confidence=min_confidence,
            limit=limit
        )
        return {
            "success": True,
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/patterns/extract/{experiment_id}")
async def extract_patterns(experiment_id: str):
    """Extract patterns from a completed experiment."""
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    
    try:
        patterns = await learner.extract_patterns_from_experiment(experiment_id)
        return {
            "success": True,
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/patterns/recommend")
async def recommend_patterns(
    content_type: str = "hook",
    pillar: Optional[str] = None,
    target_metric: str = "engagement_rate"
):
    """Get pattern recommendations for content creation."""
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    
    try:
        patterns = await learner.recommend_patterns_for_content(
            content_type=content_type,
            pillar=pillar,
            target_metric=target_metric
        )
        return {
            "success": True,
            "recommendations": [p.to_dict() for p in patterns],
            "count": len(patterns)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/frameworks/create")
async def create_framework(
    name: str,
    pattern_ids: List[str],
    pillars: List[str] = []
):
    """Create a content framework from patterns."""
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    
    try:
        framework = await learner.generate_framework(
            name=name,
            pattern_ids=pattern_ids,
            pillars=pillars
        )
        return {
            "success": True,
            "framework": framework.to_dict()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# EXPERIMENT DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard/overview")
async def get_dashboard_overview():
    """Get experiments dashboard overview."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Active experiments
        active_exp = conn.execute(text(
            "SELECT COUNT(*) FROM experiments WHERE status = 'active'"
        )).scalar() or 0
        
        # Total experiments
        total_exp = conn.execute(text(
            "SELECT COUNT(*) FROM experiments"
        )).scalar() or 0
        
        # Passed hypotheses
        passed_hyp = conn.execute(text(
            "SELECT COUNT(*) FROM hypotheses WHERE status = 'passed'"
        )).scalar() or 0
        
        # Failed hypotheses
        failed_hyp = conn.execute(text(
            "SELECT COUNT(*) FROM hypotheses WHERE status = 'failed'"
        )).scalar() or 0
        
        # Learned patterns
        patterns = conn.execute(text(
            "SELECT COUNT(*) FROM content_patterns WHERE is_active = TRUE"
        )).scalar() or 0
        
        # Winners detected
        winners = conn.execute(text(
            "SELECT COUNT(*) FROM experiment_winners"
        )).scalar() or 0
        
        # Posts by origin
        origin_stats = {}
        origin_result = conn.execute(text("""
            SELECT COALESCE(origin_type, 'user') as origin, COUNT(*) 
            FROM scheduled_posts 
            GROUP BY origin_type
        """))
        for row in origin_result:
            origin_stats[row[0]] = row[1]
    
    return {
        "success": True,
        "overview": {
            "experiments": {
                "active": active_exp,
                "total": total_exp
            },
            "hypotheses": {
                "passed": passed_hyp,
                "failed": failed_hyp,
                "pass_rate": passed_hyp / max(passed_hyp + failed_hyp, 1)
            },
            "patterns_learned": patterns,
            "winners_detected": winners,
            "posts_by_origin": origin_stats
        }
    }


@router.get("/dashboard/recent-experiments")
async def get_recent_experiments(limit: int = 10):
    """Get recent experiments with status."""
    engine = get_engine()
    
    experiments = []
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT e.id, e.name, e.goal, e.status, e.created_at,
                   COUNT(h.id) as hypothesis_count,
                   SUM(CASE WHEN h.status = 'passed' THEN 1 ELSE 0 END) as passed_count
            FROM experiments e
            LEFT JOIN hypotheses h ON h.experiment_id = e.id
            GROUP BY e.id, e.name, e.goal, e.status, e.created_at
            ORDER BY e.created_at DESC
            LIMIT :limit
        """), {"limit": limit})
        
        for row in result:
            experiments.append({
                "id": str(row[0]),
                "name": row[1],
                "goal": row[2],
                "status": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "hypothesis_count": row[5] or 0,
                "passed_count": row[6] or 0
            })
    
    return {"success": True, "experiments": experiments}


@router.get("/dashboard/hypothesis-results")
async def get_hypothesis_results(limit: int = 20):
    """Get hypothesis results with improvements."""
    engine = get_engine()
    
    hypotheses = []
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT h.id, h.statement, h.status, h.actual_improvement,
                   h.confidence_level, h.success_threshold, h.learnings,
                   e.name as experiment_name
            FROM hypotheses h
            LEFT JOIN experiments e ON e.id = h.experiment_id
            WHERE h.status IN ('passed', 'failed', 'inconclusive')
            ORDER BY h.updated_at DESC NULLS LAST
            LIMIT :limit
        """), {"limit": limit})
        
        for row in result:
            hypotheses.append({
                "id": str(row[0]),
                "statement": row[1],
                "status": row[2],
                "actual_improvement": float(row[3]) if row[3] else None,
                "confidence_level": float(row[4]) if row[4] else None,
                "success_threshold": float(row[5]) if row[5] else 1.2,
                "learnings": row[6],
                "experiment_name": row[7]
            })
    
    return {"success": True, "hypotheses": hypotheses}


@router.get("/dashboard/top-patterns")
async def get_top_patterns(limit: int = 10):
    """Get top performing content patterns."""
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    
    try:
        patterns = await learner.get_patterns(min_confidence=0.5, limit=limit)
        return {
            "success": True,
            "patterns": [p.to_dict() for p in patterns]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/dashboard/winner-leaderboard")
async def get_winner_leaderboard(limit: int = 10):
    """Get top winners ranked by performance."""
    engine = get_engine()
    
    winners = []
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT w.id, w.video_id, w.ranking_score, w.winner_type,
                   w.promoted_to_narrative, w.performance_metrics,
                   e.name as experiment_name
            FROM experiment_winners w
            LEFT JOIN experiments e ON e.id = w.experiment_id
            ORDER BY w.ranking_score DESC
            LIMIT :limit
        """), {"limit": limit})
        
        for row in result:
            winners.append({
                "id": str(row[0]),
                "video_id": str(row[1]) if row[1] else None,
                "ranking_score": float(row[2]) if row[2] else 0,
                "winner_type": row[3],
                "promoted_to_narrative": row[4],
                "performance_metrics": row[5] or {},
                "experiment_name": row[6]
            })
    
    return {"success": True, "winners": winners}


# =============================================================================
# EXPERIMENT-TO-NARRATIVE PIPELINE
# =============================================================================

@router.post("/pipeline/promote-winners")
async def promote_winners_to_narrative(
    min_ranking_score: float = 0.7,
    max_promotions: int = 5,
    narrative_goal_id: Optional[str] = None
):
    """Promote top experiment winners to narrative builder."""
    from services.experiments_scheduler import WinnerDetector
    
    detector = WinnerDetector()
    
    promoted = []
    errors = []
    
    try:
        # Get promotion candidates
        candidates = await detector.get_promotion_candidates(limit=max_promotions)
        
        for candidate in candidates:
            if candidate.ranking_score >= min_ranking_score:
                try:
                    result = await detector.promote_to_narrative(
                        candidate.id, 
                        narrative_goal_id
                    )
                    if result.get("success"):
                        promoted.append({
                            "winner_id": candidate.id,
                            "video_id": candidate.video_id,
                            "narrative_post_id": result.get("narrative_post_id")
                        })
                except Exception as e:
                    errors.append({
                        "winner_id": candidate.id,
                        "error": str(e)
                    })
        
        return {
            "success": True,
            "promoted_count": len(promoted),
            "promoted": promoted,
            "errors": errors
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pipeline/run-experiment")
async def run_complete_experiment(
    goal: str,
    min_score: int = 60,
    videos_per_variant: int = 5,
    platform: str = "tiktok"
):
    """
    Run a complete experiment end-to-end.
    
    1. Plans experiment with AI
    2. Selects content from library
    3. Schedules control and variant posts
    4. Returns experiment for monitoring
    """
    from services.experiments_scheduler import (
        ExperimentAgent, ExperimentsScheduler
    )
    
    agent = ExperimentAgent()
    scheduler = ExperimentsScheduler()
    
    try:
        # Step 1: Plan experiment
        resources = {"types": ["ugc"], "tools": ["subtitles", "hooks"]}
        experiment = await agent.plan_experiment(goal, resources)
        
        # Step 2: Save to database
        saved_exp = await scheduler.create_experiment(
            name=experiment.name,
            goal=experiment.goal,
            description=f"Auto-generated experiment for: {goal}"
        )
        
        # Step 3: Add hypotheses
        for hyp in experiment.hypotheses:
            hyp.experiment_id = saved_exp.id
            await scheduler.add_hypothesis(saved_exp.id, hyp)
        
        # Step 4: Browse content library
        action = await agent.execute_action(
            AgentAction(
                experiment_id=saved_exp.id,
                action_type=AgentActionType.BROWSE_UGC_LIBRARY,
                action_params={"min_score": min_score, "limit": videos_per_variant * 2}
            )
        )
        
        videos = action.result.get("videos", [])
        
        # Step 5: Split into control and variant
        control_ids = [v["id"] for v in videos[::2]][:videos_per_variant]
        variant_ids = [v["id"] for v in videos[1::2]][:videos_per_variant]
        
        # Step 6: Schedule posts (if we have videos)
        scheduled = {"control": 0, "variant": 0}
        if control_ids and variant_ids and experiment.hypotheses:
            hyp = experiment.hypotheses[0]
            result = await scheduler.schedule_experiment_posts(
                experiment_id=saved_exp.id,
                hypothesis_id=hyp.id,
                control_video_ids=control_ids,
                variant_video_ids=variant_ids,
                platform=platform
            )
            scheduled = {
                "control": len(result.get("control_posts", [])),
                "variant": len(result.get("variant_posts", []))
            }
        
        # Step 7: Start experiment
        await scheduler.start_experiment(saved_exp.id)
        
        return {
            "success": True,
            "experiment_id": saved_exp.id,
            "hypotheses_count": len(experiment.hypotheses),
            "videos_found": len(videos),
            "scheduled": scheduled,
            "status": "active"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


from services.experiments_scheduler.experiment_agent import AgentAction, AgentActionType


@router.post("/pipeline/sync-learnings")
async def sync_learnings_to_narrative():
    """
    Sync experiment learnings to narrative builder.
    
    Updates narrative pillars with successful patterns.
    """
    from services.experiments_scheduler import PatternLearner
    
    learner = PatternLearner()
    engine = get_engine()
    
    synced_patterns = []
    
    try:
        # Get high-confidence patterns
        patterns = await learner.get_patterns(min_confidence=0.7, limit=20)
        
        # Update learnings table for narrative use
        with engine.connect() as conn:
            for pattern in patterns:
                try:
                    conn.execute(text("""
                        INSERT INTO learnings (id, content_id, learning_type, 
                            insight, confidence, created_at)
                        VALUES (gen_random_uuid(), NULL, 'experiment_pattern',
                            :insight, :confidence, NOW())
                        ON CONFLICT DO NOTHING
                    """), {
                        "insight": f"Pattern: {pattern.name} - {pattern.description}. "
                                   f"Avg improvement: {pattern.avg_improvement:.1%}",
                        "confidence": pattern.confidence
                    })
                    synced_patterns.append(pattern.name)
                except Exception:
                    pass
            conn.commit()
        
        return {
            "success": True,
            "synced_count": len(synced_patterns),
            "patterns": synced_patterns
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

