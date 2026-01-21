"""
Base Agent module using official a2a-sdk.

Provides AgentExecutor base class and utilities for A2A-compatible agents.
"""
import logging
from abc import abstractmethod
from typing import Any, Optional

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    AgentSkill,
    Message,
    Part,
    TextPart,
    DataPart,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    Artifact,
)

logger = logging.getLogger(__name__)


class BaseAgentExecutor(AgentExecutor):
    """
    Base class for A2A agent executors.
    
    Extends a2a-sdk AgentExecutor with common utilities.
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize the agent executor.
        
        Args:
            agent_name: Name of this agent
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"a2a.{agent_name}")
    
    @abstractmethod
    def get_agent_card(self) -> AgentCard:
        """Return the agent's capability card."""
        pass
    
    @abstractmethod
    async def process(self, query: str, context: Optional[dict] = None) -> str:
        """
        Process a query and return response text.
        
        Args:
            query: User query text
            context: Optional context data
            
        Returns:
            Response text
        """
        pass
    
    async def execute(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """
        Execute the agent task.
        
        Args:
            context: Request context with task and message info
            event_queue: Queue for sending events back
        """
        try:
            # Extract query from context
            query = self._extract_query(context)
            self.logger.info(f"Processing: {query[:100]}...")
            
            # Send running status
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(
                            role="agent",
                            parts=[TextPart(text=f"{self.agent_name} processing...")],
                            messageId=f"working-{context.task_id}"
                        )
                    ),
                    final=False
                )
            )
            
            # Process the query
            result = await self.process(query, context.context)
            
            # Send artifact with result
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    artifact=Artifact(
                        name=f"{self.agent_name}_response",
                        parts=[TextPart(text=result)]
                    )
                )
            )
            
            # Send completed status
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    status=TaskStatus(
                        state=TaskState.completed,
                        message=Message(
                            role="agent",
                            parts=[TextPart(text="Task completed successfully")],
                            messageId=f"completed-{context.task_id}"
                        )
                    ),
                    final=True
                )
            )
            
        except Exception as e:
            self.logger.error(f"Execution failed: {e}", exc_info=True)
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    status=TaskStatus(
                        state=TaskState.failed,
                        message=Message(
                            role="agent",
                            parts=[TextPart(text=f"Error: {str(e)}")],
                            messageId=f"error-{context.task_id}"
                        )
                    ),
                    final=True
                )
            )
    
    async def cancel(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """
        Cancel the agent task.
        
        Args:
            context: Request context
            event_queue: Event queue
        """
        self.logger.info(f"Cancelling task {context.task_id}")
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        role="agent",
                        parts=[TextPart(text="Task cancelled")],
                        messageId=f"cancel-{context.task_id}"
                    )
                ),
                final=True
            )
        )
    
    def _extract_query(self, context: RequestContext) -> str:
        """Extract query text from request context."""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if isinstance(part, TextPart):
                    return part.text
                if hasattr(part, 'text'):
                    return part.text
        return ""
    
    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        tags: list[str] = None,
        examples: list[str] = None
    ) -> AgentSkill:
        """Create an agent skill."""
        return AgentSkill(
            id=skill_id,
            name=name,
            description=description,
            tags=tags or [],
            examples=examples or []
        )
