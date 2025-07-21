import google.generativeai as genai
from datetime import datetime
from typing import Dict, List

class IntentClassificationAgent:
    def __init__(self, gemini_model):
        self.model = gemini_model
        self.current_time = datetime(2025, 7, 21, 13, 56, 2)
        
    def classify_intent(self, user_input: str) -> Dict:
        """Classify user intent using LLM"""
        classification_prompt = f"""
        Current Time: {self.current_time}
        User: A4xMimic
        
        Classify this user request into the most appropriate category:
        
        User Input: "{user_input}"
        
        Intent Categories:
        1. RESTAURANT_BOOKING - Finding restaurants, booking tables, dining plans
           Examples: "book restaurant", "find dinner place", "team dinner"
           
        2. EMAIL_COMMUNICATION - Sending emails, messages, birthday wishes, notifications
           Examples: "mail mayank", "send birthday wishes", "email team"
           
        3. CALENDAR_SCHEDULING - Meetings, appointments, checking availability
           Examples: "schedule meeting", "check availability", "book meeting room"
           
        4. EVENT_PLANNING - Parties, celebrations, organizing events
           Examples: "plan birthday party", "organize celebration", "team event"
           
        5. GENERAL_TASK - Reminders, notes, other tasks
           Examples: "remind me", "create note", "set alarm"
        
        Return ONLY JSON format:
        {{
            "intent": "CATEGORY_NAME",
            "confidence": 0.95,
            "entities": ["extracted", "key", "entities"],
            "reasoning": "Brief explanation"
        }}
        """
        
        try:
            response = self.model.generate_content(classification_prompt)
            response_text = response.text.strip()
            
            # Clean JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end]
            
            import json
            result = json.loads(response_text)
            
            return {
                "success": True,
                "intent": result.get("intent", "GENERAL_TASK"),
                "confidence": result.get("confidence", 0.5),
                "entities": result.get("entities", []),
                "reasoning": result.get("reasoning", ""),
                "timestamp": self.current_time.isoformat()
            }
            
        except Exception as e:
            # Fallback classification based on keywords
            return self._fallback_classification(user_input)
    
    def _fallback_classification(self, user_input: str) -> Dict:
        """Fallback classification using keyword matching"""
        user_lower = user_input.lower()
        
        # Email keywords
        email_keywords = ['mail', 'email', 'send', 'message', 'birthday', 'wishes', 'greeting', 'notify']
        if any(keyword in user_lower for keyword in email_keywords):
            return {
                "success": True,
                "intent": "EMAIL_COMMUNICATION",
                "confidence": 0.8,
                "entities": [],
                "reasoning": "Keyword-based classification",
                "timestamp": self.current_time.isoformat()
            }
        
        # Restaurant keywords
        restaurant_keywords = ['restaurant', 'dinner', 'lunch', 'food', 'book', 'table', 'dining', 'eat']
        if any(keyword in user_lower for keyword in restaurant_keywords):
            return {
                "success": True,
                "intent": "RESTAURANT_BOOKING",
                "confidence": 0.8,
                "entities": [],
                "reasoning": "Keyword-based classification",
                "timestamp": self.current_time.isoformat()
            }
        
        # Calendar keywords
        calendar_keywords = ['meeting', 'schedule', 'appointment', 'calendar', 'availability', 'book meeting']
        if any(keyword in user_lower for keyword in calendar_keywords):
            return {
                "success": True,
                "intent": "CALENDAR_SCHEDULING", 
                "confidence": 0.8,
                "entities": [],
                "reasoning": "Keyword-based classification",
                "timestamp": self.current_time.isoformat()
            }
        
        # Default to general task
        return {
            "success": True,
            "intent": "GENERAL_TASK",
            "confidence": 0.6,
            "entities": [],
            "reasoning": "Default classification",
            "timestamp": self.current_time.isoformat()
        }