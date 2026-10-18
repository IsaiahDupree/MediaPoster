"""
Celery Tasks for Weekly Competitor Reports
===========================================
Scheduled tasks to automatically generate and deliver weekly competitor analysis reports.
"""

from celery import shared_task
from datetime import datetime
from loguru import logger
import asyncio
from sqlalchemy import text

from services.competitor_audit import (
    CompetitorCollector,
    CompetitorDeepAuditService,
    FunnelMapper,
    PostRanker,
    CompetitorReportGenerator
)
from services.competitor_audit.posting_time_analyzer import PostingTimeAnalyzer
from services.competitor_audit.hook_generator import HookGenerator


@shared_task(name='tasks.competitor_weekly_reports.generate_weekly_reports')
def generate_weekly_reports():
    """
    Generate weekly competitor analysis reports for all tracked accounts.
    Runs every Sunday at 3:00 AM via Celery Beat.
    """
    import asyncio
    
    async def _generate():
        async with async_session_maker() as db:
            try:
                logger.info("Starting weekly competitor report generation")
                
                # Get all tracked competitor accounts
                collector = CompetitorCollector()
                
                # Query database for all competitor accounts
                from sqlalchemy import text
                query = text("""
                    SELECT DISTINCT account_id, platform, handle, display_name, follower_count
                    FROM competitor_accounts
                    WHERE is_active = true
                """)
                
                with collector.engine.connect() as conn:
                    result = conn.execute(query)
                    accounts = result.fetchall()
                
                logger.info(f"Found {len(accounts)} active competitor accounts")
                
                reports_generated = 0
                errors = []
                
                for account_row in accounts:
                    account_id = str(account_row[0])
                    platform = account_row[1]
                    handle = account_row[2]
                    display_name = account_row[3]
                    follower_count = account_row[4] or 0
                    
                    try:
                        logger.info(f"Generating report for @{handle} ({platform})")
                        
                        # 1. Collect latest posts (if needed)
                        # Note: This might be done separately by sync scheduler
                        
                        # 2. Run deep audit
                        deep_audit_service = CompetitorDeepAuditService()
                        account_audit = await deep_audit_service.audit_account(account_id)
                        
                        # 3. Map funnel
                        funnel_mapper = FunnelMapper()
                        funnel_map = await funnel_mapper.map_funnel(account_id)
                        
                        # 4. Rank posts (not async)
                        post_ranker = PostRanker()
                        ranking = post_ranker.rank_posts(
                            account_id=account_id,
                            ranking_type="composite",
                            time_window="30d"
                        )
                        
                        # 5. Analyze posting times
                        posting_analyzer = PostingTimeAnalyzer()
                        posting_recommendation = await posting_analyzer.analyze_account(
                            account_id=account_id,
                            days_back=90
                        )
                        
                        # 6. Get post data for report
                        posts_query = text("""
                            SELECT id, permalink, caption_text, posted_at, views, likes, comments
                            FROM competitor_posts
                            WHERE account_id = CAST(:account_id AS uuid)
                            ORDER BY posted_at DESC
                            LIMIT 50
                        """)
                        
                        with collector.engine.connect() as conn:
                            posts_result = conn.execute(posts_query, {"account_id": account_id})
                            posts_data = [
                                {
                                    "post_id": str(row[0]),
                                    "permalink": row[1],
                                    "caption_text": row[2],
                                    "posted_at": row[3].isoformat() if row[3] else None,
                                    "views": row[4] or 0,
                                    "likes": row[5] or 0,
                                    "comments": row[6] or 0
                                }
                                for row in posts_result.fetchall()
                            ]
                        
                        # 7. Generate report
                        report_generator = CompetitorReportGenerator()
                        report = await report_generator.generate_report(
                            account_id=account_id,
                            platform=platform,
                            handle=handle,
                            display_name=display_name,
                            follower_count=follower_count,
                            account_audit=account_audit,
                            funnel_map=funnel_map,
                            ranking=ranking,
                            posts_data=posts_data
                        )
                        
                        # 8. Add posting time analysis to report
                        # (Extend report model to include this)
                        
                        # 9. Save report
                        report_id = await report_generator.save_report(report)
                        logger.info(f"Report generated: {report_id} for @{handle}")
                        
                        reports_generated += 1
                        
                    except Exception as e:
                        logger.error(f"Error generating report for @{handle}: {e}", exc_info=True)
                        errors.append({"account": handle, "error": str(e)})
                
                logger.info(f"Weekly reports complete: {reports_generated} generated, {len(errors)} errors")
                
                return {
                    "success": True,
                    "reports_generated": reports_generated,
                    "errors": errors,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error in weekly report generation: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
    
    return asyncio.run(_generate())


@shared_task(name='tasks.competitor_weekly_reports.generate_cross_competitor_insights')
def generate_cross_competitor_insights():
    """
    Generate cross-competitor insights and hook ideas.
    Analyzes patterns across all competitors and generates actionable recommendations.
    """
    import asyncio
    
    async def _generate():
        try:
            logger.info("Starting cross-competitor insights generation")
            
            # Get all active competitor accounts
            collector = CompetitorCollector()
            query = text("""
                SELECT DISTINCT account_id
                FROM competitor_accounts
                WHERE is_active = true
            """)
            
            with collector.engine.connect() as conn:
                result = conn.execute(query)
                account_ids = [str(row[0]) for row in result.fetchall()]
            
            if not account_ids:
                logger.warning("No active competitor accounts found")
                return {"success": False, "error": "No accounts"}
            
            logger.info(f"Analyzing {len(account_ids)} competitor accounts")
            
            # 1. Generate hook ideas across all competitors
            hook_generator = HookGenerator()
            hook_result = await hook_generator.generate_hooks(
                competitor_account_ids=account_ids,
                num_hooks=20,
                min_confidence=75.0
            )
            
            # 2. Analyze posting times across all competitors
            posting_analyzer = PostingTimeAnalyzer()
            posting_recommendation = await posting_analyzer.analyze_multiple_accounts(
                account_ids=account_ids,
                days_back=90
            )
            
            # 3. Save insights (could create a new table for cross-competitor insights)
            logger.info(f"Generated {len(hook_result.hooks_generated)} hook ideas")
            logger.info(f"Top posting hours: {posting_recommendation.best_hours}")
            
            return {
                "success": True,
                "hook_ideas_count": len(hook_result.hooks_generated),
                "top_posting_hours": posting_recommendation.best_hours,
                "top_posting_days": posting_recommendation.best_days,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating cross-competitor insights: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    return asyncio.run(_generate())

