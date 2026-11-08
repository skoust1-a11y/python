"""Investment agents.

Specialists depend on provider contracts and the LangGraph workflow, not on vendors.
"""

from app.agents.base import Agent, AgentContext, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput, AgentOutput
from app.agents.evidence import EvidenceCollector
from app.agents.execution import execute_agent, run_agent_on_state
from app.agents.fundamental import FundamentalAnalysisAgent
from app.agents.manager import PortfolioManagerAgent
from app.agents.market import MarketAnalysisAgent
from app.agents.optimization import PortfolioOptimizationAgent
from app.agents.risk import RiskAssessmentAgent

__all__ = [
    "Agent",
    "AgentAnalysis",
    "AgentContext",
    "AgentInput",
    "AgentMetadata",
    "AgentOutput",
    "AgentRuntime",
    "EvidenceCollector",
    "FundamentalAnalysisAgent",
    "MarketAnalysisAgent",
    "PortfolioManagerAgent",
    "PortfolioOptimizationAgent",
    "RiskAssessmentAgent",
    "execute_agent",
    "run_agent_on_state",
]
