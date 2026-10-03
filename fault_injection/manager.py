"""
Fault Manager.

Manages active fault configurations per service in thread-safe memory
with optional time-to-live (TTL) expiration.
"""

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fault_injection.models import FaultConfig, FaultInjectRequest, FaultType

logger = logging.getLogger("fault-manager")


class FaultManager:
    """Singleton in-process manager for active fault configurations."""

    def __init__(self):
        self._lock = threading.Lock()
        # Map: service_name -> Dict[fault_id, FaultConfig]
        self._faults: Dict[str, Dict[str, FaultConfig]] = {}
        # Simulation flags
        self._db_failure_active: Dict[str, bool] = {}

    def inject_fault(self, req: FaultInjectRequest) -> FaultConfig:
        with self._lock:
            if req.service not in self._faults:
                self._faults[req.service] = {}

            fault_id = f"FAULT-{uuid.uuid4().hex[:8].upper()}"
            cfg = FaultConfig(
                fault_id=fault_id,
                service=req.service,
                fault_type=req.fault_type,
                endpoint=req.endpoint,
                latency_seconds=req.latency_seconds,
                error_rate=req.error_rate,
                status_code=req.status_code,
                error_message=req.error_message,
                duration_seconds=req.duration_seconds,
            )

            if req.fault_type == FaultType.DATABASE_FAILURE:
                self._db_failure_active[req.service] = True

            self._faults[req.service][fault_id] = cfg
            fault_type_str = cfg.fault_type.value if hasattr(cfg.fault_type, "value") else str(cfg.fault_type)
            logger.warning(
                f"[FAULT INJECTED] {fault_type_str} on {cfg.service} (ID: {fault_id}, duration: {cfg.duration_seconds}s)"
            )
            return cfg

    def clear_faults(self, service: Optional[str] = None, fault_id: Optional[str] = None) -> int:
        """Clears faults by ID or service, or all active faults if unspecified."""
        cleared_count = 0
        with self._lock:
            targets = [service] if service else list(self._faults.keys())
            for svc in targets:
                if svc not in self._faults:
                    continue
                if fault_id:
                    if fault_id in self._faults[svc]:
                        f = self._faults[svc].pop(fault_id)
                        if f.fault_type == FaultType.DATABASE_FAILURE:
                            self._db_failure_active[svc] = False
                        cleared_count += 1
                else:
                    count = len(self._faults[svc])
                    self._faults[svc].clear()
                    self._db_failure_active[svc] = False
                    cleared_count += count

            logger.info(f"[FAULTS CLEARED] Cleared {cleared_count} fault(s)")
            return cleared_count

    def get_active_faults(self, service: Optional[str] = None) -> List[FaultConfig]:
        """Returns all currently active non-expired faults."""
        active = []
        now = datetime.now(timezone.utc)
        with self._lock:
            targets = [service] if service else list(self._faults.keys())
            for svc in targets:
                if svc not in self._faults:
                    continue
                expired_ids = []
                for fid, cfg in self._faults[svc].items():
                    if cfg.duration_seconds:
                        elapsed = (now - cfg.created_at).total_seconds()
                        if elapsed > cfg.duration_seconds:
                            expired_ids.append(fid)
                            continue
                    active.append(cfg)

                # Clean up expired faults
                for fid in expired_ids:
                    f = self._faults[svc].pop(fid)
                    if f.fault_type == FaultType.DATABASE_FAILURE:
                        self._db_failure_active[svc] = False
                    logger.info(f"[FAULT EXPIRED] {f.fault_id} expired on {svc}")

        return active

    def is_db_failure_simulated(self, service: str) -> bool:
        with self._lock:
            return self._db_failure_active.get(service, False) or self._db_failure_active.get("all", False)


# Global singleton instance
fault_manager = FaultManager()
