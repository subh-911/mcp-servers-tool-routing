"""Health and monitoring endpoints"""

import time

import structlog
from fastapi import APIRouter, Request

from src.api.models.responses import (
    CircuitBreakerMetrics,
    HealthResponse,
    MetricsResponse,
    RouterStatsResponse,
    ServerHealthStatus,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get overall health status",
    description="Get the health status of the router and all connected servers",
)
async def get_health(request: Request) -> HealthResponse:
    """
    Get overall health status

    Args:
        request: FastAPI request object

    Returns:
        Health status
    """
    router_instance = request.app.state.router

    logger.debug("api_health_check_request")

    # Get connected servers
    connected_servers = router_instance.client_pool.get_connected_servers()
    all_servers = router_instance.list_servers()

    # Build server health statuses
    server_statuses = []
    healthy_count = 0

    for server_name in all_servers:
        is_connected = server_name in connected_servers

        # Get circuit breaker state if available
        circuit_state = None
        last_error = None

        if (
            router_instance.circuit_breaker_enabled
            and server_name in router_instance.circuit_breakers
        ):
            cb = router_instance.circuit_breakers[server_name]
            circuit_state = cb.state.value

            # Check if circuit is open or degraded
            is_healthy = cb.is_closed and is_connected
        else:
            is_healthy = is_connected

        if is_healthy:
            healthy_count += 1

        server_statuses.append(
            ServerHealthStatus(
                name=server_name,
                healthy=is_healthy,
                connected=is_connected,
                circuit_state=circuit_state,
                last_error=last_error,
            )
        )

    # Determine overall status
    if healthy_count == len(all_servers) and len(all_servers) > 0:
        overall_status = "healthy"
    elif healthy_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    logger.debug(
        "api_health_check_success",
        status=overall_status,
        total_servers=len(all_servers),
        healthy_servers=healthy_count,
    )

    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        servers=server_statuses,
        total_servers=len(all_servers),
        healthy_servers=healthy_count,
    )


@router.get(
    "/health/servers",
    response_model=HealthResponse,
    summary="Get server health status",
    description="Get detailed health status for all servers",
)
async def get_server_health(request: Request) -> HealthResponse:
    """
    Get server health status (alias for /health)

    Args:
        request: FastAPI request object

    Returns:
        Health status
    """
    return await get_health(request)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get metrics and statistics",
    description="Get circuit breaker metrics, cache statistics, and connection pool info",
)
async def get_metrics(request: Request) -> MetricsResponse:
    """
    Get metrics and statistics

    Args:
        request: FastAPI request object

    Returns:
        Metrics response
    """
    router_instance = request.app.state.router

    logger.debug("api_metrics_request")

    # Collect circuit breaker metrics
    cb_metrics = []
    for name, cb in router_instance.circuit_breakers.items():
        status_dict = cb.get_status()
        metrics_dict = status_dict.get("metrics", {})

        cb_metrics.append(
            CircuitBreakerMetrics(
                name=name,
                state=status_dict["state"],
                failure_count=status_dict["failure_count"],
                total_requests=metrics_dict.get("total_requests", 0),
                successful_requests=metrics_dict.get("successful_requests", 0),
                failed_requests=metrics_dict.get("failed_requests", 0),
                rejected_requests=metrics_dict.get("rejected_requests", 0),
                failure_rate=metrics_dict.get("failure_rate", 0.0),
                success_rate=metrics_dict.get("success_rate", 0.0),
            )
        )

    # Get cache and pool stats
    schema_cache_stats = router_instance.schema_cache.get_stats()
    connection_pool_stats = router_instance.client_pool.get_pool_stats()

    logger.debug("api_metrics_success")

    return MetricsResponse(
        circuit_breakers=cb_metrics,
        schema_cache=schema_cache_stats,
        connection_pool=connection_pool_stats,
    )


@router.get(
    "/stats",
    response_model=RouterStatsResponse,
    summary="Get router statistics",
    description="Get comprehensive statistics about the router",
)
async def get_stats(request: Request) -> RouterStatsResponse:
    """
    Get router statistics

    Args:
        request: FastAPI request object

    Returns:
        Router statistics
    """
    router_instance = request.app.state.router

    logger.debug("api_stats_request")

    stats = router_instance.get_router_stats()

    logger.debug("api_stats_success")

    return RouterStatsResponse(**stats)
