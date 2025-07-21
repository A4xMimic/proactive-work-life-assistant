from typing import Dict, List, Any
import re
from datetime import datetime, timedelta
import google.generativeai as genai

from utils.logger import setup_logger

logger = setup_logger(__name__)

class PlanningAgent:
    """Agent responsible for breaking down high-level goals into actionable plans"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.available_models = []
        
    def initialize_model(self, api_key: str):
        """Initialize the Gemini model with current available models"""
        if not self.model:
            try:
                genai.configure(api_key=api_key)
                
                # Get available models
                self.available_models = [m.name for m in genai.list_models() 
                                       if 'generateContent' in m.supported_generation_methods]
                
                # Updated model preferences (as of July 2024+)
                model_preferences = [
                    'gemini-2.0-flash',
                    'gemini-1.5-flash',
                    'gemini-1.5-pro',
                    'models/gemini-2.0-flash',
                    'models/gemini-1.5-flash',
                    'models/gemini-1.5-pro'
                ]
                
                logger.info(f"Available models: {self.available_models}")
                
                for model_name in model_preferences:
                    if model_name in self.available_models:
                        try:
                            self.model = genai.GenerativeModel(model_name)
                            logger.info(f"Successfully initialized model: {model_name}")
                            return True
                        except Exception as e:
                            logger.warning(f"Failed to initialize {model_name}: {str(e)}")
                            continue
                
                # If no preferred model works, try the first available one
                if self.available_models:
                    first_model = self.available_models[0]
                    try:
                        self.model = genai.GenerativeModel(first_model)
                        logger.info(f"Using fallback model: {first_model}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to initialize fallback model {first_model}: {str(e)}")
                
                logger.error("No suitable models available")
                return False
                
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {str(e)}")
                return False
        return True
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return self.available_models
    
    async def create_plan(self, user_goal: str, session_state: Dict) -> Dict:
        """Create a structured plan from a high-level goal"""
        try:
            # Initialize model if needed
            if not self.model and session_state.get('gemini_key'):
                if not self.initialize_model(session_state['gemini_key']):
                    return {
                        "success": False, 
                        "message": f"Failed to initialize Gemini model. Available models: {self.available_models}"
                    }
            
            if not self.model:
                return {"success": False, "message": "Gemini API key not configured"}
            
            # Analyze the goal and create a structured plan
            plan_prompt = self.create_planning_prompt(user_goal, session_state)
            
            response = self.model.generate_content(plan_prompt)
            plan_analysis = response.text
            
            # Parse the plan analysis into structured data
            structured_plan = self.parse_plan_analysis(plan_analysis, user_goal, session_state)
            
            return {
                "success": True,
                "plan": structured_plan,
                "analysis": plan_analysis
            }
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            return {"success": False, "message": f"Failed to create plan: {str(e)}"}
    
    def create_planning_prompt(self, user_goal: str, session_state: Dict) -> str:
        """Create a detailed prompt for plan generation"""
        
        user_context = {
            "default_location": session_state.get('default_location', 'Not specified'),
            "team_size": session_state.get('team_size', 'Not specified'),
            "preferred_cuisine": session_state.get('preferred_cuisine', 'Not specified'),
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "current_time": datetime.now().strftime("%H:%M")
        }
        
        prompt = f"""
You are an expert planning assistant. Analyze the following user goal and create a structured execution plan.

USER GOAL: {user_goal}

USER CONTEXT:
- Default Location: {user_context['default_location']}
- Default Team Size: {user_context['team_size']}
- Preferred Cuisines: {user_context['preferred_cuisine']}
- Current Date: {user_context['current_date']}
- Current Time: {user_context['current_time']}

Please analyze this goal and provide:

1. TASK TYPE: Classify this as one of:
   - restaurant_booking
   - event_planning
   - meeting_scheduling
   - travel_planning
   - general_assistance

2. KEY REQUIREMENTS: Extract specific requirements like:
   - Location/venue preferences
   - Date/time constraints
   - Number of people involved
   - Budget considerations
   - Special preferences or constraints

3. EXECUTION STEPS: Break down into logical steps:
   - What research is needed?
   - What external services to query?
   - What user inputs are required?
   - What final actions need to be taken?

4. POTENTIAL CHALLENGES: Identify possible issues:
   - Availability conflicts
   - Limited options
   - Booking difficulties
   - Communication needs

5. SUCCESS CRITERIA: Define what constitutes success:
   - What deliverables are expected?
   - How will we measure completion?

