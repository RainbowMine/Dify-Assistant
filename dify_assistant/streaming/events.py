"""
SSE Streaming Event Models

Defines various streaming events returned by the Dify API.
"""

from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from dify_assistant.models.common import RetrieverResource, Usage


class StreamEventType(str, Enum):
    """
    Streaming Event Types
    """

    # Chat/Completion events
    MESSAGE = "message"
    """Message content chunk"""

    MESSAGE_END = "message_end"
    """Message end"""

    MESSAGE_FILE = "message_file"
    """Message file"""

    MESSAGE_REPLACE = "message_replace"
    """Message replace"""

    # Agent events
    AGENT_MESSAGE = "agent_message"
    """Agent message"""

    AGENT_THOUGHT = "agent_thought"
    """Agent thought process"""

    # TTS events
    TTS_MESSAGE = "tts_message"
    """TTS audio message"""

    TTS_MESSAGE_END = "tts_message_end"
    """TTS message end"""

    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    """Workflow started"""

    WORKFLOW_FINISHED = "workflow_finished"
    """Workflow finished"""

    NODE_STARTED = "node_started"
    """Node started"""

    NODE_FINISHED = "node_finished"
    """Node finished"""

    PARALLEL_BRANCH_STARTED = "parallel_branch_started"
    """Parallel branch started"""

    PARALLEL_BRANCH_FINISHED = "parallel_branch_finished"
    """Parallel branch finished"""

    # Common events
    ERROR = "error"
    """Error event"""

    PING = "ping"
    """Heartbeat event"""


class BaseStreamEvent(BaseModel):
    """
    Base Streaming Event
    """

    event: StreamEventType


class MessageEvent(BaseStreamEvent):
    """
    Message Event

    Streaming message content chunk.

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        conversation_id: Conversation ID
        answer: Response content chunk
        created_at: Creation timestamp
    """

    event: StreamEventType = StreamEventType.MESSAGE
    task_id: str
    message_id: str
    conversation_id: Optional[str] = None
    answer: str
    created_at: int


class MessageEndEvent(BaseStreamEvent):
    """
    Message End Event

    Indicates the end of message stream, contains complete metadata.

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        conversation_id: Conversation ID
        metadata: Metadata (contains usage and retriever_resources)
    """

    event: StreamEventType = StreamEventType.MESSAGE_END
    task_id: str
    message_id: str
    conversation_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def usage(self) -> Optional[Usage]:
        """Get token usage"""
        usage_data = self.metadata.get("usage")
        if usage_data:
            return Usage.model_validate(usage_data)
        return None

    @property
    def retriever_resources(self) -> Optional[list[RetrieverResource]]:
        """Get retriever resources"""
        resources_data = self.metadata.get("retriever_resources")
        if resources_data:
            return [RetrieverResource.model_validate(r) for r in resources_data]
        return None


class MessageFileEvent(BaseStreamEvent):
    """
    Message File Event

    Attributes:
        event: Event type
        id: File ID
        type: File type
        belongs_to: Belongs to
        url: File URL
        conversation_id: Conversation ID
    """

    event: StreamEventType = StreamEventType.MESSAGE_FILE
    id: str
    type: str
    belongs_to: str
    url: str
    conversation_id: Optional[str] = None


class AgentMessageEvent(BaseStreamEvent):
    """
    Agent Message Event

    Message content chunk in Agent mode.

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        conversation_id: Conversation ID
        answer: Response content chunk
        created_at: Creation timestamp
    """

    event: StreamEventType = StreamEventType.AGENT_MESSAGE
    task_id: str
    message_id: str
    conversation_id: Optional[str] = None
    answer: str
    created_at: int


