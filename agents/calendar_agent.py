import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from utils.logger import setup_logger

logger = setup_logger(__name__)

class CalendarAgent:
    def __init__(self, config):
        self.config = config
        self.service = None
        
    def initialize_calendar_service(self, credentials_data: Dict) -> Dict:
        """Initialize calendar service with proper OAuth flow"""
        try:
            # Check if this is OAuth credentials (not service account)
            if credentials_data.get("type") == "service_account":
                return {
                    "success": False,
                    "error": "Service account credentials detected. For calendar invitations, please use OAuth 2.0 credentials instead.",
                    "suggestion": "Download OAuth 2.0 credentials from Google Cloud Console > APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client ID"
                }
            
            # Try to initialize with OAuth credentials
            import pickle
            import os
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            
            creds = None
            # Load existing token if available
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Create temporary credentials file
                    import tempfile
                    import json
                    
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(credentials_data, f)
                        temp_creds_path = f.name
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(temp_creds_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                        
                        # Save the credentials for future use
                        with open('token.pickle', 'wb') as token:
                            pickle.dump(creds, token)
                    finally:
                        os.unlink(temp_creds_path)
            
            self.service = build('calendar', 'v3', credentials=creds)
            
            # Test the service
            calendar_list = self.service.calendarList().list().execute()
            
            return {
                "success": True,
                "message": "Google Calendar connected successfully",
                "calendars_count": len(calendar_list.get('items', []))
            }
            
        except Exception as e:
            logger.error(f"Calendar initialization error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Make sure you're using OAuth 2.0 credentials, not service account credentials"
            }
    
    async def find_availability(self, date: str, attendee_emails: List[str], session_state: Dict) -> Dict:
        """Find team availability for a given date"""
        try:
            # Parse the date
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            current_date = datetime.now().date()
            
            # Mock availability data (since we're not using real calendar integration)
            if not attendee_emails:
                attendee_emails = session_state.get('team_emails', [
                    'alice@company.com',
                    'bob@company.com', 
                    'charlie@company.com',
                    'diana@company.com',
                    'eve@company.com',
                    'frank@company.com'
                ])
            
            total_attendees = len(attendee_emails)
            
            # Simulate availability based on date and time
            if target_date < current_date:
                available_count = 0  # Past dates
                availability_status = "past"
            elif target_date == current_date:
                available_count = max(1, total_attendees - 2)  # Some people busy today
                availability_status = "limited"
            elif target_date <= current_date + timedelta(days=3):
                available_count = max(2, total_attendees - 1)  # Good availability soon
                availability_status = "good"
            elif target_date <= current_date + timedelta(days=7):
                available_count = total_attendees  # Perfect availability in a week
                availability_status = "excellent"
            else:
                available_count = max(3, total_attendees - 2)  # Decent availability far out
                availability_status = "good"
            
            # Generate time slot suggestions
            time_slots = []
            suggested_times = ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30"]
            
            for time in suggested_times:
                # Adjust availability slightly for different times
                time_available = available_count
                if time in ["19:00", "19:30"]:  # Peak dinner times
                    time_available = min(time_available, total_attendees)
                elif time in ["18:00", "20:30"]:  # Edge times
                    time_available = max(1, time_available - 1)
                
                time_slots.append({
                    "time": time,
                    "available_attendees": time_available,
                    "total_attendees": total_attendees,
                    "availability_percentage": round((time_available / total_attendees) * 100),
                    "status": "available" if time_available >= total_attendees // 2 else "limited"
                })
            
            return {
                "success": True,
                "date": date,
                "total_attendees": total_attendees,
                "available_attendees": available_count,
                "availability_status": availability_status,
                "time_slots": time_slots,
                "attendee_emails": attendee_emails,
                "message": f"Found availability for {available_count}/{total_attendees} team members on {date}"
            }
            
        except Exception as e:
            logger.error(f"Availability check error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Could not check team availability"
            }
    
    async def create_event(self, title: str, description: str, start_time: str, attendees: List[str], session_state: Dict) -> Dict:
        """Create calendar event with proper fallback to universal links"""
        try:
            # Parse the datetime
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = start_dt + timedelta(hours=2)  # 2-hour event
            except:
                # Fallback parsing
                start_dt = datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S")
                end_dt = start_dt + timedelta(hours=2)
            
            # If we have a working Google Calendar service, try to create real event
            if self.service and session_state.get('calendar_verified') and session_state.get('calendar_mode') != 'universal':
                try:
                    event = {
                        'summary': title,
                        'description': description,
                        'start': {
                            'dateTime': start_dt.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': end_dt.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'attendees': [{'email': email} for email in attendees],
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                                {'method': 'popup', 'minutes': 30},       # 30 minutes before
                            ],
                        },
                        'sendUpdates': 'all'  # Send invitations
                    }
                    
                    # Create the event
                    created_event = self.service.events().insert(
                        calendarId='primary', 
                        body=event,
                        sendUpdates='all'
                    ).execute()
                    
                    return {
                        "success": True,
                        "source": "google_calendar",
                        "event": {
                            "id": created_event.get('id'),
                            "link": created_event.get('htmlLink'),
                            "status": created_event.get('status')
                        },
                        "message": "Real Google Calendar event created with invitations"
                    }
                    
                except Exception as e:
                    logger.error(f"Google Calendar API error: {str(e)}")
                    # Fall back to universal link
                    return await self.create_universal_calendar_link(title, description, start_dt, end_dt, attendees)
            
            else:
                # Create universal calendar link
                return await self.create_universal_calendar_link(title, description, start_dt, end_dt, attendees)
                
        except Exception as e:
            logger.error(f"Calendar event creation error: {str(e)}")
            # Last resort: create basic universal link
            return await self.create_basic_calendar_link(title, start_time)
    
    async def create_universal_calendar_link(self, title: str, description: str, start_dt: datetime, end_dt: datetime, attendees: List[str]) -> Dict:
        """Create universal calendar link that works across all calendar apps"""
        try:
            # Format dates for Google Calendar URL (YYYYMMDDTHHMMSSZ)
            start_formatted = start_dt.strftime("%Y%m%dT%H%M%S") + "Z"
            end_formatted = end_dt.strftime("%Y%m%dT%H%M%S") + "Z"
            
            # URL encode the components
            import urllib.parse
            
            title_encoded = urllib.parse.quote(title)
            description_encoded = urllib.parse.quote(description.replace('\n', ' ')[:500])  # Limit length
            
            # Create Google Calendar add link
            base_url = "https://calendar.google.com/calendar/render"
            params = {
                "action": "TEMPLATE",
                "text": title,
                "dates": f"{start_formatted}/{end_formatted}",
                "details": description.replace('\n', ' ')[:500],
                "sf": "true",
                "output": "xml"
            }
            
            # Build URL
            param_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
            calendar_link = f"{base_url}?{param_string}"
            
            return {
                "success": True,
                "source": "universal_link",
                "event": {
                    "id": f"universal_{int(start_dt.timestamp())}",
                    "link": calendar_link,
                    "status": "confirmed"
                },
                "message": "Universal calendar link created (works with all calendar apps)"
            }
            
        except Exception as e:
            logger.error(f"Universal calendar link error: {str(e)}")
            return await self.create_basic_calendar_link(title, start_dt.isoformat())
    
    async def create_basic_calendar_link(self, title: str, start_time: str) -> Dict:
        """Create basic calendar link as last resort"""
        try:
            import urllib.parse
            
            # Simple Google Calendar link
            title_encoded = urllib.parse.quote(title)
            calendar_link = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title_encoded}"
            
            return {
                "success": True,
                "source": "basic_link",
                "event": {
                    "id": f"basic_{int(datetime.now().timestamp())}",
                    "link": calendar_link,
                    "status": "confirmed"
                },
                "message": "Basic calendar link created"
            }
            
        except Exception as e:
            logger.error(f"Basic calendar link error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_availability(self, start_time: str, end_time: str, attendees: List[str], session_state: Dict) -> Dict:
        """Check availability for specific time slot"""
        try:
            # Parse start time to get date
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            date_str = start_dt.strftime("%Y-%m-%d")
            
            # Use find_availability method
            availability_result = await self.find_availability(date_str, attendees, session_state)
            
            if availability_result.get("success"):
                # Find the specific time slot
                requested_time = start_dt.strftime("%H:%M")
                time_slots = availability_result.get("time_slots", [])
                
                # Find closest time slot
                best_match = None
                for slot in time_slots:
                    if slot["time"] == requested_time:
                        best_match = slot
                        break
                
                if not best_match and time_slots:
                    # Use first available slot as fallback
                    best_match = time_slots[0]
                
                return {
                    "success": True,
                    "available": True if best_match else False,
                    "time_slot": best_match,
                    "alternative_slots": time_slots[:3],  # Top 3 alternatives
                    "message": f"Availability checked for {requested_time}"
                }
            else:
                return availability_result
                
        except Exception as e:
            logger.error(f"Availability check error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_team_schedules(self, date: str, session_state: Dict) -> Dict:
        """Get team schedules for a specific date"""
        try:
            # Get team emails
            team_emails = session_state.get('team_emails', [])
            
            if not team_emails:
                return {
                    "success": False,
                    "error": "No team members configured"
                }
            
            # Mock schedule data for each team member
            schedules = {}
            busy_times = {
                "morning": ["09:00-12:00"],
                "afternoon": ["14:00-17:00"],
                "evening": ["18:00-21:00"]
            }
            
            for email in team_emails:
                # Simulate some people being busy at different times
                member_busy_times = []
                if email.endswith('@company.com'):
                    # Company emails are more likely to be busy during work hours
                    if hash(email + date) % 3 == 0:
                        member_busy_times.extend(busy_times["morning"])
                    if hash(email + date) % 4 == 0:
                        member_busy_times.extend(busy_times["afternoon"])
                
                schedules[email] = {
                    "email": email,
                    "busy_times": member_busy_times,
                    "available": len(member_busy_times) < 2,
                    "status": "available" if len(member_busy_times) < 2 else "busy"
                }
            
            return {
                "success": True,
                "date": date,
                "schedules": schedules,
                "total_members": len(team_emails),
                "available_members": len([s for s in schedules.values() if s["available"]]),
                "message": f"Retrieved schedules for {len(team_emails)} team members"
            }
            
        except Exception as e:
            logger.error(f"Schedule retrieval error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }