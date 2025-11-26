"""Tool execution endpoints"""

import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from src.api.models.requests import BatchExecuteRequest, ExecuteToolRequest
from src.api.models.responses import (
    BatchExecutionResponse,
    ErrorResponse,
    ToolExecutionResponse,
)
from src.core.exceptions import (
    CircuitBreakerError,
    MCPToolRouterError,
    ToolExecutionError,
    ToolNotFoundError,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post(
    "/{tool_name}/execute",
    response_model=ToolExecutionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tool not found"},
        500: {"model": ErrorResponse, "description": "Execution failed"},
        503: {"model": ErrorResponse, "description": "Circuit breaker open"},
    },
    summary="Execute a specific tool",
    description="Execute a tool by name with the provided arguments",
)
async def execute_tool(
    tool_name: str,
    request_body: ExecuteToolRequest,
    request: Request,
) -> ToolExecutionResponse:
    """
    Execute a specific tool

    Args:
        tool_name: Name of the tool to execute
        request_body: Tool execution request with arguments
        request: FastAPI request object

    Returns:
        Tool execution response

    Raises:
        HTTPException: If tool not found or execution fails
    """
    router_instance = request.app.state.router

    start_time = time.time()

    try:
        logger.info(
            "api_execute_tool_request",
            tool_name=tool_name,
            arguments=request_body.arguments,
        )

        # Execute tool
        result = await router_instance.execute_tool(
            tool_name=tool_name,
            arguments=request_body.arguments,
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Get server name from tool map
        server_name = router_instance.tool_map.get(tool_name, "unknown")

        logger.info(
            "api_execute_tool_success",
            tool_name=tool_name,
            server_name=server_name,
            execution_time_ms=execution_time_ms,
        )

        return ToolExecutionResponse(
            success=True,
            tool_name=tool_name,
            server_name=server_name,
            result=result,
            execution_time_ms=execution_time_ms,
        )

    except ToolNotFoundError as e:
        logger.warning("api_execute_tool_not_found", tool_name=tool_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        )

    except CircuitBreakerError as e:
        logger.warning(
            "api_execute_tool_circuit_breaker",
            tool_name=tool_name,
            server_name=e.server_name,
            state=e.state,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.to_dict(),
        )

    except ToolExecutionError as e:
        logger.error(
            "api_execute_tool_failed",
            tool_name=tool_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )

    except MCPToolRouterError as e:
        logger.error(
            "api_execute_tool_error",
            tool_name=tool_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )

    except Exception as e:
        logger.error(
            "api_execute_tool_unexpected_error",
            tool_name=tool_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Unexpected error: {str(e)}",
                "details": {},
            },
        )


@router.post(
    "/batch",
    response_model=BatchExecutionResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Batch execution failed"},
    },
    summary="Execute multiple tools",
    description="Execute multiple tools in parallel or sequentially",
)
async def execute_batch(
    request_body: BatchExecuteRequest,
    request: Request,
) -> BatchExecutionResponse:
    """
    Execute multiple tools in batch

    Args:
        request_body: Batch execution request
        request: FastAPI request object

    Returns:
        Batch execution response
    """
    router_instance = request.app.state.router

    logger.info(
        "api_execute_batch_request",
        tool_count=len(request_body.tools),
        parallel=request_body.parallel,
    )

    results = []
    successful = 0
    failed = 0

    async def execute_single(tool_item: Any) -> ToolExecutionResponse:
        """Execute a single tool and return response"""
        nonlocal successful, failed

        start_time = time.time()

        try:
            result = await router_instance.execute_tool(
                tool_name=tool_item.tool_name,
                arguments=tool_item.arguments,
            )

            execution_time_ms = (time.time() - start_time) * 1000
            server_name = router_instance.tool_map.get(tool_item.tool_name, "unknown")

            successful += 1

            return ToolExecutionResponse(
                success=True,
                tool_name=tool_item.tool_name,
                server_name=server_name,
                result=result,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            server_name = router_instance.tool_map.get(tool_item.tool_name, "unknown")

            failed += 1

            return ToolExecutionResponse(
                success=False,
                tool_name=tool_item.tool_name,
                server_name=server_name,
                result=None,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    # Execute tools
    if request_body.parallel:
        # Parallel execution
        import asyncio

        tasks = [execute_single(tool_item) for tool_item in request_body.tools]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    else:
        # Sequential execution
        for tool_item in request_body.tools:
            result = await execute_single(tool_item)
            results.append(result)

    logger.info(
        "api_execute_batch_complete",
        total=len(request_body.tools),
        successful=successful,
        failed=failed,
    )

    return BatchExecutionResponse(
        total=len(request_body.tools),
        successful=successful,
        failed=failed,
        results=results,
    )
