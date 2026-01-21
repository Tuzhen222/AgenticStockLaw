"""
Agent Registry - Manages agent endpoints and capabilities.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    url: str
    skills: List[str]
    version: str = "1.0.0"
    enabled: bool = True


class AgentRegistry:
    """Registry for managing agent endpoints."""
    
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default agent configurations from environment or defaults."""
        self.register(AgentInfo(
            agent_id="knowledge",
            url=os.getenv("KNOWLEDGE_AGENT_URL", "http://ai-knowledge:9101"),
            skills=["search_legal_docs", "get_article_content"],
            version="1.0.0",
            enabled=True
        ))
        
        self.register(AgentInfo(
            agent_id="validation",
            url=os.getenv("VALIDATION_AGENT_URL", "http://ai-validation:9102"),
            skills=["check_in_force", "check_amendments", "validate_info"],
            version="1.0.0",
            enabled=True
        ))
        
        self.register(AgentInfo(
            agent_id="regulatory_update",
            url=os.getenv("REGULATORY_UPDATE_AGENT_URL", "http://ai-regulatory:9103"),
            skills=["find_new_regulations", "web_search"],
            version="1.0.0",
            enabled=True
        ))
    
    def register(self, agent: AgentInfo) -> None:
        """Register an agent."""
        self._agents[agent.agent_id] = agent
    
    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        return self._agents.get(agent_id)
    
    def get_url(self, agent_id: str) -> Optional[str]:
        """Get agent URL by ID."""
        agent = self.get(agent_id)
        return agent.url if agent and agent.enabled else None
    
    def list_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def is_enabled(self, agent_id: str) -> bool:
        """Check if agent is enabled."""
        agent = self.get(agent_id)
        return agent.enabled if agent else False


# Singleton instance
agent_registry = AgentRegistry()
