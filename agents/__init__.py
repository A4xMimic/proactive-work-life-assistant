"""
Proactive Work-Life Assistant Agents

This package contains specialized agents for different aspects of task execution:
- Planning Agent: Goal decomposition and strategy formation
- Research Agent: External data gathering and analysis  
- Calendar Agent: Availability checking and event management
- Reservation Agent: Automated booking and web form handling
- Communication Agent: Email and invitation management
- Orchestrator: Multi-agent coordination and workflow management
"""

from .orchestrator import AgentOrchestrator
from .planning_agent import PlanningAgent
from .research_agent import ResearchAgent
from .calendar_agent import CalendarAgent
from .reservation_agent import ReservationAgent
from .communication_agent import CommunicationAgent
from .restaurant_agent import RestaurantAgent
from .email_agent import EmailCommunicationAgent
from .intent_classifier import IntentClassificationAgent

__all__ = [
    'AgentOrchestrator',
    'PlanningAgent', 
    'ResearchAgent',
    'CalendarAgent',
    'ReservationAgent',
    'CommunicationAgent',
    'RestaurantAgent',
    'EmailCommunicationAgent',
    'IntentClassificationAgent'
]

__version__ = "1.0.0"