Format your response as a structured analysis that I can parse programmatically.
Be specific about dates, times, locations, and requirements.
"""
        return prompt
    
    def parse_plan_analysis(self, analysis: str, original_goal: str, session_state: Dict) -> Dict:
        """Parse the LLM analysis into a structured plan"""
        
        # Extract task type
        task_type = self.extract_task_type(analysis)
        
        # Extract requirements
        requirements = self.extract_requirements(analysis, session_state)
        
        # Extract execution steps
        steps = self.extract_execution_steps(analysis)
        
        # Create structured plan
        plan = {
            "original_goal": original_goal,
            "task_type": task_type,
            "requirements": requirements,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "status": "planning"
        }
        
        return plan
    
    def extract_task_type(self, analysis: str) -> str:
        """Extract task type from analysis"""
        task_types = [
            "restaurant_booking",
            "event_planning", 
            "meeting_scheduling",
            "travel_planning",
            "general_assistance"
        ]
        
        analysis_lower = analysis.lower()
        
        # Look for explicit task type mentions
        for task_type in task_types:
            if task_type.replace("_", " ") in analysis_lower or task_type in analysis_lower:
                return task_type
        
        # Default classification based on keywords
        if any(word in analysis_lower for word in ["restaurant", "dinner", "lunch", "eat", "food"]):
            return "restaurant_booking"
        elif any(word in analysis_lower for word in ["meeting", "call", "discussion", "sync"]):
            return "meeting_scheduling"
        elif any(word in analysis_lower for word in ["event", "party", "celebration", "gathering"]):
            return "event_planning"
        elif any(word in analysis_lower for word in ["travel", "trip", "flight", "hotel"]):
            return "travel_planning"
        else:
            return "general_assistance"
    
    def extract_requirements(self, analysis: str, session_state: Dict) -> Dict:
        """Extract specific requirements from analysis"""
        requirements = {}
        
        # Location extraction
        location_patterns = [
            r"location[:\s]+([^\n]+)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, analysis, re.IGNORECASE)
            if match:
                requirements["location"] = match.group(1).strip()
                break
        
        if "location" not in requirements:
            requirements["location"] = session_state.get('default_location', 'Not specified')
        
        # Party size extraction
        size_patterns = [
            r"(\d+)\s*people",
            r"(\d+)\s*person",
            r"team\s+of\s+(\d+)",
            r"(\d+)\s*members"
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, analysis, re.IGNORECASE)
            if match:
                requirements["party_size"] = int(match.group(1))
                break
        
        if "party_size" not in requirements:
            requirements["party_size"] = session_state.get('team_size', 6)
        
        # Time preferences
        time_preferences = self.extract_time_preferences(analysis)
        requirements["time_preferences"] = time_preferences
        
        # Cuisine preferences
        cuisines = ["indian", "chinese", "italian", "mexican", "thai", "mediterranean", "biryani"]
        mentioned_cuisines = []
        
        for cuisine in cuisines:
            if cuisine in analysis.lower():
                mentioned_cuisines.append(cuisine.title())
        
        if mentioned_cuisines:
            requirements["cuisine"] = mentioned_cuisines
        else:
            requirements["cuisine"] = session_state.get('preferred_cuisine', ['Indian'])
        
        return requirements
    
    def extract_time_preferences(self, analysis: str) -> List[str]:
        """Extract time preferences from analysis"""
        time_prefs = []
        
        # Look for specific days
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            if day in analysis.lower():
                time_prefs.append(day.title())
        
        # Look for relative time references
        if "next week" in analysis.lower():
            # Generate next week dates
            today = datetime.now()
            next_week_start = today + timedelta(days=(7 - today.weekday()))
            for i in range(7):
                date = next_week_start + timedelta(days=i)
                time_prefs.append(date.strftime("%Y-%m-%d"))
        
        if "this week" in analysis.lower():
            # Generate this week dates
            today = datetime.now()
            for i in range(7):
                date = today + timedelta(days=i)
                time_prefs.append(date.strftime("%Y-%m-%d"))
        
        # Default to next 7 days if nothing specified
        if not time_prefs:
            today = datetime.now()
            for i in range(1, 8):
                date = today + timedelta(days=i)
                time_prefs.append(date.strftime("%Y-%m-%d"))
        
        return time_prefs
    
    def extract_execution_steps(self, analysis: str) -> List[Dict]:
        """Extract execution steps from analysis"""
        # Default steps for restaurant booking
        default_steps = [
            {
                "title": "Goal Analysis",
                "description": "Analyze user requirements and preferences",
                "status": "completed"
            },
            {
                "title": "Restaurant Research", 
                "description": "Find suitable restaurants based on location, cuisine, and ratings",
                "status": "pending"
            },
            {
                "title": "Availability Check",
                "description": "Check team calendar availability for proposed dates",
                "status": "pending"
            },
            {
                "title": "Option Presentation",
                "description": "Present curated options to user for selection",
                "status": "pending"
            },
            {
                "title": "Reservation & Booking",
                "description": "Make restaurant reservation and create calendar events",
                "status": "pending"
            }
        ]
        
        return default_steps