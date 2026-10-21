"""Exercise the manual integration checks through a real local HTTP boundary."""
import sys
from pathlib import Path

import pytest
from aiohttp import web
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import test_microservices_integration as checks

TITLE_STATE = web.AppKey("title_state", dict)


@pytest.fixture
async def contract_service():
    async def title_contract(request):
        if request.app[TITLE_STATE]["mode"] == "false_success":
            return web.json_response({"titles": ["placeholder"]})
        return web.json_response({"error": "script_hub_required"}, status=409)

    async def unavailable(_request):
        return web.json_response({"error": "capability_unavailable"}, status=503)

    app = web.Application()
    app[TITLE_STATE] = {"mode": "blocked"}
    app.router.add_post("/api/generate/title", title_contract)
    app.router.add_post("/api/score/fate", unavailable)
    app.router.add_post("/api/classify/awareness", unavailable)
    app.router.add_post("/api/analyze/sentiment", unavailable)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    previous = checks.SERVICES["content-intelligence"]
    checks.SERVICES["content-intelligence"] = f"http://127.0.0.1:{port}"
    try:
        yield {"url": f"http://127.0.0.1:{port}", "title_state": app[TITLE_STATE]}
    finally:
        checks.SERVICES["content-intelligence"] = previous
        await runner.cleanup()


@pytest.mark.asyncio
async def test_manual_title_check_accepts_only_governed_block(contract_service, capsys):
    async with httpx.AsyncClient() as client:
        assert await checks.test_title_generation(client) is True
    assert "correctly blocked" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_manual_analysis_checks_accept_explicit_adapter_unavailability(contract_service):
    async with httpx.AsyncClient() as client:
        assert await checks.test_fate_scoring(client) is True
        assert await checks.test_awareness_classification(client) is True
        assert await checks.test_sentiment_analysis(client) is True


@pytest.mark.asyncio
async def test_manual_title_check_rejects_unreceipted_200(contract_service, capsys):
    contract_service["title_state"]["mode"] = "false_success"
    checks.SERVICES["content-intelligence"] = contract_service["url"]
    async with httpx.AsyncClient() as client:
        assert await checks.test_title_generation(client) is False
    assert "expected 409" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_manual_checker_requires_explicit_content_intelligence_target(capsys):
    previous = checks.SERVICES["content-intelligence"]
    checks.SERVICES["content-intelligence"] = ""
    try:
        assert await checks.main() == 2
    finally:
        checks.SERVICES["content-intelligence"] = previous

    output = capsys.readouterr().out
    assert "Set CONTENT_INTEL_URL" in output
    assert "Market Tape" in output
