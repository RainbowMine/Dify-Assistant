"""
Workflow API Response Model
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """
    Workflow Execution Status
    """

    RUNNING = "running"
    """Running"""

    SUCCEEDED = "succeeded"
    """Succeeded"""

    FAILED = "failed"
    """Failed"""

    STOPPED = "stopped"
    """Stopped"""

    PARTIAL_SUCCEEDED = "partial-succeeded"
    """Partially succeeded"""


class WorkflowData(BaseModel):
    """
    Workflow Execution Data

    Attributes:
        id: Workflow execution ID
        workflow_id: Workflow ID
        status: Execution status
        outputs: Output results
        error: Error message
        elapsed_time: Execution time (seconds)
        total_tokens: Total tokens
        total_steps: Number of execution steps
        created_at: Creation timestamp
        finished_at: Completion timestamp
    """

    id: str
    workflow_id: str
    status: WorkflowStatus
    outputs: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_time: Optional[float] = None
    total_tokens: Optional[int] = None
    total_steps: int = 0
    created_at: int
    finished_at: Optional[int] = None


class WorkflowRunResponse(BaseModel):
    """
    Workflow Execution Response (Blocking Mode)

    Blocking mode response for POST /workflows/run endpoint.

    Attributes:
        workflow_run_id: Workflow run ID
        task_id: Task ID
        data: Execution data
    """

    workflow_run_id: str = Field(..., description="Workflow run ID")
    task_id: str = Field(..., description="Task ID")
    data: WorkflowData = Field(..., description="Execution data")
