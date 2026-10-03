"""
Fault Injection Middleware & Endpoints for FastAPI.

Intercepts requests to apply active latency, error spikes, or database faults,
and provides management endpoints (/faults/inject, /faults/clear, /faults/active).
"""

import asyncio
import logging
import random
from typing import Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from fault_injection.manager import fault_manager
from fault_injection.models import (
    FaultClearRequest,
    FaultConfig,
    FaultInjectRequest,
    FaultType,
)

logger = logging.getLogger("fault-injection")


def create_fault_router(service_name: str) -> APIRouter:
    """Creates standard management router for a service."""
    router = APIRouter(prefix="/faults", tags=["fault-injection"])

    @router.post("/inject", response_model=FaultConfig)
    def inject_fault(req: FaultInjectRequest):
        # Allow target to be explicitly this service or 'all'
        target_service = req.service if req.service in (service_name, "all") else service_name
        req.service = target_service
        return fault_manager.inject_fault(req)

    @router.post("/clear")
    def clear_faults(req: FaultClearRequest = None):
        target_service = req.service if (req and req.service) else service_name
        target_id = req.fault_id if req else None
        cleared = fault_manager.clear_faults(service=target_service, fault_id=target_id)
        return {"status": "cleared", "cleared_count": cleared, "service": target_service}

    @router.get("/active")
    def get_active():
        active = fault_manager.get_active_faults(service=service_name)
        return {"service": service_name, "active_faults": active}

    return router


def attach_fault_injection(app: FastAPI, service_name: str):
    """
    Mounts fault middleware and management routes on the target FastAPI app.
    """
    # 1. Mount standard endpoints
    router = create_fault_router(service_name)
    app.include_router(router)

    # 2. Add middleware interceptor
    @app.middleware("http")
    async def fault_injection_middleware(request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Never inject faults into internal operational routes
        if path.startswith("/faults") or path in ("/metrics", "/health", "/ready"):
            return await call_next(request)

        active_faults = fault_manager.get_active_faults(service=service_name)
        # Also check global 'all' service faults
        active_faults += fault_manager.get_active_faults(service="all")

        for fault in active_faults:
            # Check endpoint matching
            if fault.endpoint and not path.startswith(fault.endpoint):
                continue

            # A. Artificial Latency
            if fault.fault_type == FaultType.LATENCY and fault.latency_seconds > 0:
                logger.warning(
                    f"Applying simulated latency ({fault.latency_seconds}s) to {path} [Fault: {fault.fault_id}]"
                )
                await asyncio.sleep(fault.latency_seconds)

            # B. Error Spike
            elif fault.fault_type == FaultType.ERROR_SPIKE:
                if random.random() <= fault.error_rate:
                    logger.error(
                        f"Injecting simulated error ({fault.status_code}) on {path} [Fault: {fault.fault_id}]: {fault.error_message}"
                    )
                    return JSONResponse(
                        status_code=fault.status_code,
                        content={
                            "error": "FaultInjectionSimulatedError",
                            "fault_id": fault.fault_id,
                            "fault_type": fault.fault_type,
                            "service": service_name,
                            "detail": fault.error_message,
                            "path": path,
                        },
                    )

            # C. Dependency Timeout
            elif fault.fault_type == FaultType.DEPENDENCY_TIMEOUT:
                logger.error(
                    f"Simulating downstream dependency timeout on {path} [Fault: {fault.fault_id}]"
                )
                return JSONResponse(
                    status_code=504,
                    content={
                        "error": "DownstreamDependencyTimeout",
                        "fault_id": fault.fault_id,
                        "detail": "Simulated upstream gateway / dependency timeout",
                    },
                )

        # Proceed with normal request
        return await call_next(request)
