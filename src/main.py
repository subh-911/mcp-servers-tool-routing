"""Main FastAPI application"""

import structlog
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import discovery, health, servers, tools
from src.core.config import get_config
from src.core.exceptions import MCPToolRouterError
from src.core.router import create_router_from_config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(structlog.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Application lifespan manager

    Handles startup and shutdown events
    """
    # Startup
    logger.info("application_starting")

    try:
        # Load configuration
        config = get_config()
        logger.info(
            "configuration_loaded",
            servers_count=len(config.get_enabled_servers()),
        )

        # Create and initialize router
        router = await create_router_from_config()
        app.state.router = router

        logger.info(
            "router_initialized",
            servers=router.list_servers(),
            tools_count=len(router.list_tools()),
        )

        logger.info("application_started")

        yield

    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise

    finally:
        # Shutdown
        logger.info("application_shutting_down")

        if hasattr(app.state, "router"):
            await app.state.router.shutdown()

        logger.info("application_shutdown_complete")


# Create FastAPI application
def create_app() -> FastAPI:
    """
    Create and configure FastAPI application

    Returns:
        Configured FastAPI application
    """
    config = get_config()
    settings = config.settings

    app = FastAPI(
        title="MCP Tool Router",
        description="Production-quality MCP Tool Router with FastAPI",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register exception handlers
    @app.exception_handler(MCPToolRouterError)
    async def mcp_exception_handler(
        request: Request, exc: MCPToolRouterError
    ) -> JSONResponse:
        """Handle MCP Tool Router exceptions"""
        logger.warning(
            "mcp_exception",
            error=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors"""
        logger.warning(
            "validation_error",
            errors=exc.errors(),
            path=request.url.path,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle general exceptions"""
        logger.error(
            "unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)},
            },
        )

    # Register routes
    app.include_router(tools.router, prefix="/api/v1")
    app.include_router(servers.router, prefix="/api/v1")
    app.include_router(discovery.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information"""
        return {
            "name": "MCP Tool Router",
            "version": "1.0.0",
            "description": "Production-quality MCP Tool Router with FastAPI",
            "docs": "/api/docs",
            "health": "/api/v1/health",
        }

    # Readiness probe
    @app.get("/ready", tags=["Health & Monitoring"])
    async def readiness() -> Dict[str, Any]:
        """Readiness probe for container orchestration"""
        return {"status": "ready"}

    # Liveness probe
    @app.get("/alive", tags=["Health & Monitoring"])
    async def liveness() -> Dict[str, Any]:
        """Liveness probe for container orchestration"""
        return {"status": "alive"}

    logger.info("fastapi_application_created")

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    settings = config.settings

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
