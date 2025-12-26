"""
Database Health Check Endpoints
Verify Docker/Supabase/PostgreSQL connection status
"""
import os
import socket
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import create_engine, text
from typing import Dict, Any, List

from services.event_bus import EventBus, Topics

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@router.get("/status")
async def database_status() -> Dict[str, Any]:
    """
    Comprehensive database health check.
    Checks Docker, PostgreSQL, and table status.
    """
    checks = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "unknown",
        "docker": {},
        "database": {},
        "tables": {},
    }
    
    # Check Docker ports
    docker_ports = {
        "postgres": 54322,
        "supabase_api": 54321,
        "supabase_studio": 54323,
    }
    
    checks["docker"]["ports"] = {}
    all_ports_ok = True
    for name, port in docker_ports.items():
        is_open = check_port_open("localhost", port)
        checks["docker"]["ports"][name] = {
            "port": port,
            "status": "open" if is_open else "closed"
        }
        if not is_open:
            all_ports_ok = False
    
    checks["docker"]["status"] = "healthy" if all_ports_ok else "degraded"
    
    # Check database connection
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Basic connectivity
            checks["database"]["connected"] = True
            checks["database"]["url"] = DATABASE_URL.replace(
                DATABASE_URL.split(":")[2].split("@")[0], "****"
            )  # Mask password
            
            # Database info
            version = conn.execute(text("SELECT version()")).scalar()
            checks["database"]["version"] = version[:60] + "..." if len(version) > 60 else version
            
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            checks["database"]["name"] = db_name
            
            # Connection stats
            conn_count = conn.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            )).scalar()
            checks["database"]["active_connections"] = conn_count
            
            # Table counts
            table_count = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).scalar()
            checks["tables"]["total_count"] = table_count
            
            # List important tables and their row counts
            important_tables = [
                "scheduled_posts", "posted_content", "social_media_accounts",
                "videos", "video_analysis", "top_engaged_followers"
            ]
            
            checks["tables"]["details"] = {}
            for table in important_tables:
                try:
                    row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    checks["tables"]["details"][table] = {
                        "exists": True,
                        "row_count": row_count
                    }
                except Exception as e:
                    if "does not exist" in str(e):
                        checks["tables"]["details"][table] = {
                            "exists": False,
                            "row_count": 0
                        }
                    else:
                        checks["tables"]["details"][table] = {
                            "exists": "unknown",
                            "error": str(e)[:50]
                        }
            
            checks["database"]["status"] = "healthy"
            
    except Exception as e:
        checks["database"]["connected"] = False
        checks["database"]["status"] = "error"
        checks["database"]["error"] = str(e)[:200]
    
    # Overall status
    if checks["docker"]["status"] == "healthy" and checks["database"].get("status") == "healthy":
        checks["overall_status"] = "healthy"
    elif checks["database"].get("connected"):
        checks["overall_status"] = "degraded"
    else:
        checks["overall_status"] = "unhealthy"
    
    return checks


@router.get("/tables")
async def list_tables() -> Dict[str, Any]:
    """List all tables in the public schema with row counts"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            tables = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)).fetchall()
            
            result = []
            for (table_name,) in tables:
                try:
                    count = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                    result.append({"name": table_name, "rows": count})
                except Exception:
                    result.append({"name": table_name, "rows": "error"})
            
            return {
                "total_tables": len(result),
                "tables": result
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/docker")
async def docker_status() -> Dict[str, Any]:
    """Check Docker container ports"""
    ports_to_check = {
        "supabase_db": 54322,
        "supabase_api": 54321,
        "supabase_studio": 54323,
        "supabase_inbucket": 54324,
        "backend_api": 5555,
        "frontend": 5557,
    }
    
    results = {}
    for name, port in ports_to_check.items():
        is_open = check_port_open("localhost", port)
        results[name] = {
            "port": port,
            "status": "running" if is_open else "stopped",
            "url": f"http://localhost:{port}"
        }
    
    running = sum(1 for r in results.values() if r["status"] == "running")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services_running": running,
        "services_total": len(results),
        "services": results
    }


@router.post("/test-connection")
async def test_database_connection() -> Dict[str, Any]:
    """Test database connection with a simple query"""
    try:
        engine = create_engine(DATABASE_URL)
        start = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        latency_ms = (datetime.now() - start).total_seconds() * 1000
        
        return {
            "success": True,
            "latency_ms": round(latency_ms, 2),
            "message": "Database connection successful"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Database connection failed"
        }
