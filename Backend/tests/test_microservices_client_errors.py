"""HTTP-boundary tests for downstream service failure semantics."""
import pytest
from aiohttp import web

from services.microservices_client import MicroservicesClient, ServiceCallError


@pytest.fixture
async def service_url():
    async def titles(_request):
        return web.json_response({"titles": ["A real title"]})

    async def blocked(_request):
        return web.json_response(
            {"error": "script_hub_required"}, status=409
        )

    app = web.Application()
    app.router.add_post("/titles", titles)
    app.router.add_post("/blocked", blocked)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_successful_list_response_is_returned(service_url):
    client = MicroservicesClient()
    client.services["ai"] = service_url

    result = await client._call("ai", "/titles", {})

    assert result == {"titles": ["A real title"]}


@pytest.mark.asyncio
async def test_non_success_status_is_not_converted_to_empty_list(service_url):
    client = MicroservicesClient()
    client.services["ai"] = service_url

    with pytest.raises(ServiceCallError) as error:
        await client._call("ai", "/blocked", {})

    assert error.value.status_code == 409
    assert error.value.service == "ai"
    assert error.value.endpoint == "/blocked"


@pytest.mark.asyncio
async def test_connection_failure_is_explicit():
    client = MicroservicesClient()
    client.services["ai"] = "http://127.0.0.1:1"
    client.timeout = 0.2

    with pytest.raises(ServiceCallError, match="request failed"):
        await client._call("ai", "/titles", {})

