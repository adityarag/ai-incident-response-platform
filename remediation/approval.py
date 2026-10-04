"""
Human-in-the-Loop Approval Workflow.

Enforces operator oversight for HIGH and CRITICAL risk actions before
execution is authorized.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from remediation.schemas import ActionRequest, RemediationStatus

logger = logging.getLogger("remediation-approval")


class ApprovalManager:
    """
    Manages review and approval lifecycle for high-risk operations.
    """

    def __init__(self):
        self._requests: Dict[str, ActionRequest] = {}

    def register_request(self, action: ActionRequest) -> ActionRequest:
        """Registers an action for human review if approval is needed."""
        self._requests[action.action_id] = action
        if action.requires_human_approval and action.status == RemediationStatus.PENDING_APPROVAL:
            logger.info(
                f"[!] Action {action.action_id} ({action.action_type} on {action.target_service}) "
                f"queued for human operator approval [Risk: {action.risk_level.value}]."
            )
        return action

    def list_pending_requests(self) -> List[ActionRequest]:
        """Returns all actions awaiting human operator decision."""
        return [
            req for req in self._requests.values()
            if req.status == RemediationStatus.PENDING_APPROVAL
        ]

    def get_request(self, action_id: str) -> Optional[ActionRequest]:
        """Retrieves an action request by its ID."""
        return self._requests.get(action_id)

    def approve_action(
        self,
        action_id: str,
        approver: str = "human_operator",
    ) -> ActionRequest:
        """
        Approves an action, authorizing it for execution.
        """
        action = self._requests.get(action_id)
        if not action:
            raise KeyError(f"Action '{action_id}' not found.")

        if action.status != RemediationStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve action in '{action.status.value}' state.")

        action.status = RemediationStatus.APPROVED
        action.approver = approver
        action.approval_timestamp = datetime.now(timezone.utc)
        logger.info(f"[+] Action {action_id} approved by '{approver}'.")
        return action

    def reject_action(
        self,
        action_id: str,
        approver: str = "human_operator",
        reason: str = "Rejected by operator",
    ) -> ActionRequest:
        """
        Rejects an action, stopping execution and escalating.
        """
        action = self._requests.get(action_id)
        if not action:
            raise KeyError(f"Action '{action_id}' not found.")

        action.status = RemediationStatus.REJECTED
        action.approver = approver
        action.rejection_reason = reason
        action.approval_timestamp = datetime.now(timezone.utc)
        logger.warning(f"[-] Action {action_id} rejected by '{approver}': {reason}")
        return action
