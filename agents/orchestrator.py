import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AgentOrchestrator:
    def __init__(self, config):
        self.config = config
        self.restaurant_agent = None
        self.calendar_agent = None
        self.intent_classifier = None  # NEW
        self.email_agent = None       # NEW
        
    def initialize_intent_classifier(self, gemini_model):
        """Initialize intent classifier with Gemini model"""
        try:
            from agents.intent_classifier import IntentClassificationAgent
            self.intent_classifier = IntentClassificationAgent(gemini_model)
            logger.info("✅ Intent classifier initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize intent classifier: {str(e)}")
            self.intent_classifier = None
    
    def initialize_email_agent(self):
        """Initialize email agent"""
        try:
            from agents.email_agent import EmailCommunicationAgent
            self.email_agent = EmailCommunicationAgent()
            logger.info("✅ Email agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize email agent: {str(e)}")
            self.email_agent = None
        
    async def process_goal(self, user_input: str, session_state: Dict) -> Dict:
        """ENHANCED: Process user goal with intent classification"""
        try:
            # STEP 1: CLASSIFY INTENT FIRST
            intent_result = self._classify_user_intent(user_input)
            intent = intent_result.get("intent", "RESTAURANT_BOOKING")
            confidence = intent_result.get("confidence", 0.5)
            
            logger.info(f"🧠 Intent Classification: {intent} (confidence: {confidence})")
            
            # STEP 2: ROUTE TO APPROPRIATE HANDLER
            if intent == "EMAIL_COMMUNICATION":
                return await self._handle_email_request(user_input, session_state)
            elif intent == "CALENDAR_SCHEDULING":
                return await self.handle_calendar_request(user_input, session_state)
            elif intent in ["RESTAURANT_BOOKING", "EVENT_PLANNING"]:
                return await self.handle_restaurant_request(user_input, session_state)
            else:  # GENERAL_TASK
                return await self._handle_general_request(user_input, session_state)
                
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}")
            return {
                "type": "error",
                "content": f"I encountered an error processing your request: {str(e)}"
            }
    
    def _classify_user_intent(self, user_input: str) -> Dict:
        """Classify user intent using LLM or fallback"""
        if self.intent_classifier:
            try:
                result = self.intent_classifier.classify_intent(user_input)
                logger.info(f"🤖 LLM Classification: {result.get('intent')} - {result.get('reasoning')}")
                return result
            except Exception as e:
                logger.warning(f"LLM classification failed: {str(e)}, using fallback")
        
        # Enhanced fallback classification
        return self._enhanced_fallback_classification(user_input)
    
    def _enhanced_fallback_classification(self, user_input: str) -> Dict:
        """Enhanced fallback classification with better logic"""
        user_lower = user_input.lower()
        
        # 1. EMAIL COMMUNICATION - Explicit email requests
        email_keywords = [
            'mail', 'email', 'send message', 'birthday wishes', 'wishes', 
            'message to', 'email to', 'send to', 'notify', 'inform', 'tell'
        ]
        email_score = sum(1 for keyword in email_keywords if keyword in user_lower)
        
        # 2. RESTAURANT/EVENT PLANNING - Higher priority for party planning
        restaurant_event_keywords = [
            # Event planning
            'organize', 'birthday party', 'celebration', 'party', 'event',
            'plan', 'celebrate',
            # Restaurant/Food
            'restaurant', 'dinner', 'lunch', 'food', 'eat', 'dining',
            'great food', 'vibes', 'ambiance', 'place', 'venue',
            # Locations  
            'delhi', 'mumbai', 'hyderabad', 'bangalore', 'cannaught place',
            'connaught place', 'cp', 'near office',
            # Group context
            'team', 'group', 'people', '6-person', 'colleagues',
            # Action words
            'go somewhere', 'book', 'reservation'
        ]
        restaurant_score = sum(1 for keyword in restaurant_event_keywords if keyword in user_lower)
        
        # 3. CALENDAR SCHEDULING - Only if no restaurant context
        calendar_keywords = ['meeting', 'schedule', 'availability', 'calendar', 'appointment']
        calendar_score = sum(1 for keyword in calendar_keywords if keyword in user_lower)
        
        # DECISION LOGIC
        if email_score >= 1 and restaurant_score == 0:
            return {
                "intent": "EMAIL_COMMUNICATION",
                "confidence": 0.8,
                "reasoning": f"Email keywords detected (score: {email_score})"
            }
        elif restaurant_score >= 1:
            return {
                "intent": "RESTAURANT_BOOKING",
                "confidence": 0.9,
                "reasoning": f"Restaurant/event keywords detected (score: {restaurant_score})"
            }
        elif calendar_score >= 1:
            return {
                "intent": "CALENDAR_SCHEDULING",
                "confidence": 0.7,
                "reasoning": f"Calendar keywords detected (score: {calendar_score})"
            }
        else:
            return {
                "intent": "GENERAL_TASK",
                "confidence": 0.6,
                "reasoning": "No specific intent detected"
            }
    
    async def _handle_email_request(self, user_input: str, session_state: Dict) -> Dict:
        """Handle email communication requests"""
        try:
            # Initialize email agent if needed
            if not self.email_agent:
                self.initialize_email_agent()
            
            if self.email_agent:
                logger.info("📧 Routing to email agent")
                return await self.email_agent.process_email_request(user_input, session_state)
            else:
                return {
                    "type": "text",
                    "content": """📧 **Email Request Detected!**
                    
I understand you want to send an email, but the email agent is not available.

**For now, try:**
- 🍽️ "Book birthday celebration restaurant for Mayank"
- 🎉 "Organize birthday party with team dinner"

Email features will be available soon!
                    """
                }
                
        except Exception as e:
            logger.error(f"Email request error: {str(e)}")
            return {
                "type": "error",
                "content": f"Error processing email request: {str(e)}"
            }
    
    async def _handle_general_request(self, user_input: str, session_state: Dict) -> Dict:
        """Handle general/unknown requests"""
        return {
            "type": "text",
            "content": f"""🤖 **I understand you said:** "{user_input}"

**I currently specialize in:**
- 🍽️ **Restaurant Booking** - "Find restaurants in Delhi"
- 🎉 **Event Planning** - "Organize birthday party for team"
- 📅 **Calendar Integration** - "Check team availability" 
- 📧 **Email Features** - "Mail birthday wishes"

**Try asking me to:**
- "Organize a birthday party for my team in Delhi tomorrow"
- "Book a restaurant with great food and vibes near Connaught Place"
- "Check team availability for next Tuesday"

**Current Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
**User:** A4xMimic
            """
        }

    # Keep ALL your existing restaurant and calendar methods UNCHANGED
    async def handle_restaurant_request(self, user_input: str, session_state: Dict) -> Dict:
        """Handle restaurant search and booking requests with unique results"""
        try:
            # Lazy import to avoid circular imports
            from agents.restaurant_agent import RestaurantAgent
            from agents.calendar_agent import CalendarAgent
            
            if not self.restaurant_agent:
                self.restaurant_agent = RestaurantAgent(self.config)
            if not self.calendar_agent:
                self.calendar_agent = CalendarAgent(self.config)
            
            logger.info(f"🍽️ Processing restaurant request for: {user_input}")
            
            # Extract location from user input
            location = self.extract_location(user_input)
            if not location:
                location = "Hyderabad"  # Default location
            
            # Extract cuisine preferences
            cuisine_preferences = self.extract_cuisine(user_input)
            
            # Extract party size
            party_size = self.extract_party_size(user_input, session_state)
            
            logger.info(f"🔍 Search params - Location: {location}, Cuisine: {cuisine_preferences}, Party: {party_size}")
            
            # Search for restaurants
            restaurant_result = await self.restaurant_agent.search_restaurants(
                location=location,
                cuisine=cuisine_preferences,
                party_size=party_size,
                session_state=session_state
            )
            
            if not restaurant_result.get("success"):
                return {
                    "type": "error",
                    "content": f"Restaurant search failed: {restaurant_result.get('error', 'Unknown error')}"
                }
            
            restaurants = restaurant_result.get("restaurants", [])
            if not restaurants:
                return {
                    "type": "error",
                    "content": f"No restaurants found in {location}. Try a different location or cuisine."
                }
            
            # Get team availability for next few days
            availability_options = []
            current_date = datetime.now().date()
            
            for i in range(1, 4):  # Next 3 days
                check_date = current_date + timedelta(days=i)
                date_str = check_date.strftime("%Y-%m-%d")
                
                # Check team availability
                availability_result = await self.calendar_agent.find_availability(
                    date=date_str,
                    attendee_emails=session_state.get('team_emails', []),
                    session_state=session_state
                )
                
                if availability_result.get("success"):
                    availability_options.append({
                        "date": date_str,
                        "availability": availability_result
                    })
            
            # Combine restaurants with availability - FIXED TO AVOID DUPLICATES
            options = []
            seen_combinations = set()  # Track unique restaurant-date combinations
            unique_restaurants = set()  # Track unique restaurants
            
            # Ensure we get diverse restaurant options first
            for restaurant in restaurants[:8]:  # Look at top 8 restaurants
                restaurant_key = restaurant['name'].lower().strip()
                
                # Skip if we've already included this restaurant
                if restaurant_key in unique_restaurants:
                    continue
                
                unique_restaurants.add(restaurant_key)
                
                # For each unique restaurant, find the best availability option
                best_option = None
                best_score = 0
                
                for avail_option in availability_options:
                    availability = avail_option["availability"]
                    
                    # Create unique combination key
                    combo_key = f"{restaurant_key}_{avail_option['date']}"
                    
                    if combo_key in seen_combinations:
                        continue
                    
                    # Pick best time slot for this date
                    time_slots = availability.get("time_slots", [])
                    if time_slots:
                        best_slot = max(time_slots, key=lambda x: x["available_attendees"])
                        
                        # Score this option (prefer higher availability and sooner dates)
                        availability_score = best_slot["available_attendees"] / best_slot["total_attendees"]
                        date_score = 1.0 / (i + 1)  # Prefer sooner dates
                        total_score = availability_score + date_score
                        
                        if total_score > best_score:
                            best_score = total_score
                            best_option = {
                                "title": f"{restaurant['name']} - {avail_option['date']} at {best_slot['time']}",
                                "restaurant": restaurant,
                                "time_slot": {
                                    "date": avail_option['date'],
                                    "time": best_slot['time'],
                                    "available_attendees": best_slot['available_attendees'],
                                    "total_attendees": best_slot['total_attendees'],
                                    "attendee_emails": availability.get('attendee_emails', [])
                                },
                                "combo_key": combo_key
                            }
                
                # Add the best option for this restaurant
                if best_option:
                    seen_combinations.add(best_option["combo_key"])
                    options.append(best_option)
                    
                    # Stop if we have enough options
                    if len(options) >= 6:
                        break
            
            # If we don't have enough options, add more combinations from remaining restaurants
            if len(options) < 6:
                for restaurant in restaurants:
                    restaurant_key = restaurant['name'].lower().strip()
                    
                    for avail_option in availability_options:
                        availability = avail_option["availability"]
                        combo_key = f"{restaurant_key}_{avail_option['date']}"
                        
                        if combo_key in seen_combinations:
                            continue
                        
                        time_slots = availability.get("time_slots", [])
                        if time_slots:
                            best_slot = max(time_slots, key=lambda x: x["available_attendees"])
                            
                            options.append({
                                "title": f"{restaurant['name']} - {avail_option['date']} at {best_slot['time']}",
                                "restaurant": restaurant,
                                "time_slot": {
                                    "date": avail_option['date'],
                                    "time": best_slot['time'],
                                    "available_attendees": best_slot['available_attendees'],
                                    "total_attendees": best_slot['total_attendees'],
                                    "attendee_emails": availability.get('attendee_emails', [])
                                }
                            })
                            
                            seen_combinations.add(combo_key)
                            
                            if len(options) >= 6:
                                break
                    
                    if len(options) >= 6:
                        break
            
            if not options:
                return {
                    "type": "error",
                    "content": "No suitable restaurant and time combinations found. Please try adjusting your preferences."
                }
            
            # Sort options by restaurant rating and availability
            options.sort(key=lambda x: (
                x["restaurant"].get("rating", 0),
                x["time_slot"]["available_attendees"] / x["time_slot"]["total_attendees"]
            ), reverse=True)
            
            # Add event context if this was an event planning request
            note_suffix = ""
            if any(word in user_input.lower() for word in ['birthday', 'party', 'celebration', 'organize']):
                note_suffix = " - Perfect venues for your celebration! 🎉"
            
            return {
                "type": "options",
                "content": {
                    "options": options[:6],  # Final limit to 6 unique options
                    "note": f"Found {len(unique_restaurants)} unique restaurants in {location} with team availability{note_suffix}",
                    "search_criteria": {
                        "location": location,
                        "cuisine": cuisine_preferences,
                        "party_size": party_size,
                        "search_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "user": "A4xMimic",
                        "intent": "restaurant_booking",
                        "event_context": bool(note_suffix)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Restaurant request error: {str(e)}")
            return {
                "type": "error",
                "content": f"Error processing restaurant request: {str(e)}"
            }
    
    async def handle_calendar_request(self, user_input: str, session_state: Dict) -> Dict:
        """Handle calendar and meeting requests"""
        try:
            # Extract date from user input
            target_date = self.extract_date(user_input)
            if not target_date:
                target_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Check team availability
            availability_result = await self.calendar_agent.find_availability(
                date=target_date,
                attendee_emails=session_state.get('team_emails', []),
                session_state=session_state
            )
            
            if availability_result.get("success"):
                time_slots = availability_result.get("time_slots", [])
                best_times = [slot['time'] for slot in time_slots[:3] if slot.get('available_attendees', 0) > 0]
                
                return {
                    "type": "text",
                    "content": f"📅 **Team availability for {target_date}:**\n\n" +
                              f"👥 **Available:** {availability_result['available_attendees']}/{availability_result['total_attendees']} team members\n\n" +
                              f"🕐 **Best times:** {', '.join(best_times) if best_times else 'No availability'}\n\n" +
                              f"💡 **Tip:** Try searching for restaurants to see booking options with automatic calendar integration!"
                }
            else:
                return {
                    "type": "error",
                    "content": f"Could not check team availability: {availability_result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"Calendar request error: {str(e)}")
            return {
                "type": "error",
                "content": f"Error processing calendar request: {str(e)}"
            }
    
    async def execute_option(self, selected_option: Dict, session_state: Dict) -> Dict:
        """Execute the selected option (booking, event creation, etc.)"""
        try:
            restaurant = selected_option.get("restaurant", {})
            time_slot = selected_option.get("time_slot", {})
            
            # Generate confirmation ID with timestamp
            confirmation_id = f"BOOK_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Process restaurant reservation
            reservation_result = await self.process_restaurant_reservation(restaurant, time_slot, confirmation_id)
            
            # Create calendar event
            calendar_result = await self.create_calendar_event(restaurant, time_slot, confirmation_id, session_state)
            
            return {
                "success": True,
                "message": f"✅ Successfully organized dinner at {restaurant.get('name', 'restaurant')}! " +
                          f"({'Real restaurant from GoMaps API' if restaurant.get('source') == 'gomaps_api' else 'Demo restaurant'}) " +
                          f"📞 Please call {restaurant.get('phone', 'the restaurant')} to confirm reservation.",
                "reservation": reservation_result,
                "calendar_event": calendar_result,
                "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": "A4xMimic"
            }
            
        except Exception as e:
            logger.error(f"Option execution error: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to execute booking: {str(e)}"
            }
    
    async def process_restaurant_reservation(self, restaurant: Dict, time_slot: Dict, confirmation_id: str) -> Dict:
        """Process restaurant reservation"""
        try:
            # For now, all reservations are manual (call restaurant)
            return {
                "confirmation": confirmation_id,
                "method": "manual",
                "restaurant_phone": restaurant.get("phone"),
                "restaurant_name": restaurant.get("name"),
                "status": "pending_confirmation",
                "instructions": f"Call {restaurant.get('phone', 'restaurant')} to confirm reservation",
                "booking_details": {
                    "date": time_slot.get("date"),
                    "time": time_slot.get("time"),
                    "party_size": time_slot.get("total_attendees"),
                    "restaurant_address": restaurant.get("address")
                }
            }
        except Exception as e:
            logger.error(f"Reservation processing error: {str(e)}")
            return {
                "confirmation": confirmation_id,
                "method": "manual",
                "status": "error",
                "error": str(e)
            }
    
    async def create_calendar_event(self, restaurant: Dict, time_slot: Dict, confirmation_id: str, session_state: Dict) -> Dict:
        """Create calendar event for the booking"""
        try:
            # Prepare event details
            event_title = f"Team Dinner at {restaurant.get('name', 'Restaurant')}"
            event_description = f"""Team Dinner Booking - {confirmation_id}

🍽️ Restaurant: {restaurant.get('name', 'Unknown')}
📍 Address: {restaurant.get('address', 'N/A')}
📞 Phone: {restaurant.get('phone', 'N/A')}
⭐ Rating: {restaurant.get('rating', 'N/A')} ({restaurant.get('user_ratings_total', 0)} reviews)
💰 Price Range: {restaurant.get('price_range', 'N/A')}

🎯 Reservation: {confirmation_id}
👤 Organized by: A4xMimic
📅 Booking Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please confirm attendance and bring ID for reservation.

Location: {restaurant.get('address', 'N/A')}

Team Members Invited:
{chr(10).join(['• ' + email for email in time_slot.get('attendee_emails', [])])}
            """.strip()
            
            # Create datetime string
            event_date = time_slot.get('date', '2025-07-20')
            event_time = time_slot.get('time', '19:00')
            event_datetime = f"{event_date}T{event_time}:00"
            
            # Get attendee emails
            attendee_emails = time_slot.get('attendee_emails', session_state.get('team_emails', []))
            
            # Create the event
            result = await self.calendar_agent.create_event(
                title=event_title,
                description=event_description,
                start_time=event_datetime,
                attendees=attendee_emails,
                session_state=session_state
            )
            
            if result.get("success"):
                calendar_event = result.get("event", {})
                return {
                    "source": result.get("source", "unknown"),
                    "event_id": calendar_event.get("id"),
                    "link": calendar_event.get("link"),
                    "status": calendar_event.get("status"),
                    "attendees": attendee_emails,
                    "event_title": event_title,
                    "creation_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                # Create fallback universal link
                return {
                    "source": "fallback_universal_link",
                    "event_id": f"fallback_{confirmation_id}",
                    "link": f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Team%20Dinner&dates={event_date.replace('-', '')}T{event_time.replace(':', '')}00Z/{event_date.replace('-', '')}T{str(int(event_time.replace(':', '')) + 200).zfill(4)}00Z",
                    "status": "created",
                    "attendees": attendee_emails,
                    "error": result.get("error"),
                    "event_title": event_title
                }
                
        except Exception as e:
            logger.error(f"Calendar event creation error: {str(e)}")
            return {
                "source": "error_fallback",
                "event_id": f"error_{confirmation_id}",
                "link": "https://calendar.google.com/calendar/render?action=TEMPLATE&text=Team%20Dinner",
                "status": "error",
                "error": str(e),
                "attendees": time_slot.get('attendee_emails', [])
            }
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from user input"""
        # Indian cities and common locations
        locations = [
            'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai', 'kolkata', 'calcutta',
            'pune', 'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore', 'thane', 
            'bhopal', 'visakhapatnam', 'pimpri', 'patna', 'vadodara', 'ghaziabad', 'ludhiana', 
            'agra', 'nashik', 'faridabad', 'meerut', 'rajkot', 'kalyan', 'vasai', 'varanasi', 
            'srinagar', 'aurangabad', 'dhanbad', 'amritsar', 'navi mumbai', 'allahabad', 'prayagraj',
            'ranchi', 'howrah', 'coimbatore', 'jabalpur', 'gwalior', 'vijayawada', 'jodhpur',
            'madurai', 'raipur', 'kota', 'guwahati', 'chandigarh', 'solapur', 'hubballi', 'tiruchirappalli',
            'bareilly', 'mysuru', 'mysore', 'tiruppur', 'gurgaon', 'gurugram', 'aligarh', 'jalandhar',
            'bhubaneswar', 'salem', 'warangal', 'guntur', 'bhiwandi', 'saharanpur', 'gorakhpur',
            'bikaner', 'amravati', 'noida', 'jamshedpur', 'bhilai', 'cuttack', 'firozabad',
            'kochi', 'cochin', 'nellore', 'bhavnagar', 'dehradun', 'durgapur', 'asansol'
        ]
        
        text_lower = text.lower()
        
        # Direct location matches
        for location in locations:
            if location in text_lower:
                # Handle special cases
                if location in ['bengaluru', 'bangalore']:
                    return 'Bangalore'
                elif location in ['calcutta', 'kolkata']:
                    return 'Kolkata'
                elif location in ['cochin', 'kochi']:
                    return 'Kochi'
                elif location in ['mysuru', 'mysore']:
                    return 'Mysore'
                elif location in ['prayagraj', 'allahabad']:
                    return 'Allahabad'
                elif location in ['gurugram', 'gurgaon']:
                    return 'Gurgaon'
                else:
                    return location.title()
        
        # Check for phrases like "in Mumbai", "near Delhi", etc.
        import re
        location_pattern = r'\b(?:in|near|at|around)\s+([a-zA-Z\s]+?)(?:\s|$|,|\.)'
        matches = re.findall(location_pattern, text_lower)
        
        for match in matches:
            match = match.strip()
            for location in locations:
                if location in match:
                    return location.title()
        
        return None
    
    def extract_cuisine(self, text: str) -> List[str]:
        """Extract cuisine preferences from user input"""
        cuisines = [
            # Indian cuisines
            'indian', 'north indian', 'south indian', 'punjabi', 'gujarati', 'rajasthani', 
            'bengali', 'maharashtrian', 'tamil', 'kerala', 'hyderabadi', 'lucknowi', 'awadhi',
            'mughlai', 'tandoor', 'biryani', 'dosa', 'thali',
            
            # International cuisines  
            'chinese', 'italian', 'mexican', 'thai', 'japanese', 'korean', 'american',
            'continental', 'mediterranean', 'french', 'greek', 'turkish', 'arabic',
            'lebanese', 'persian', 'afghan', 'tibetan', 'burmese', 'vietnamese',
            
            # Food types
            'pizza', 'burger', 'pasta', 'seafood', 'sushi', 'bbq', 'barbecue',
            'street food', 'fast food', 'fine dining', 'casual dining', 'buffet',
            
            # Dietary preferences
            'vegetarian', 'vegan', 'non-vegetarian', 'jain', 'halal', 'kosher',
            
            # Specific dishes
            'biryani', 'kebab', 'tikka', 'curry', 'dal', 'naan', 'roti', 'paratha'
        ]
        
        text_lower = text.lower()
        found_cuisines = []
        
        # Sort cuisines by length (longest first) to match "north indian" before "indian"
        cuisines_sorted = sorted(cuisines, key=len, reverse=True)
        
        for cuisine in cuisines_sorted:
            if cuisine in text_lower and cuisine not in found_cuisines:
                found_cuisines.append(cuisine)
        
        return found_cuisines if found_cuisines else ['indian']
    
    def extract_party_size(self, text: str, session_state: Dict) -> int:
        """Extract party size from user input"""
        import re
        
        # Look for explicit numbers
        numbers = re.findall(r'\b(\d+)\b', text)
        
        # Look for specific patterns
        text_lower = text.lower()
        
        # Team-related keywords
        if any(word in text_lower for word in ['team', 'group', 'colleagues', 'office', 'work']):
            return session_state.get('team_size', 6)
        
        # Family-related keywords
        if any(word in text_lower for word in ['family', 'relatives']):
            return 4
        
        # Couple-related keywords
        if any(word in text_lower for word in ['couple', 'two', 'date', 'romantic']):
            return 2
        
        # Large group keywords
        if any(word in text_lower for word in ['large group', 'big group', 'celebration', 'party']):
            return max(session_state.get('team_size', 6), 8)
        
        # Use first reasonable number found
        for num_str in numbers:
            num = int(num_str)
            if 1 <= num <= 50:  # Reasonable party size range
                return num
        
        # Default to team size
        return session_state.get('team_size', 6)
    
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from user input"""
        import re
        from datetime import datetime, timedelta
        
        text_lower = text.lower()
        current_date = datetime.now().date()
        
        # Handle relative dates
        if 'today' in text_lower:
            return current_date.strftime("%Y-%m-%d")
        elif 'tomorrow' in text_lower:
            return (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        elif 'day after tomorrow' in text_lower:
            return (current_date + timedelta(days=2)).strftime("%Y-%m-%d")
        elif 'next week' in text_lower:
            return (current_date + timedelta(days=7)).strftime("%Y-%m-%d")
        elif 'this week' in text_lower:
            return (current_date + timedelta(days=3)).strftime("%Y-%m-%d")
        elif 'this weekend' in text_lower:
            days_until_saturday = (5 - current_date.weekday()) % 7
            if days_until_saturday == 0:  # It's Saturday
                days_until_saturday = 7
            return (current_date + timedelta(days=days_until_saturday)).strftime("%Y-%m-%d")
        elif 'next weekend' in text_lower:
            days_until_next_saturday = ((5 - current_date.weekday()) % 7) + 7
            return (current_date + timedelta(days=days_until_next_saturday)).strftime("%Y-%m-%d")
        
        # Handle day names
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in text_lower:
                days_ahead = (i - current_date.weekday()) % 7
                if days_ahead == 0:  # Today is that day, get next week
                    days_ahead = 7
                return (current_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Look for date patterns (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, etc.)
        date_patterns = [
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b',  # MM-DD-YYYY or DD-MM-YYYY
            r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b'  # MM.DD.YYYY or DD.MM.YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    match = matches[0]
                    if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD format
                        year, month, day = match
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:  # Other formats - assume MM/DD/YYYY (US format)
                        part1, part2, year = match
                        # Simple heuristic: if first part > 12, assume DD/MM format
                        if int(part1) > 12:
                            day, month = part1, part2
                        else:
                            month, day = part1, part2
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def get_search_summary(self, search_criteria: Dict, options_count: int) -> str:
        """Generate a summary of the search results"""
        location = search_criteria.get("location", "Unknown")
        cuisine = search_criteria.get("cuisine", [])
        party_size = search_criteria.get("party_size", "Unknown")
        
        cuisine_text = ", ".join(cuisine) if cuisine else "Any cuisine"
        
        return f"""🔍 **Search Summary:**
📍 **Location:** {location}
🍽️ **Cuisine:** {cuisine_text}
👥 **Party Size:** {party_size} people
📊 **Results:** {options_count} restaurant options found
🕐 **Search Time:** {datetime.now().strftime('%H:%M:%S')}
👤 **Requested by:** A4xMimic
"""