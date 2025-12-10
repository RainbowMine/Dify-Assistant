"""
API Endpoint Wrapper Module

Provides high-level API wrappers to simplify interactions with Dify API.
"""

from dify_assistant.api.chat import AsyncChatAPI, SyncChatAPI
from dify_assistant.api.completion import AsyncCompletionAPI, SyncCompletionAPI
from dify_assistant.api.conversation import AsyncConversationAPI, SyncConversationAPI
from dify_assistant.api.dify_client import DifyClient
from dify_assistant.api.file import AsyncFileAPI, SyncFileAPI
from dify_assistant.api.workflow import AsyncWorkflowAPI, SyncWorkflowAPI

__all__ = [
    # Main client
    "DifyClient",
    # Chat API
    "AsyncChatAPI",
    "SyncChatAPI",
    # Completion API
    "AsyncCompletionAPI",
    "SyncCompletionAPI",
    # Workflow API
    "AsyncWorkflowAPI",
    "SyncWorkflowAPI",
    # Conversation API
    "AsyncConversationAPI",
    "SyncConversationAPI",
    # File API
    "AsyncFileAPI",
    "SyncFileAPI",
]