class AgentThoughtEvent(BaseStreamEvent):
    """
    Agent Thought Event

    Agent's thought process.

    Attributes:
        event: Event type
        id: Thought ID
        task_id: Task ID
        message_id: Message ID
        position: Position index
        thought: Thought content
        observation: Observation result
        tool: Tool used
        tool_input: Tool input
        created_at: Creation timestamp
        message_files: Associated message files
        conversation_id: Conversation ID
    """

    event: StreamEventType = StreamEventType.AGENT_THOUGHT
    id: str
    task_id: str
    message_id: str
    position: int
    thought: str
    observation: str = ""
    tool: str = ""
    tool_input: str = ""
    created_at: int
    message_files: list[str] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class TtsMessageEvent(BaseStreamEvent):
    """
    TTS Message Event

    Audio chunk from text-to-speech synthesis.

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        audio: Base64 encoded audio data
        created_at: Creation timestamp
    """

    event: StreamEventType = StreamEventType.TTS_MESSAGE
    task_id: str
    message_id: str
    audio: str
    created_at: int


class TtsMessageEndEvent(BaseStreamEvent):
    """
    TTS Message End Event

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        audio: Base64 encoded audio data
        created_at: Creation timestamp
    """

    event: StreamEventType = StreamEventType.TTS_MESSAGE_END
    task_id: str
    message_id: str
    audio: str = ""
    created_at: int


class WorkflowStartedEvent(BaseStreamEvent):
    """
    Workflow Started Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Workflow data
    """

    event: StreamEventType = StreamEventType.WORKFLOW_STARTED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class WorkflowFinishedEvent(BaseStreamEvent):
    """
    Workflow Finished Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Workflow data (contains status, outputs, error, etc.)
    """

    event: StreamEventType = StreamEventType.WORKFLOW_FINISHED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class NodeStartedEvent(BaseStreamEvent):
    """
    Node Started Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Node data
    """

    event: StreamEventType = StreamEventType.NODE_STARTED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class NodeFinishedEvent(BaseStreamEvent):
    """
    Node Finished Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Node data (contains outputs, status, etc.)
    """

    event: StreamEventType = StreamEventType.NODE_FINISHED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class ParallelBranchStartedEvent(BaseStreamEvent):
    """
    Parallel Branch Started Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Branch data
    """

    event: StreamEventType = StreamEventType.PARALLEL_BRANCH_STARTED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class ParallelBranchFinishedEvent(BaseStreamEvent):
    """
    Parallel Branch Finished Event

    Attributes:
        event: Event type
        task_id: Task ID
        workflow_run_id: Workflow run ID
        data: Branch data
    """

    event: StreamEventType = StreamEventType.PARALLEL_BRANCH_FINISHED
    task_id: str
    workflow_run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class MessageReplaceEvent(BaseStreamEvent):
    """
    Message Replace Event

    Used to replace previous message content.

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        conversation_id: Conversation ID
        answer: Complete content after replacement
        created_at: Creation timestamp
    """

    event: StreamEventType = StreamEventType.MESSAGE_REPLACE
    task_id: str
    message_id: str
    conversation_id: Optional[str] = None
    answer: str
    created_at: int


class ErrorEvent(BaseStreamEvent):
    """
    Error Event

    Attributes:
        event: Event type
        task_id: Task ID
        message_id: Message ID
        status: Status code
        code: Error code
        message: Error message
    """

    event: StreamEventType = StreamEventType.ERROR
    task_id: Optional[str] = None
    message_id: Optional[str] = None
    status: int = 500
    code: str = ""
    message: str = ""


class PingEvent(BaseStreamEvent):
    """
    Ping Event

    Used to keep connection alive.
    """

    event: StreamEventType = StreamEventType.PING


# Union type for type annotations
StreamEvent = Union[
    MessageEvent,
    MessageEndEvent,
    MessageFileEvent,
    MessageReplaceEvent,
    AgentMessageEvent,
    AgentThoughtEvent,
    TtsMessageEvent,
    TtsMessageEndEvent,
    WorkflowStartedEvent,
    WorkflowFinishedEvent,
    NodeStartedEvent,
    NodeFinishedEvent,
    ParallelBranchStartedEvent,
    ParallelBranchFinishedEvent,
    ErrorEvent,
    PingEvent,
]
