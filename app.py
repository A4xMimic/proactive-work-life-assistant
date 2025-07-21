import streamlit as st
import asyncio
from datetime import datetime, timedelta, timezone
import json
from typing import Dict, List, Optional, Tuple
import logging
import google.generativeai as genai
import time
import re

from agents.orchestrator import AgentOrchestrator
from utils.config import Config
from utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="ProActive Work-Life Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

class RequestTypePreferences:
    """Define optimal times for different request types"""
    
    DINNER = {
        "name": "🍽️ Team Dinner",
        "preferred_hours": [18, 19, 20, 21],
        "optimal_days": [1, 2, 3, 4],  # Tuesday-Friday
        "duration_hours": 2,
        "avoid_times": [22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8],
        "description": "Best for evening dining with team"
    }
    
    MEETING = {
        "name": "📅 Team Meeting", 
        "preferred_hours": [9, 10, 11, 14, 15, 16],
        "optimal_days": [1, 2, 3],  # Tuesday-Thursday
        "duration_hours": 1,
        "avoid_times": [17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8],
        "description": "Business hours for productive meetings"
    }
    
    CELEBRATION = {
        "name": "🎉 Team Celebration",
        "preferred_hours": [17, 18, 19, 20, 21, 22],
        "optimal_days": [4, 5, 6],  # Friday-Sunday
        "duration_hours": 3,
        "avoid_times": [23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "description": "Perfect for celebrations and parties"
    }
    
    BIRTHDAY = {
        "name": "🎂 Birthday Celebration",
        "preferred_hours": [12, 13, 18, 19, 20],
        "optimal_days": [0, 1, 2, 3, 4, 5, 6],  # Any day
        "duration_hours": 2,
        "avoid_times": [22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "description": "Lunch or dinner celebration"
    }

class WebAutomationAgent:
    """Advanced web automation for restaurant reservations using LLM-driven Selenium"""
    
    def __init__(self, llm_model=None):
        self.llm_model = llm_model
        self.current_time = datetime.now() + timedelta(hours=5, minutes=30)  # Updated current time
        self.automation_enabled = False
        
    async def check_automation_dependencies(self) -> Dict:
        """Check if Selenium web automation dependencies are available"""
        try:
            # Step 1: Check if selenium is installed
            try:
                import selenium
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options
                selenium_version = getattr(selenium, '__version__', 'Unknown')
            except ImportError:
                return {
                    "success": False,
                    "error": "Selenium not installed",
                    "suggestion": "Install with: pip install selenium",
                    "install_command": "pip install selenium",
                    "step": "install_selenium"
                }
            
            # Step 2: Check available webdrivers
            browsers_status = {}
            available_browsers = []
            errors = []
            
            # Test Chrome/Chromium
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.quit()
                browsers_status["chrome"] = {"available": True, "error": None}
                available_browsers.append("chrome")
            except Exception as e:
                browsers_status["chrome"] = {"available": False, "error": str(e)}
                errors.append(f"Chrome: {str(e)}")
            
            # Test Firefox
            try:
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                firefox_options = FirefoxOptions()
                firefox_options.add_argument('--headless')
                
                driver = webdriver.Firefox(options=firefox_options)
                driver.quit()
                browsers_status["firefox"] = {"available": True, "error": None}
                available_browsers.append("firefox")
            except Exception as e:
                browsers_status["firefox"] = {"available": False, "error": str(e)}
                errors.append(f"Firefox: {str(e)}")
            
            # Test Edge
            try:
                from selenium.webdriver.edge.options import Options as EdgeOptions
                edge_options = EdgeOptions()
                edge_options.add_argument('--headless')
                
                driver = webdriver.Edge(options=edge_options)
                driver.quit()
                browsers_status["edge"] = {"available": True, "error": None}
                available_browsers.append("edge")
            except Exception as e:
                browsers_status["edge"] = {"available": False, "error": str(e)}
                errors.append(f"Edge: {str(e)}")
            
            # Check results
            if available_browsers:
                return {
                    "success": True,
                    "message": f"Selenium automation ready with {len(available_browsers)} browser(s)",
                    "selenium_version": selenium_version,
                    "available_browsers": available_browsers,
                    "browsers_status": browsers_status,
                    "primary_browser": available_browsers[0],
                    "timestamp": self.current_time.isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "No browsers available for automation",
                    "suggestion": "Install ChromeDriver or other webdrivers",
                    "install_command": "pip install webdriver-manager",
                    "browsers_status": browsers_status,
                    "detailed_errors": errors,
                    "step": "install_webdrivers",
                    "selenium_version": selenium_version
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Selenium setup error: {str(e)}",
                "suggestion": "Check Selenium installation and try: pip install selenium webdriver-manager",
                "step": "general_error"
            }
    
    async def analyze_restaurant_website(self, website_url: str) -> Dict:
        """Use LLM to analyze restaurant website structure for automation using Selenium"""
        try:
            if not website_url or not website_url.startswith('http'):
                return {"success": False, "error": "Invalid website URL"}
            
            # Check if selenium is available first
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager.chrome import ChromeDriverManager
            except ImportError:
                return {
                    "success": False,
                    "error": "Selenium not installed",
                    "suggestion": "Run: pip install selenium webdriver-manager"
                }
            
            driver = None
            try:
                # Try to setup Chrome with automatic driver management
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                
                try:
                    # Use webdriver-manager for automatic driver installation
                    driver = webdriver.Chrome(
                        service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                        options=chrome_options
                    )
                except Exception:
                    # Fallback to system Chrome
                    driver = webdriver.Chrome(options=chrome_options)
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to initialize Chrome driver: {str(e)}",
                    "suggestion": "Install ChromeDriver or run: pip install webdriver-manager"
                }
            
            try:
                # Navigate to website with timeout
                driver.set_page_load_timeout(30)
                driver.get(website_url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Get page information
                page_title = driver.title
                page_source = driver.page_source
                
                # Find interactive elements
                form_elements = driver.find_elements(By.TAG_NAME, 'form')
                input_elements = driver.find_elements(By.TAG_NAME, 'input')
                button_elements = driver.find_elements(By.TAG_NAME, 'button')
                select_elements = driver.find_elements(By.TAG_NAME, 'select')
                
                # Look for reservation-related elements
                reservation_keywords = ['reservation', 'book', 'table', 'booking', 'reserve', 'book a table', 'make reservation', 'reserve table', 'table booking', 'book now', 'reserve now']
                booking_selectors = [ # Navigation buttons (like BBK's "Book a Table")
            "//nav//a[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Table')]",
            "//header//a[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Table')]",
            
            # Menu items
            "//ul//a[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Table')]",
            
            # Buttons anywhere
            "//button[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Table')]",
            "//a[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Table')]",
            
            # By attributes
            "//a[contains(@title, 'Book') or contains(@title, 'Reserve') or contains(@title, 'Table')]",
            "//*[contains(@class, 'book') or contains(@class, 'reserve') or contains(@class, 'table')]",
            "//*[contains(@id, 'book') or contains(@id, 'reserve') or contains(@id, 'table')]",
            
            # Forms
            "//form[contains(@action, 'book') or contains(@action, 'reserve')]",
            "//input[@type='date' or contains(@name, 'date') or contains(@id, 'date')]"
        ]
                
                potential_elements = []
                for selector in booking_selectors:
                    try:

                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                text_content = element.text or ""
                                href = element.get_attribute('href') or ""
                                title = element.get_attribute('title') or ""
                                element_class = element.get_attribute('class') or ""
                            
                                potential_elements.append({
                                    "type": element.tag_name,
                                    "text": text_content,
                                    "href": href,
                                    "title": title,
                                    "class": element_class,
                                    "selector": selector
                                })
                    except:
                        continue
                
        
                # ENHANCED LLM ANALYSIS
                analysis_prompt = f"""
                Analyze this restaurant website for automated reservation booking:
        
                Website: {website_url}
                Title: {page_title}
        
                Found {len(form_elements)} forms, {len(input_elements)} inputs, {len(button_elements)} buttons
        
                Potential booking elements:
                {json.dumps(potential_elements[:20], indent=2)}
        
                IMPORTANT: Look for ANY booking-related elements including:
                - Navigation buttons like "Book a Table"
                - Menu items for reservations
                - Links that might lead to booking pages
                - External booking systems (OpenTable, Resy, etc.)
        
                Provide a JSON analysis with:
                1. "has_online_booking": boolean (true if ANY booking option exists)
                2. "booking_method": "form" | "navigation_link" | "external_service" | "phone_only"
                3. "automation_feasibility": "high" | "medium" | "low" | "impossible"
                4. "booking_entry_points": list of detected booking options
                5. "automation_steps": detailed steps for automation
                6. "challenges": potential automation challenges
              """
                if self.llm_model:
                    
                    try:
                        response = self.llm_model.generate_content(analysis_prompt)
                        # Clean the response to extract JSON
                        response_text = response.text.strip()
                        if '```json' in response_text:
                            json_start = response_text.find('```json') + 7
                            json_end = response_text.find('```', json_start)
                            response_text = response_text[json_start:json_end]
                        elif '```' in response_text:
                            response_text = response_text.strip('```').strip()
                        
                        llm_analysis = json.loads(response_text)
                    except Exception as e:
                        logger.warning(f"LLM analysis failed: {str(e)}")
                        llm_analysis = {
                            "has_online_booking": len(potential_elements) > 0,
                            "booking_method": "form" if len(form_elements) > 0 else "unknown",
                            "automation_feasibility": "medium",
                            "required_fields": ["date", "time", "party_size", "name", "phone"],
                            "automation_steps": ["Navigate to booking form", "Fill required fields", "Submit"],
                            "challenges": ["Dynamic content", "CAPTCHA", "Authentication"]
                        }
                else:
                    # Fallback analysis without LLM
                    llm_analysis = {
                        "has_online_booking": len(potential_elements) > 0,
                        "booking_method": "form" if len(form_elements) > 0 else "phone_only",
                        "automation_feasibility": "medium" if len(potential_elements) > 0 else "low",
                        "required_fields": ["date", "time", "party_size", "name", "phone"],
                        "automation_steps": ["Navigate to website", "Find booking form", "Fill details"],
                        "challenges": ["Website structure", "Form validation"]
                    }
                
                return {
                    "success": True,
                    "website_url": website_url,
                    "analysis": llm_analysis,
                    "technical_details": {
                        "forms_found": len(form_elements),
                        "inputs_found": len(input_elements),
                        "buttons_found": len(button_elements),
                        "potential_booking_elements": len(potential_elements)
                    },
                    "timestamp": self.current_time.isoformat()
                }
                
            except Exception as e:
                if driver:
                    driver.quit()
                return {
                    "success": False,
                    "error": f"Failed to analyze website: {str(e)}",
                    "suggestion": "Website may be slow or blocking automation"
                }
                
        except Exception as e:
            logger.error(f"Website analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Website may not support automated booking or Selenium needs setup"
            }
    
    async def attempt_automated_booking(self, restaurant: Dict, booking_details: Dict) -> Dict:
        """Attempt automated restaurant booking using LLM-driven Selenium automation"""
        try:
            website_url = restaurant.get('website')
            if not website_url or not website_url.startswith('http'):
                return {
                    "success": False,
                    "method": "automation_failed",
                    "error": "No valid website URL for automation",
                    "fallback": "manual_booking_required"
                }
            
            # Check dependencies first
            deps_check = await self.check_automation_dependencies()
            if not deps_check.get("success"):
                return {
                    "success": False,
                    "method": "automation_failed",
                    "error": deps_check.get("error", "Automation dependencies not available"),
                    "suggestion": deps_check.get("suggestion", "Install Selenium"),
                    "fallback": "manual_booking_required"
                }
            
            # First analyze the website
            analysis_result = await self.analyze_restaurant_website(website_url)
            if not analysis_result.get("success"):
                return {
                    "success": False,
                    "method": "automation_failed",
                    "error": "Website analysis failed",
                    "details": analysis_result.get("error", "Unknown analysis error"),
                    "fallback": "manual_booking_required"
                }
            
            analysis = analysis_result.get("analysis", {})
            
            # Check if automation is feasible
            if analysis.get("automation_feasibility") == "impossible":
                return {
                    "success": False,
                    "method": "automation_not_feasible",
                    "reason": "Website doesn't support automated booking",
                    "fallback": "phone_booking_required"
                }
            
            # Attempt automated booking with Selenium
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            driver = None
            try:
                # Setup Chrome driver
                chrome_options = Options()
                if not st.session_state.get('automation_show_browser', True):
                    chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                
                try:
                    driver = webdriver.Chrome(
                        service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                        options=chrome_options
                    )
                except Exception:
                    driver = webdriver.Chrome(options=chrome_options)
                
                # Navigate to restaurant website
                driver.set_page_load_timeout(30)
                driver.get(website_url)
                
                automation_log = []
                automation_log.append(f"✅ Navigated to {website_url}")
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                automation_log.append("✅ Page loaded successfully")
                
                # Look for common booking elements
                booking_selectors = [
                    "//a[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Reservation')]",
                    "//button[contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Reservation')]",
                    "//a[contains(@href, 'book') or contains(@href, 'reservation') or contains(@href, 'reserve')]",
                    "//*[contains(@class, 'book') or contains(@class, 'reserve') or contains(@id, 'book') or contains(@id, 'reserve')]"
                ]
                
                booking_element = None
                for selector in booking_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                booking_element = element
                                automation_log.append(f"✅ Found booking element: {selector}")
                                break
                        if booking_element:
                            break
                    except:
                        continue
                
                if booking_element:
                    # Click on booking element
                    driver.execute_script("arguments[0].click();", booking_element)
                    automation_log.append("✅ Clicked booking element")
                    time.sleep(3)  # Wait for page transition
                    
                    # Try to fill basic information
                    form_fields = [
                        {'selector': "//input[@type='date' or contains(@name, 'date') or contains(@id, 'date')]", 'value': booking_details.get('date')},
                        {'selector': "//input[contains(@name, 'time') or contains(@id, 'time')]", 'value': booking_details.get('time')},
                        {'selector': "//select[contains(@name, 'time') or contains(@id, 'time')]", 'value': booking_details.get('time')},
                        {'selector': "//input[contains(@name, 'party') or contains(@name, 'guest') or contains(@name, 'people') or contains(@id, 'party') or contains(@id, 'guest')]", 'value': str(booking_details.get('party_size', 2))},
                        {'selector': "//input[contains(@name, 'name') or contains(@id, 'name') or contains(@placeholder, 'name')]", 'value': booking_details.get('contact_name', 'John Doe')},
                        {'selector': "//input[contains(@name, 'phone') or contains(@id, 'phone') or contains(@placeholder, 'phone')]", 'value': booking_details.get('contact_phone', '+1234567890')},
                        {'selector': "//input[contains(@name, 'email') or contains(@id, 'email') or contains(@placeholder, 'email')]", 'value': booking_details.get('contact_email', 'user@example.com')}
                    ]
                    
                    filled_fields = 0
                    for field in form_fields:
                        if field['value']:
                            try:
                                elements = driver.find_elements(By.XPATH, field['selector'])
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        element.clear()
                                        element.send_keys(str(field['value']))
                                        automation_log.append(f"✅ Filled field: {field['value']}")
                                        filled_fields += 1
                                        time.sleep(0.5)
                                        break
                            except Exception as e:
                                automation_log.append(f"❌ Failed to fill field: {str(e)}")
                    
                    automation_log.append(f"📊 Filled {filled_fields} form fields")
                    
                    # Try to find submit button (but don't actually submit)
                    submit_selectors = [
                        "//button[@type='submit' or contains(text(), 'Submit') or contains(text(), 'Book') or contains(text(), 'Reserve') or contains(text(), 'Confirm')]",
                        "//input[@type='submit']"
                    ]
                    
                    submit_element = None
                    for selector in submit_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_element = element
                                    automation_log.append(f"✅ Found submit button: {selector}")
                                    break
                            if submit_element:
                                break
                        except:
                            continue
                    
                    if submit_element:
                        # Don't actually submit for demo purposes
                        automation_log.append("⚠️ Submit button found but not clicked (demo mode)")
                        booking_success = True
                    else:
                        automation_log.append("❌ No submit button found")
                        booking_success = False
                
                else:
                    automation_log.append("❌ No booking elements found on page")
                    booking_success = False
                
                # Take screenshot of final state
                try:
                    screenshot_path = f"selenium_booking_{int(time.time())}.png"
                    driver.save_screenshot(screenshot_path)
                    automation_log.append(f"📸 Screenshot saved: {screenshot_path}")
                except:
                    screenshot_path = None
                
                # Check final state
                final_url = driver.current_url
                automation_log.append(f"🏁 Final URL: {final_url}")
                
                driver.quit()
                
                if booking_success:
                    return {
                        "success": True,
                        "method": "selenium_automated_booking",
                        "confirmation": f"SELENIUM_{self.current_time.strftime('%Y%m%d%H%M%S')}",
                        "automation_log": automation_log,
                        "final_url": final_url,
                        "screenshot": screenshot_path,
                        "timestamp": self.current_time.isoformat(),
                        "note": "Demo mode - form filled but not submitted"
                    }
                else:
                    return {
                        "success": False,
                        "method": "selenium_automation_partial",
                        "automation_log": automation_log,
                        "final_url": final_url,
                        "screenshot": screenshot_path,
                        "message": "Selenium automation attempted but could not complete booking process",
                        "fallback": "manual_verification_required"
                    }
                
            except Exception as e:
                if driver:
                    driver.quit()
                logger.error(f"Selenium automation failed: {str(e)}")
                return {
                    "success": False,
                    "method": "selenium_automation_failed",
                    "error": str(e),
                    "fallback": "manual_booking_required"
                }
                
        except Exception as e:
            logger.error(f"Automated booking failed: {str(e)}")
            return {
                "success": False,
                "method": "automation_failed",
                "error": str(e),
                "fallback": "manual_booking_required"
            }

class WorkLifeAssistantApp:
    def __init__(self):
        self.config = Config()
        self.orchestrator = AgentOrchestrator(self.config)
        self.current_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)  # Updated to exact current time
        self.current_user = "A4xMimic"  # Updated current user
        self.request_preferences = RequestTypePreferences()
        self.web_automation = None
        
    def initialize_web_automation(self):
        """Initialize web automation agent with Selenium"""
        try:
            # Get LLM model for automation
            if st.session_state.get('gemini_verified') and st.session_state.get('gemini_key'):
                genai.configure(api_key=st.session_state['gemini_key'])
                model = genai.GenerativeModel('gemini-2.0-flash')
                self.web_automation = WebAutomationAgent(model)
                self.orchestrator.initialize_intent_classifier(model)
                self.orchestrator.initialize_email_agent()
            else:
                self.web_automation = WebAutomationAgent()
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize web automation: {str(e)}")
            return False
    
    def detect_request_type(self, user_input: str) -> str:
        """Detect the type of request from user input"""
        user_input_lower = user_input.lower()
        
        # Birthday keywords
        if any(word in user_input_lower for word in ["birthday", "bday", "b-day", "celebrate birthday", "birthday party"]):
            return "BIRTHDAY"
        
        # Celebration keywords  
        elif any(word in user_input_lower for word in ["celebration", "celebrate", "party", "anniversary", "milestone", "achievement", "celebratory"]):
            return "CELEBRATION"
        
        # Meeting keywords
        elif any(word in user_input_lower for word in ["meeting", "discuss", "planning", "review", "standup", "sync", "conference"]):
            return "MEETING"
        
        # Dinner keywords (default for restaurant-related requests)
        elif any(word in user_input_lower for word in ["dinner", "restaurant", "food", "eat", "dining", "meal", "lunch"]):
            return "DINNER"
        
        # Default to dinner for ambiguous requests
        return "DINNER"
    
    def get_request_preferences(self, request_type: str) -> Dict:
        """Get preferences for a specific request type"""
        return getattr(self.request_preferences, request_type, self.request_preferences.DINNER)
    
    def load_css(self):
        """Load enhanced CSS with Selenium web automation styling"""
        st.markdown("""
        <style>
        html {
            scroll-behavior: smooth;
        }
        
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .main-header h1 {
            font-size: 1.8rem;
            margin: 0 0 0.5rem 0;
        }
        
        .main-header p {
            font-size: 1rem;
            margin: 0;
            opacity: 0.9;
        }
        
        .option-card {
            background: #ffffff;
            border: 2px solid #e1e5e9;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .option-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .option-card h4 {
            color: #2d3748;
            margin: 0 0 1rem 0;
            font-size: 1.2rem;
            font-weight: 600;
        }
        
        .reviews-section {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border: 2px solid #f4a261;
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            box-shadow: 0 8px 16px rgba(244, 162, 97, 0.2);
        }
        
        .reviews-header {
            background: #e76f51;
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 1rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .review-item {
            background: white;
            border-left: 4px solid #e76f51;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .review-item:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .review-author {
            color: #e76f51;
            font-weight: bold;
            font-size: 1.1rem;
        }
        
        .review-rating {
            color: #f4a261;
            font-size: 1.2rem;
            margin-left: 0.5rem;
        }
        
        .review-text {
            color: #2d3748;
            font-style: italic;
            margin: 0.8rem 0;
            line-height: 1.6;
        }
        
        .review-time {
            color: #6c757d;
            font-size: 0.9rem;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            margin: 0.25rem;
        }
        
        .status-success { 
            background: #c6f6d5; 
            color: #22543d; 
            border: 1px solid #9ae6b4;
        }
        
        .status-warning { 
            background: #fef5e7; 
            color: #744210; 
            border: 1px solid #f6e05e;
        }
        
        .status-info { 
            background: #bee3f8; 
            color: #2a4365; 
            border: 1px solid #90cdf4;
        }
        
        .status-error { 
            background: #fed7d7; 
            color: #822727; 
            border: 1px solid #fc8181;
        }
        
        .selenium-automation-section {
            background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
            border: 2px solid #4caf50;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            color: #2e7d32;
        }
        
        .automation-status {
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
            border: 2px solid #10b981;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            color: #047857;
        }
        
        .automation-error {
            background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
            border: 2px solid #ef4444;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            color: #dc2626;
        }
        
        .automation-log {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            font-family: monospace;
            font-size: 0.9rem;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .install-command {
            background: #1e293b;
            color: #f1f5f9;
            padding: 1rem;
            border-radius: 8px;
            font-family: monospace;
            margin: 1rem 0;
            border-left: 4px solid #22c55e;
        }
        
        .browser-status {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem;
            margin: 0.5rem 0;
            font-family: monospace;
            font-size: 0.85rem;
        }
        
        .chat-message {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
        }
        
        .user-message {
            background: #667eea;
            color: white;
            margin-left: 2rem;
        }
        
        .assistant-message {
            background: #f7fafc;
            border-left: 4px solid #667eea;
            color: #2d3748;
        }
        
        .time-selection {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            margin: 2rem 0;
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
            animation: slideInScale 0.6s ease-out;
        }
        
        .availability-info {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            border: 2px solid #4ecdc4;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            color: #2d3748;
        }
        
        .real-calendar-info {
            background: linear-gradient(135deg, #c6f6d5 0%, #9ae6b4 100%);
            border: 2px solid #48bb78;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            color: #22543d;
        }
        
        .enhanced-availability {
            background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);
            border: 2px solid #0288d1;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            color: #01579b;
        }
        
        .team-status-summary {
            background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
            border: 2px solid #8e24aa;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            color: #4a148c;
        }
        
        @keyframes slideInScale {
            from {
                opacity: 0;
                transform: translateY(50px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        .time-selection h3 {
            color: white;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .time-selection p {
            color: rgba(255, 255, 255, 0.9);
            margin: 0.5rem 0;
        }
        
        .scroll-target {
            scroll-margin-top: 100px;
            scroll-margin-bottom: 50px;
        }
        
        .booking-success {
            animation: bounceIn 0.6s ease-out;
        }
        
        @keyframes bounceIn {
            0% {
                opacity: 0;
                transform: scale(0.3);
            }
            50% {
                opacity: 1;
                transform: scale(1.05);
            }
            70% {
                transform: scale(0.9);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .stButton button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
        </style>
        """, unsafe_allow_html=True)
    
    def test_web_automation(self) -> Dict:
        """Test Selenium web automation capabilities"""
        try:
            if not self.web_automation:
                self.initialize_web_automation()
            
            if self.web_automation:
                return asyncio.run(self.web_automation.check_automation_dependencies())
            else:
                return {"success": False, "error": "Web automation not initialized"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_gemini_connection(self, api_key: str) -> Dict:
        """Test Gemini API connection"""
        try:
            genai.configure(api_key=api_key)
            
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            if not available_models:
                return {"success": False, "error": "No models available"}
            
            preferred_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
            selected_model = None
            
            for preferred in preferred_models:
                for available in available_models:
                    if preferred in available:
                        selected_model = available
                        break
                if selected_model:
                    break
            
            if not selected_model:
                selected_model = available_models[0]
            
            test_model = genai.GenerativeModel(selected_model)
            response = test_model.generate_content("Hello")
            
            return {
                "success": True,
                "model": selected_model,
                "response": response.text
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_gomaps_connection(self, api_key: str) -> Dict:
        """Test GoMaps API connection"""
        try:
            import aiohttp
            
            async def test_api():
                url = "https://maps.gomaps.pro/maps/api/geocode/json"
                params = {"address": "New York, USA", "key": api_key}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {"success": data.get("status") == "OK"}
                        return {"success": False, "error": f"HTTP {response.status}"}
            
            return asyncio.run(test_api())
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_email_configuration(self, smtp_server: str, smtp_port: int, email: str, password: str) -> Dict:
        """Test email configuration with better error handling"""
        try:
            import smtplib
            
            # Connect and test
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email, password)
            server.quit()
            
            return {
                "success": True,
                "message": "Email configuration successful!"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            if "Username and Password not accepted" in str(e):
                return {
                    "success": False,
                    "error": "Gmail Authentication Failed",
                    "suggestion": "For Gmail, you need an 'App Password', not your regular password. Go to Gmail Settings > Security > 2-Step Verification > App Passwords to generate one."
                }
            else:
                return {
                    "success": False,
                    "error": f"Authentication failed: {str(e)}",
                    "suggestion": "Check your email and password. For Gmail, use an App Password."
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Check your SMTP server settings and credentials."
            }
    
    def test_real_calendar_access(self) -> Dict:
        """Test real Google Calendar API access"""
        try:
            credentials_json = st.session_state.get('calendar_credentials')
            if not credentials_json:
                return {"success": False, "error": "No calendar credentials configured"}
            
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Parse credentials
            credentials_data = json.loads(credentials_json)
            service_account_email = credentials_data.get("client_email")
            
            # Build service
            credentials = service_account.Credentials.from_service_account_info(
                credentials_data,
                scopes=[
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar.freebusy'
                ]
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Test with your email (A4xMimic's calendar)
            test_email = st.session_state.get('email_address', 'clips7621@gmail.com')
            test_date = (self.current_time + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Make a real API call
            freebusy_result = service.freebusy().query(
                body={
                    "timeMin": f"{test_date}T00:00:00Z",
                    "timeMax": f"{test_date}T23:59:59Z",
                    "items": [{"id": test_email}]
                }
            ).execute()
            
            calendar_data = freebusy_result.get('calendars', {}).get(test_email, {})
            errors = calendar_data.get('errors', [])
            
            if errors:
                return {
                    "success": False,
                    "error": f"Calendar access denied: {errors[0].get('reason', 'Unknown error')}",
                    "service_account": service_account_email,
                    "test_email": test_email
                }
            
            return {
                "success": True,
                "message": "Real calendar access working!",
                "service_account": service_account_email,
                "test_email": test_email,
                "test_date": test_date
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def render_sidebar(self):
        """Enhanced sidebar with Selenium web automation configuration"""
        with st.sidebar:
            st.markdown("### 🤖 ProActive Assistant")
            st.markdown(f"**User:** {self.current_user}")
            st.markdown(f"**Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            st.divider()
            
            # API Configuration
            st.markdown("### ⚙️ API Configuration")
            
            # Gemini AI
            with st.expander("🧠 Gemini AI", expanded=True):
                gemini_key = st.text_input("API Key", 
                                         value=st.session_state.get('gemini_key', ''),
                                         type="password", 
                                         key="gemini_api_key")
                
                if gemini_key:
                    if st.button("Test Connection", key="test_gemini_btn"):
                        with st.spinner("Testing..."):
                            result = self.test_gemini_connection(gemini_key)
                            if result["success"]:
                                st.success("✅ Connected")
                                st.session_state['gemini_key'] = gemini_key
                                st.session_state['gemini_verified'] = True
                                # Initialize web automation when Gemini is connected
                                self.initialize_web_automation()
                            else:
                                st.error("❌ Failed")
                                st.session_state['gemini_verified'] = False
            
            # Enhanced Selenium Web Automation
            with st.expander("🤖 Selenium Web Automation", expanded=True):
                st.markdown("**🌐 Advanced Restaurant Booking with Selenium**")
                
                # Enable/disable automation
                automation_enabled = st.checkbox(
                    "Enable Selenium Automation",
                    value=st.session_state.get('web_automation_enabled', False),
                    help="Automatically fill restaurant reservation forms using Selenium web automation"
                )
                st.session_state['web_automation_enabled'] = automation_enabled
                
                if automation_enabled:
                    if st.button("🧪 Test Selenium Automation", key="test_automation_btn"):
                        with st.spinner("Testing Selenium automation capabilities..."):
                            result = self.test_web_automation()
                            
                            if result["success"]:
                                st.success(f"✅ {result['message']}")
                                
                                # Show detailed success information
                                if result.get('selenium_version'):
                                    st.info(f"🔧 Selenium v{result['selenium_version']}")
                                
                                if result.get('available_browsers'):
                                    st.info(f"🌐 Available: {', '.join(result['available_browsers'])}")
                                    st.info(f"🚀 Primary: {result.get('primary_browser', 'chrome')}")
                                
                                # Show browser status details
                                if result.get('browsers_status'):
                                    st.markdown("**Browser Status:**")
                                    for browser, status in result['browsers_status'].items():
                                        if status.get('available'):
                                            st.markdown(f"✅ **{browser.capitalize()}:** Ready")
                                        else:
                                            st.markdown(f"❌ **{browser.capitalize()}:** {status.get('error', 'Not available')}")
                                
                                st.session_state['web_automation_verified'] = True
                            else:
                                st.error(f"❌ {result['error']}")
                                
                                # Enhanced error handling with specific guidance
                                error_step = result.get('step', 'unknown')
                                
                                if error_step == "install_selenium":
                                    st.markdown("""
                                    <div class="automation-error">
                                        <h4>🚨 Selenium Installation Required</h4>
                                        <p>Install Selenium to enable web automation:</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown("""
                                    <div class="install-command">
                                        pip install selenium webdriver-manager
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                elif error_step == "install_webdrivers":
                                    st.markdown("""
                                    <div class="automation-error">
                                        <h4>🚨 WebDriver Installation Required</h4>
                                        <p>Selenium is installed but webdrivers are missing. Install webdrivers:</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Show current Selenium version
                                    if result.get('selenium_version'):
                                        st.info(f"🔧 Selenium v{result['selenium_version']} detected")
                                    
                                    st.markdown("""
                                    <div class="install-command">
                                        pip install webdriver-manager
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Show detailed browser status
                                    if result.get('browsers_status'):
                                        st.markdown("**Detailed Browser Status:**")
                                        for browser, status in result['browsers_status'].items():
                                            status_icon = "✅" if status.get('available') else "❌"
                                            error_msg = status.get('error', 'Not available')
                                            
                                            st.markdown(f"""
                                            <div class="browser-status">
                                                {status_icon} <strong>{browser.capitalize()}:</strong> {error_msg[:100]}
                                            </div>
                                            """, unsafe_allow_html=True)
                                    
                                    # Show specific errors if available
                                    if result.get('detailed_errors'):
                                        with st.expander("🔍 Detailed Error Information", expanded=False):
                                            for error in result['detailed_errors']:
                                                st.text(error)
                                
                                else:
                                    st.markdown("""
                                    <div class="automation-error">
                                        <h4>🚨 General Automation Error</h4>
                                        <p>There's an issue with the Selenium automation setup.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                if result.get('suggestion'):
                                    st.warning(f"💡 {result['suggestion']}")
                                    
                                    if result.get('install_command'):
                                        st.markdown(f"""
                                        <div class="install-command">
                                            {result['install_command']}
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                st.session_state['web_automation_verified'] = False
                    
                    # Automation settings
                    st.markdown("**⚙️ Selenium Settings:**")
                    
                    automation_timeout = st.number_input(
                        "Timeout (seconds)",
                        min_value=10,
                        max_value=120,
                        value=st.session_state.get('automation_timeout', 30),
                        help="Maximum time to wait for web automation"
                    )
                    st.session_state['automation_timeout'] = automation_timeout
                    
                    show_browser = st.checkbox(
                        "Show Browser Window",
                        value=st.session_state.get('automation_show_browser', True),
                        help="Show browser window during automation (useful for debugging)"
                    )
                    st.session_state['automation_show_browser'] = show_browser
                    
                    # Enhanced installation helper
                    st.markdown("**📖 Selenium Installation Commands:**")
                    if st.button("📋 Show Selenium Install Commands", key="copy_selenium_install_cmd"):
                        st.markdown("**Step 1: Install Selenium**")
                        st.code("pip install selenium", language="bash")
                        
                        st.markdown("**Step 2: Install WebDriver Manager**")
                        st.code("pip install webdriver-manager", language="bash")
                        
                        st.markdown("**Optional: Manual ChromeDriver Setup**")
                        st.code("# Download ChromeDriver from https://chromedriver.chromium.org/", language="bash")
                        
                        st.success("✅ Selenium commands ready to copy and run!")
                    
                    # Quick status check
                    if st.session_state.get('web_automation_verified'):
                        st.markdown("""
                        <div class="selenium-automation-section">
                            <h4>🟢 Selenium Automation Active</h4>
                            <p>✅ All dependencies installed and verified</p>
                            <p>🔧 Using Selenium WebDriver for automation</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                else:
                    st.info("💡 Enable to use Selenium-powered restaurant booking automation")
            
            # GoMaps API
            with st.expander("🗺️ GoMaps Pro", expanded=True):
                gomaps_key = st.text_input("API Key", 
                                         value=st.session_state.get('gomaps_key', ''),
                                         type="password", 
                                         key="gomaps_api_key")
                
                if gomaps_key:
                    if st.button("Test Connection", key="test_gomaps_btn"):
                        with st.spinner("Testing..."):
                            result = self.test_gomaps_connection(gomaps_key)
                            if result["success"]:
                                st.success("✅ Connected")
                                st.session_state['gomaps_key'] = gomaps_key
                                st.session_state['gomaps_verified'] = True
                            else:
                                st.error("❌ Failed")
                                st.session_state['gomaps_verified'] = False
                
                if not gomaps_key:
                    st.info("💡 Add GoMaps key for real restaurant data")
            
            # Google Calendar API Configuration
            with st.expander("📅 Google Calendar API", expanded=True):
                st.markdown("**🔧 Real Calendar Integration Setup:**")
                
                calendar_credentials = st.text_area(
                    "Google Calendar Credentials JSON",
                    value=st.session_state.get('calendar_credentials', ''),
                    height=100,
                    help="Paste your Google Calendar API service account JSON credentials here",
                    placeholder='{"type": "service_account", "project_id": "...", ...}'
                )
                
                if calendar_credentials:
                    try:
                        # Validate JSON
                        credentials_data = json.loads(calendar_credentials)
                        if 'type' in credentials_data and 'client_email' in credentials_data:
                            st.session_state['calendar_credentials'] = calendar_credentials
                            st.session_state['calendar_verified'] = True
                            service_email = credentials_data.get("client_email")
                            st.success("✅ Calendar credentials validated")
                            st.info(f"📧 Service Account: `{service_email}`")
                            
                            # Test real calendar access
                            if st.button("🧪 Test Real Calendar Access", key="test_calendar_access"):
                                with st.spinner("Testing real calendar API..."):
                                    test_result = self.test_real_calendar_access()
                                    if test_result["success"]:
                                        st.success(f"✅ {test_result['message']}")
                                        st.info(f"📅 Tested calendar: {test_result['test_email']}")
                                        st.session_state['calendar_real_verified'] = True
                                    else:
                                        st.error(f"❌ {test_result['error']}")
                                        st.warning("💡 Make sure you've shared your calendar with the service account!")
                                        st.session_state['calendar_real_verified'] = False
                        else:
                            st.error("❌ Invalid credentials format")
                            st.session_state['calendar_verified'] = False
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON format")
                        st.session_state['calendar_verified'] = False
                
                # Status display
                if st.session_state.get('calendar_real_verified'):
                    st.success("🟢 **Real calendar integration active!**")
                elif st.session_state.get('calendar_verified'):
                    st.warning("🟡 **Credentials OK, test calendar access above**")
                else:
                    st.info("💡 **Add credentials for real calendar integration**")
            
            # Enhanced Email Configuration
            with st.expander("📧 Email Configuration", expanded=True):
                st.markdown("**📧 SMTP Settings for Email Invitations:**")
                
                # Gmail helper
                st.info("💡 **For Gmail Users:** Use 'App Password', not your regular Gmail password!")
                
                if st.button("📖 How to get Gmail App Password", key="gmail_help"):
                    st.markdown("""
                    **Steps for Gmail App Password:**
                    1. Go to [Gmail Settings](https://myaccount.google.com/security)
                    2. Enable **2-Step Verification** (required)
                    3. Go to **App Passwords**
                    4. Select **Mail** and **Other (Custom name)**
                    5. Generate password and copy it
                    6. Use that password here (not your Gmail password)
                    """)
                
                smtp_server = st.text_input("SMTP Server", 
                                          value=st.session_state.get('smtp_server', 'smtp.gmail.com'),
                                          help="Gmail: smtp.gmail.com | Outlook: smtp-mail.outlook.com")
                
                smtp_port = st.number_input("SMTP Port", 
                                          value=st.session_state.get('smtp_port', 587),
                                          min_value=1, max_value=65535,
                                          help="Gmail: 587 | Outlook: 587")
                
                email_address = st.text_input("Your Email Address",
                                            value=st.session_state.get('email_address', ''),
                                            help="Your full email address")
                
                email_password = st.text_input("Email Password",
                                             value=st.session_state.get('email_password', ''),
                                             type="password",
                                             help="For Gmail: Use App Password (not regular password)")
                
                # Test email configuration
                if email_address and email_password:
                    if st.button("🧪 Test Email Config", key="test_email_btn"):
                        with st.spinner("Testing email configuration..."):
                            result = self.test_email_configuration(smtp_server, smtp_port, email_address, email_password)
                            
                            if result["success"]:
                                st.success("✅ Email configuration successful!")
                                st.session_state.update({
                                    'smtp_server': smtp_server,
                                    'smtp_port': smtp_port,
                                    'email_address': email_address,
                                    'email_password': email_password,
                                    'email_configured': True
                                })
                            else:
                                st.error(f"❌ {result['error']}")
                                if result.get('suggestion'):
                                    st.warning(f"💡 {result['suggestion']}")
                                st.session_state['email_configured'] = False
                
                if st.button("💾 Save Email Config", key="save_email_config"):
                    st.session_state.update({
                        'smtp_server': smtp_server,
                        'smtp_port': smtp_port,
                        'email_address': email_address,
                        'email_password': email_password,
                        'email_configured': bool(email_address and email_password)
                    })
                    st.success("✅ Email configuration saved!")
                
                if not (email_address and email_password):
                    st.info("💡 Configure email to send real invitations")
            
            st.divider()
            
                        # Team Configuration
            st.markdown("### 👥 Team Configuration")
            
            with st.expander("Team Members", expanded=True):
                team_size = st.number_input("Team Size", 
                                          min_value=1, max_value=20, 
                                          value=st.session_state.get('team_size', 6),
                                          key="team_size_input")
                
                # Include the user's actual email by default
                default_emails = f"{st.session_state.get('email_address', 'clips7621@gmail.com')}\nmayank2712005@gmail.com\nbob@company.com\ncharlie@company.com\ndiana@company.com\neve@company.com"
                
                team_emails = st.text_area("Team Email Addresses (one per line)", 
                                         value=st.session_state.get('team_emails_text', default_emails),
                                         height=150,
                                         help="Enter team member email addresses for calendar invitations",
                                         key="team_emails_input")
                
                if st.button("💾 Save Team Info", key="save_team_btn"):
                    # Parse team emails
                    team_emails_list = [email.strip() for email in team_emails.split('\n') if email.strip()]
                    
                    st.session_state.update({
                        'team_size': team_size,
                        'team_emails_text': team_emails,
                        'team_emails': team_emails_list
                    })
                    st.success(f"✅ Saved {len(team_emails_list)} team members!")
            
            st.divider()
            
            # Enhanced System Status
            st.markdown("### 📊 System Status")
            
            if st.session_state.get('gemini_verified'):
                st.markdown("🟢 **AI Engine:** Ready")
            else:
                st.markdown("🔴 **AI Engine:** Setup Required")
            
            # Enhanced Selenium Automation Status
            if st.session_state.get('web_automation_enabled'):
                if st.session_state.get('web_automation_verified'):
                    st.markdown("🟢 **Selenium Automation:** Active 🔧")
                else:
                    st.markdown("🟡 **Selenium Automation:** Enabled (needs testing)")
                    st.caption("💡 Click 'Test Selenium Automation' above")
            else:
                st.markdown("🔵 **Selenium Automation:** Disabled")
            
            if st.session_state.get('gomaps_verified'):
                st.markdown("🟢 **Maps/Places:** Connected")
            else:
                st.markdown("🔵 **Maps/Places:** Demo Mode")
            
            # Real calendar status
            if st.session_state.get('calendar_real_verified'):
                st.markdown("🟢 **Calendar:** Real-Time API ✅")
            elif st.session_state.get('calendar_verified'):
                st.markdown("🟡 **Calendar:** Credentials OK (test access)")
            else:
                st.markdown("🔵 **Calendar:** Not Configured")
            
            if st.session_state.get('email_configured'):
                st.markdown("🟢 **Email:** Configured")
            else:
                st.markdown("🔵 **Email:** Not Configured")
            
            # Team status
            team_count = len(st.session_state.get('team_emails', []))
            st.markdown(f"👥 **Team Members:** {team_count} configured")
    
    def render_main_header(self):
        """Render main header with updated time"""
        st.markdown("""
        <div class="main-header">
            <h1>🤖 ProActive Work-Life Assistant</h1>
            <p>AI-powered task planning with Selenium web automation and real calendar integration</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple stats
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.session_state.get('gemini_verified'):
                st.metric("AI", "Ready", delta="✓")
            else:
                st.metric("AI", "Setup", delta="!")
        
        with col2:
            if st.session_state.get('web_automation_verified'):
                st.metric("Selenium", "Active", delta="🔧")
            else:
                st.metric("Selenium", "Setup", delta="!")
        
        with col3:
            if st.session_state.get('calendar_real_verified'):
                st.metric("Calendar", "Real API", delta="✓")
            else:
                st.metric("Calendar", "Setup", delta="!")
        
        with col4:
            if st.session_state.get('email_configured'):
                st.metric("Email", "Ready", delta="✓")
            else:
                st.metric("Email", "Setup", delta="!")
        
        with col5:
            st.metric("Time", self.current_time.strftime("%H:%M"))
    
    def render_task_examples(self):
        """Render example tasks with Selenium web automation"""
        st.markdown("### 🎯 What I Can Help You With")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🍽️ Restaurant & Dining**
            - Find restaurants anywhere
            - **🔧 Selenium automated reservations**
            - Compare with real data
            - Plan team dinners
            """)
        
        with col2:
            st.markdown("""
            **📅 Event Planning**
            - Check REAL team availability
            - Schedule meetings/events
            - Plan celebrations
            - Send calendar invites
            """)
        
        with col3:
            st.markdown("""
            **🎉 Special Occasions**
            - Birthday celebrations
            - Work anniversaries
            - Team building events
            - Holiday planning
            """)
        
        # Enhanced quick action buttons
        st.markdown("### 🚀 Advanced Quick Actions with Selenium")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🍽️ Selenium Auto-Book", use_container_width=True, key="quick_restaurant"):
                prompt = "Find and automatically book a restaurant for team dinner in Hyderabad using Selenium automation"
                st.session_state.pending_prompt = prompt
                st.rerun()
        
        with col2:
            if st.button("🎉 Celebration", use_container_width=True, key="quick_celebration"):
                prompt = "Plan a team celebration dinner for 6 people in Mumbai with Selenium automated booking"
                st.session_state.pending_prompt = prompt
                st.rerun()
        
        with col3:
            if st.button("📅 Meeting", use_container_width=True, key="quick_meeting"):
                prompt = "Schedule a team meeting for next week"
                st.session_state.pending_prompt = prompt
                st.rerun()
        
        with col4:
            if st.button("🎂 Birthday", use_container_width=True, key="quick_birthday"):
                prompt = "Plan a birthday celebration in Bangalore with Selenium automated reservation"
                st.session_state.pending_prompt = prompt
                st.rerun()
    
    def render_reviews_section(self, restaurant: Dict):
        """Render DISTINCT reviews section with enhanced styling"""
        reviews = self.get_restaurant_reviews(restaurant)
        
        if not reviews:
            return
        
        # DISTINCTIVE REVIEWS SECTION
        st.markdown("""
        <div class="reviews-section">
            <div class="reviews-header">
                🌟 Customer Reviews & Feedback 🌟
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display reviews in distinctive cards
        for i, review in enumerate(reviews[:3]):  # Show top 3 reviews
            st.markdown(f"""
            <div class="review-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                    <span class="review-author">👤 {review.get('author', 'Anonymous')}</span>
                    <div>
                        <span class="review-rating">{'⭐' * int(review.get('rating', 0))}</span>
                        <small style="color: #6c757d; margin-left: 0.5rem;">({review.get('rating', 0)}/5)</small>
                    </div>
                </div>
                <div class="review-text">"{review.get('text', 'No review text')}"</div>
                <div class="review-time">🕐 {review.get('time', 'Recently')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(reviews) > 3:
            st.markdown(f"""
            <div style="text-align: center; margin-top: 1rem; padding: 0.5rem; background: rgba(255,255,255,0.7); border-radius: 8px;">
                <small style="color: #6c757d;">💬 + {len(reviews) - 3} more reviews available in full details</small>
            </div>
            """, unsafe_allow_html=True)
    
    def get_restaurant_reviews(self, restaurant: Dict) -> List[Dict]:
        """Get reviews for a restaurant"""
        # First try to get from recent_reviews
        if restaurant.get('recent_reviews'):
            return restaurant['recent_reviews']
        
        # Generate contextual reviews based on restaurant quality
        rating = restaurant.get('rating', 4.0)
        restaurant_name = restaurant.get('name', 'this restaurant')
        
        if rating >= 4.5:
            return [
                {
                    "author": "Food Critic",
                    "rating": 5,
                    "text": f"Exceptional dining experience at {restaurant_name}! Outstanding food quality, excellent service, and great ambiance.",
                    "time": "2 weeks ago"
                },
                {
                    "author": "Regular Customer",
                    "rating": 5,
                    "text": "Always consistent quality and taste. Perfect for special occasions and team celebrations.",
                    "time": "1 month ago"
                },
                {
                    "author": "Team Lead",
                    "rating": 4,
                    "text": "Great place for corporate dinners. Good portion sizes and accommodating staff for large groups.",
                    "time": "3 weeks ago"
                }
            ]
        elif rating >= 4.0:
            return [
                {
                    "author": "Local Foodie",
                    "rating": 4,
                    "text": f"Good food quality at {restaurant_name}. Reasonable prices and decent service. Would recommend for casual dining.",
                    "time": "1 week ago"
                },
                {
                    "author": "Office Team",
                    "rating": 4,
                    "text": "Nice place for team outings. Good variety of dishes and comfortable seating arrangements.",
                    "time": "2 weeks ago"
                }
            ]
        else:
            return [
                {
                    "author": "Customer",
                    "rating": 3,
                    "text": f"Average experience at {restaurant_name}. Food was okay, service could be better. Suitable for casual dining.",
                    "time": "1 week ago"
                }
            ]
    
    async def check_real_team_availability(self, date: str, team_emails: List[str]) -> Dict:
        """ENHANCED REAL Google Calendar API integration with better conflict detection"""
        try:
            # Check if real calendar integration is properly set up
            if not st.session_state.get('calendar_real_verified'):
                logger.warning("Real calendar not verified, falling back to mock")
                return await self.check_mock_team_availability(date, team_emails, "Real calendar not verified")
            
            # Import Google Calendar libraries
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Get credentials
            credentials_json = st.session_state.get('calendar_credentials')
            if not credentials_json:
                return await self.check_mock_team_availability(date, team_emails, "No credentials")
            
            credentials_data = json.loads(credentials_json)
            
            # Build authenticated service
            credentials = service_account.Credentials.from_service_account_info(
                credentials_data,
                scopes=[
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar.freebusy'
                ]
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Check availability for the date - FIXED timezone handling
            date_start = f"{date}T00:00:00Z"
            date_end = f"{date}T23:59:59Z"
            
            availability_results = {}
            api_calls_made = 0
            team_status = {}
            
            # Check each team member's calendar
            for email in team_emails:
                try:
                    logger.info(f"Checking REAL calendar for: {email}")
                    
                    # REAL API CALL to Google Calendar
                    freebusy_result = service.freebusy().query(
                        body={
                            "timeMin": date_start,
                            "timeMax": date_end,
                            "timeZone": "UTC",
                            "items": [{"id": email}]
                        }
                    ).execute()
                    
                    api_calls_made += 1
                    
                    # Parse the REAL response
                    calendar_data = freebusy_result.get('calendars', {}).get(email, {})
                    busy_times = calendar_data.get('busy', [])
                    errors = calendar_data.get('errors', [])
                    
                    # Create user-friendly team status
                    username = email.split('@')[0]
                    if errors:
                        team_status[username] = {
                            "status": "❓ Calendar not shared",
                            "busy_periods": 0,
                            "details": "Share calendar with service account"
                        }
                    else:
                        # Format busy times for display
                        busy_display = []
                        for busy in busy_times:
                            try:
                                start_time = busy.get('start', '')
                                end_time = busy.get('end', '')
                                if start_time and end_time:
                                    start_dt = self._parse_google_datetime(start_time)
                                    end_dt = self._parse_google_datetime(end_time)
                                    if start_dt and end_dt:
                                        busy_display.append(f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}")
                            except:
                                busy_display.append("Event time")
                        
                        if busy_times:
                            team_status[username] = {
                                "status": f"🔴 {len(busy_times)} event(s)",
                                "busy_periods": len(busy_times),
                                "details": f"Busy: {', '.join(busy_display[:2])}" + (f" +{len(busy_display)-2} more" if len(busy_display) > 2 else "")
                            }
                        else:
                            team_status[username] = {
                                "status": "🟢 Available all day",
                                "busy_periods": 0,
                                "details": "No conflicts found"
                            }
                    
                    availability_results[email] = {
                        "available": len(busy_times) == 0 and len(errors) == 0,
                        "busy_times": busy_times,
                        "errors": errors,
                        "last_checked": self.current_time.isoformat()
                    }
                    
                    # Rate limiting - be nice to Google's API
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error checking REAL calendar for {email}: {str(e)}")
                    username = email.split('@')[0]
                    team_status[username] = {
                        "status": "❌ API Error",
                        "busy_periods": 0,
                        "details": "Check calendar configuration"
                    }
                    availability_results[email] = {
                        "available": False,
                        "busy_times": [],
                        "errors": [{"reason": "api_error", "message": str(e)}],
                        "last_checked": self.current_time.isoformat()
                    }
            
            # Calculate optimal time slots based on REAL data with ENHANCED conflict detection
            time_slots = self._calculate_enhanced_optimal_times(availability_results, team_emails, date)
            
            return {
                "success": True,
                "source": "google_calendar_api",  # REAL source
                "date": date,
                "time_slots": time_slots,
                "total_attendees": len(team_emails),
                "available_attendees": max([slot["available_attendees"] for slot in time_slots]) if time_slots else 0,
                "attendee_emails": team_emails,
                "detailed_availability": availability_results,
                "api_calls_made": api_calls_made,
                "timestamp": self.current_time.isoformat(),
                "service_account": credentials_data.get("client_email"),
                "team_status": team_status  # Enhanced team status
            }
            
        except Exception as e:
            logger.error(f"REAL calendar integration failed: {str(e)}")
            return await self.check_mock_team_availability(date, team_emails, f"API Error: {str(e)}")
    
    def _calculate_enhanced_optimal_times(self, availability_results: Dict, team_emails: List[str], date: str) -> List[Dict]:
        """ENHANCED optimal meeting times calculation with better conflict detection"""
        business_hours = ["17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"]
        time_slots = []
        
        # Parse the target date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            target_date = datetime.now().date()
        
        for time_slot in business_hours:
            available_count = 0
            available_members = []
            unavailable_members = []
            conflicts_found = []
            
            # Convert time slot to datetime for conflict checking
            try:
                # Parse the time slot (e.g., "17:00")
                hour, minute = map(int, time_slot.split(':'))
                
                # Create datetime in UTC (assuming input times are local)
                slot_start = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
                slot_end = slot_start + timedelta(hours=2)  # Assume 2-hour duration
                
                # Convert to UTC for comparison with Google Calendar times
                slot_start_utc = slot_start
                slot_end_utc = slot_end
                
            except Exception as e:
                logger.error(f"Error parsing time slot {time_slot}: {str(e)}")
                # Fallback
                slot_start_utc = self.current_time
                slot_end_utc = self.current_time + timedelta(hours=2)
            
            # Check each team member for conflicts
            for email in team_emails:
                email_data = availability_results.get(email, {})
                
                # Check for API errors first
                if email_data.get('errors'):
                    error_reason = email_data['errors'][0].get('reason', 'unknown_error')
                    unavailable_members.append({
                        "email": email, 
                        "reason": f"calendar_error_{error_reason}",
                        "details": email_data['errors'][0].get('message', 'Calendar access error')
                    })
                    continue
                
                # Enhanced conflict checking
                is_available = True
                member_conflicts = []
                
                for busy_period in email_data.get('busy_times', []):
                    try:
                        # Parse Google Calendar datetime format
                        busy_start_str = busy_period.get('start', '')
                        busy_end_str = busy_period.get('end', '')
                        
                        if busy_start_str and busy_end_str:
                            # Enhanced datetime parsing
                            busy_start = self._parse_google_datetime(busy_start_str)
                            busy_end = self._parse_google_datetime(busy_end_str)
                            
                            if busy_start and busy_end:
                                # Check for overlap with enhanced logic
                                overlap = self._check_time_overlap(slot_start_utc, slot_end_utc, busy_start, busy_end)
                                
                                if overlap:
                                    is_available = False
                                    conflict_detail = {
                                        "start": busy_start.strftime('%H:%M'),
                                        "end": busy_end.strftime('%H:%M'),
                                        "overlap_duration": overlap
                                    }
                                    member_conflicts.append(conflict_detail)
                                    conflicts_found.append(f"{email.split('@')[0]}: {busy_start.strftime('%H:%M')}-{busy_end.strftime('%H:%M')}")
                    
                    except Exception as e:
                        logger.warning(f"Error parsing busy time for {email}: {str(e)}")
                        # If we can't parse, assume there might be a conflict for safety
                        is_available = False
                        member_conflicts.append({"error": str(e)})
                
                if is_available:
                    available_count += 1
                    available_members.append(email)
                else:
                    unavailable_members.append({
                        "email": email, 
                        "reason": "busy", 
                        "conflicts": member_conflicts
                    })
            
            # Create time slot result with enhanced information
            time_slots.append({
                "time": time_slot,
                "available_attendees": available_count,
                "total_attendees": len(team_emails),
                "available_members": available_members,
                "unavailable_members": unavailable_members,
                "availability_percentage": (available_count / len(team_emails)) * 100,
                "slot_start": slot_start_utc.isoformat(),
                "slot_end": slot_end_utc.isoformat(),
                "availability_source": "google_calendar_api",
                "conflicts_summary": conflicts_found,
                "debug_slot": f"Checking {time_slot} on {date}"
            })
        
        # Sort by availability percentage
        time_slots.sort(key=lambda x: x["availability_percentage"], reverse=True)
        
        return time_slots
    
    def _parse_google_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Enhanced Google Calendar datetime parsing"""
        try:
            # Handle different Google Calendar datetime formats
            if datetime_str.endswith('Z'):
                # UTC format: "2025-07-21T17:00:00Z"
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00')).replace(tzinfo=None)
            elif '+' in datetime_str:
                # With timezone: "2025-07-21T17:00:00+05:30"
                return datetime.fromisoformat(datetime_str).replace(tzinfo=None)
            else:
                # Assume UTC if no timezone
                return datetime.fromisoformat(datetime_str)
        except Exception as e:
            logger.error(f"Failed to parse datetime '{datetime_str}': {str(e)}")
            return None
    
    def _check_time_overlap(self, slot_start: datetime, slot_end: datetime, busy_start: datetime, busy_end: datetime) -> Optional[int]:
        """Enhanced time overlap checking"""
        try:
            # Check if there's any overlap
            latest_start = max(slot_start, busy_start)
            earliest_end = min(slot_end, busy_end)
            
            if latest_start < earliest_end:
                # There is overlap
                overlap_duration = (earliest_end - latest_start).total_seconds() / 60  # in minutes
                return int(overlap_duration)
            else:
                # No overlap
                return None
        except Exception as e:
            logger.error(f"Error checking overlap: {str(e)}")
            return 1  # Assume overlap if error
    
    async def check_mock_team_availability(self, date: str, team_emails: List[str], reason: str = "Real calendar not configured") -> Dict:
        """Fallback mock availability check with clear labeling"""
        try:
            logger.warning(f"Using MOCK availability data: {reason}")
            
            import random
            
            # Simulate realistic availability
            time_slots = []
            business_hours = ["17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"]
            
            for time_slot in business_hours:
                # Simulate availability based on time (more realistic than 100%)
                if time_slot in ["19:00", "19:30", "20:00"]:
                    base_availability = 0.75  # 75% during peak dinner time
                elif time_slot in ["17:00", "17:30"]:
                    base_availability = 0.6   # 60% during early dinner
                elif time_slot in ["21:00", "21:30"]:
                    base_availability = 0.5   # 50% during late dinner
                else:
                    base_availability = 0.7   # 70% other times
                
                available_count = 0
                available_members = []
                unavailable_members = []
                
                for email in team_emails:
                    # Add some deterministic behavior based on email and time
                    seed_value = hash(f"{email}{time_slot}{date}") % 100
                    is_available = (seed_value / 100) < base_availability
                    
                    if is_available:
                        available_count += 1
                        available_members.append(email)
                    else:
                        unavailable_members.append({
                            "email": email,
                            "reason": "simulated_busy",
                            "conflicts": [{"start": f"{date} {time_slot}", "end": f"{date} {time_slot}"}]
                        })
                
                time_slots.append({
                    "time": time_slot,
                    "available_attendees": available_count,
                    "total_attendees": len(team_emails),
                    "available_members": available_members,
                    "unavailable_members": unavailable_members,
                    "availability_percentage": (available_count / len(team_emails)) * 100,
                    "availability_source": "mock_availability"
                })
            
            # Sort by availability
            time_slots.sort(key=lambda x: x["availability_percentage"], reverse=True)
            
            return {
                "success": True,
                "source": "mock_availability",  # Clear mock labeling
                "fallback_reason": reason,
                "date": date,
                "time_slots": time_slots,
                "total_attendees": len(team_emails),
                "available_attendees": max([slot["available_attendees"] for slot in time_slots]) if time_slots else 0,
                "attendee_emails": team_emails,
                "timestamp": self.current_time.isoformat(),
                "note": "This is simulated data - configure Google Calendar API for real availability"
            }
            
        except Exception as e:
            logger.error(f"Mock availability check failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def render_enhanced_availability_analysis(self, availability_result: Dict, user_input: str = "", selected_date=None):
        """STREAMLINED availability analysis with merged smart recommendations"""
        if not availability_result.get("success"):
            return
        
        # Detect request type for smart recommendations
        request_type = self.detect_request_type(user_input) if user_input else "DINNER"
        preferences = self.get_request_preferences(request_type)
        
        st.markdown("### 📊 Smart Team Availability Analysis")
        
        # Enhanced header with request type context
        if availability_result.get("source") == "google_calendar_api":
            st.markdown("""
            <div class="enhanced-availability">
                <h4>✅ Real Calendar Analysis with Smart Recommendations</h4>
                <p><strong>🔗 Using Google Calendar API</strong> - Live team calendar data with AI-powered time suggestions</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"📊 Made {availability_result.get('api_calls_made', 0)} API calls • 🔗 Service Account: {availability_result.get('service_account', 'Unknown')}")
            
            # USER-FRIENDLY team status summary
            team_status = availability_result.get('team_status', {})
            if team_status:
                st.markdown("""
                <div class="team-status-summary">
                    <h4>👥 Team Status Summary</h4>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                for i, (member, status_info) in enumerate(team_status.items()):
                    with col1 if i % 2 == 0 else col2:
                        status_text = status_info.get("status", "Unknown")
                        details = status_info.get("details", "")
                        
                        if "🟢" in status_text:
                            st.success(f"**{member}:** {status_text}")
                        elif "🔴" in status_text:
                            st.error(f"**{member}:** {status_text}")
                            if details:
                                st.caption(f"📋 {details}")
                        else:
                            st.warning(f"**{member}:** {status_text}")
                            if details:
                                st.caption(f"📋 {details}")
        else:
            st.warning("🔵 **SIMULATED Data** - Using mock availability")
            if availability_result.get('fallback_reason'):
                st.error(f"❌ Fallback reason: {availability_result['fallback_reason']}")
            st.info("💡 Configure Google Calendar API credentials and test access for real data")
        
        # Show detected event type
        if user_input:
            st.info(f"🎯 **Detected Event Type:** {preferences['name']} - {preferences['description']}")
        
        # MERGED smart recommendations with availability analysis
        best_slots = availability_result.get("time_slots", [])[:5]
        if best_slots:
            st.markdown("**🕐 Recommended Times (Smart AI + Real Availability):**")
            
            for i, slot in enumerate(best_slots, 1):
                availability_pct = slot.get("availability_percentage", 0)
                time_str = slot['time']
                
                # Calculate smart recommendation score
                hour = int(time_str.split(':')[0])
                day_score = 1.2 if selected_date and selected_date.weekday() in preferences["optimal_days"] else 1.0
                time_score = 1.0 if hour in preferences["preferred_hours"] else 0.5
                
                # Combined score (availability + smart recommendations)
                combined_score = (availability_pct/100 * 0.6) + (time_score * 0.3) + (day_score * 0.1)
                
                # Enhanced status with smart context
                if combined_score >= 0.9 and availability_pct >= 80:
                    color = "🟢"
                    status = "Perfect"
                    reasons = ["High availability", f"Optimal for {preferences['name']}"]
                elif combined_score >= 0.7 or availability_pct >= 60:
                    color = "🟡"
                    status = "Good" 
                    reasons = []
                    if availability_pct >= 60:
                        reasons.append("Good availability")
                    if hour in preferences["preferred_hours"]:
                        reasons.append(f"Preferred for {preferences['name']}")
                else:
                    color = "🔴"
                    status = "Limited"
                    reasons = ["Low availability"]
                
                # Show conflicts if any
                conflicts = slot.get('conflicts_summary', [])
                unavailable = slot.get('unavailable_members', [])
                
                conflict_text = ""
                if conflicts:
                    conflict_text = f" - {', '.join(conflicts[:1])}"
                    if len(conflicts) > 1:
                        conflict_text += f" +{len(conflicts)-1} more"
                elif unavailable:
                    unavailable_names = [m.get('email', '').split('@')[0] for m in unavailable if isinstance(m, dict)]
                    if unavailable_names:
                        conflict_text = f" - {', '.join(unavailable_names[:2])} busy"
                        if len(unavailable_names) > 2:
                            conflict_text += f" +{len(unavailable_names)-2} more"
                
                # Display enhanced result with smart context
                reason_text = " • ".join(reasons) if reasons else ""
                display_text = f"{color} **{time_str}** - {slot['available_attendees']}/{slot['total_attendees']} available ({availability_pct:.0f}%) {status}"
                
                if reason_text:
                    display_text += f" - {reason_text}"
                if conflict_text:
                    display_text += conflict_text
                
                if combined_score >= 0.8:
                    st.success(display_text)
                elif combined_score >= 0.6:
                    st.warning(display_text)
                else:
                    st.error(display_text)
    
    def render_options(self, options_data: Dict, message_id: int):
        """Render options with REAL team availability integration and Selenium automation badges"""
        st.markdown("### 🎯 Available Options")
        
        # Show search info with REAL availability
        if options_data.get("note"):
            st.info(f"ℹ️ {options_data['note']}")
        
        # Show REAL team availability information
        if options_data.get("availability_source"):
            if options_data["availability_source"] == "google_calendar_api":
                st.markdown("""
                <div class="real-calendar-info">
                    <h4>✅ Real Team Availability Integration</h4>
                    <p><strong>🔗 Using Google Calendar API</strong> - Checking actual team calendars</p>
                    <p>📊 Availability data is pulled from real calendar events</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="availability-info">
                    <h4>🔵 Simulated Team Availability</h4>
                    <p><strong>Demo Mode</strong> - Configure Google Calendar API for real data</p>
                    <p>📊 Showing realistic availability simulation</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Show Selenium automation status
        if st.session_state.get('web_automation_enabled'):
            if st.session_state.get('web_automation_verified'):
                st.markdown("""
                <div class="selenium-automation-section">
                    <h4>🔧 Selenium Automation Ready</h4>
                    <p><strong>⚡ AI-Powered Selenium Booking</strong> - Restaurants with websites can be booked automatically using Selenium WebDriver</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("🟡 **Selenium Automation Enabled** - Test automation in sidebar to activate")
        
        # Get original options
        original_options = options_data.get("options", [])
        
        # Filters
        if f"sort_value_{message_id}" not in st.session_state:
            st.session_state[f"sort_value_{message_id}"] = "Rating"
        if f"rating_value_{message_id}" not in st.session_state:
            st.session_state[f"rating_value_{message_id}"] = 0.0
        if f"open_value_{message_id}" not in st.session_state:
            st.session_state[f"open_value_{message_id}"] = False
        
        with st.expander("🔧 Filter & Sort Options", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sort_by = st.selectbox("Sort by:", ["Rating", "Price", "Reviews", "Name"], 
                                     index=["Rating", "Price", "Reviews", "Name"].index(st.session_state[f"sort_value_{message_id}"]),
                                     key=f"sort_{message_id}")
                st.session_state[f"sort_value_{message_id}"] = sort_by
            
            with col2:
                min_rating = st.slider("Min Rating", 0.0, 5.0, 
                                     value=st.session_state[f"rating_value_{message_id}"], 
                                     step=0.1,
                                     key=f"rating_{message_id}")
                st.session_state[f"rating_value_{message_id}"] = min_rating
            
            with col3:
                show_open_only = st.checkbox("Open Now Only", 
                                           value=st.session_state[f"open_value_{message_id}"],
                                           key=f"open_{message_id}")
                st.session_state[f"open_value_{message_id}"] = show_open_only
        
        # Apply filters and sorting
        filtered_options = []
        
        for option in original_options:
            restaurant = option.get("restaurant", {})
            
            # Apply rating filter
            restaurant_rating = restaurant.get("rating", 0)
            if restaurant_rating < min_rating:
                continue
            
            # Apply open now filter
            if show_open_only and not restaurant.get("open_now", False):
                continue
            
            filtered_options.append(option)
        
        # Apply sorting
        if sort_by == "Rating":
            filtered_options.sort(key=lambda x: x.get("restaurant", {}).get("rating", 0), reverse=True)
        elif sort_by == "Price":
            price_order = {"₹ (Budget)": 1, "₹₹ (Moderate)": 2, "₹₹₹ (Expensive)": 3, "₹₹₹₹ (Very Expensive)": 4}
            filtered_options.sort(key=lambda x: price_order.get(x.get("restaurant", {}).get("price_range", "₹₹ (Moderate)"), 2))
        elif sort_by == "Reviews":
            filtered_options.sort(key=lambda x: x.get("restaurant", {}).get("user_ratings_total", 0), reverse=True)
        elif sort_by == "Name":
            filtered_options.sort(key=lambda x: x.get("restaurant", {}).get("name", "").lower())
        
        # Show filter results
        if len(filtered_options) != len(original_options):
            st.info(f"🔍 Showing {len(filtered_options)} of {len(original_options)} options (filtered by: Rating ≥ {min_rating}" + 
                    (", Open Now" if show_open_only else "") + f", Sorted by: {sort_by})")
        
        # Track button clicks to avoid reprocessing
        if f"selected_option_{message_id}" not in st.session_state:
            st.session_state[f"selected_option_{message_id}"] = None
        
        # Display filtered and sorted options with Selenium automation badges
        if not filtered_options:
            st.warning("🚫 No restaurants match your filter criteria. Try adjusting the filters.")
            return
        
        for i, option in enumerate(filtered_options, 1):
            restaurant = option.get("restaurant", {})
            time_slot = option.get("time_slot", {})
            
            with st.container():
                st.markdown(f"""
                <div class="option-card">
                    <h4>🍽️ Option {i}: {restaurant.get('name', 'Unknown Restaurant')}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Restaurant photo
                    photo_reference = restaurant.get("photo_reference")
                    if photo_reference and st.session_state.get('gomaps_key'):
                        photo_url = f"https://maps.gomaps.pro/maps/api/place/photo?photo_reference={photo_reference}&maxwidth=400&key={st.session_state['gomaps_key']}"
                        try:
                            st.image(photo_url, caption=f"📸 {restaurant.get('name')}", width=400)
                        except:
                            st.caption("📷 Photo not available")
                    
                    # Restaurant details
                    st.markdown(f"**📍 Address:** {restaurant.get('address', 'N/A')}")
                    st.markdown(f"**⭐ Rating:** {restaurant.get('rating', 'N/A')} ({restaurant.get('user_ratings_total', 0)} reviews)")
                    st.markdown(f"**💰 Price:** {restaurant.get('price_range', 'N/A')}")
                    st.markdown(f"**🍽️ Cuisine:** {', '.join(restaurant.get('cuisine', ['N/A']))}")
                    
                    # REAL/MOCK team availability display
                    availability_percentage = (time_slot.get('available_attendees', 0) / time_slot.get('total_attendees', 6)) * 100
                    st.markdown(f"**👥 Team Availability:** {time_slot.get('available_attendees', 0)}/{time_slot.get('total_attendees', 6)} members ({availability_percentage:.0f}%)")
                    
                    # Contact info
                    if restaurant.get("phone"):
                        st.markdown(f"**📞 Phone:** {restaurant['phone']}")
                    if restaurant.get("website") and restaurant.get("website") not in ['Not available', 'Contact for details']:
                        st.markdown(f"**🌐 Website:** [Visit]({restaurant['website']})")
                    
                    # Reviews section
                    self.render_reviews_section(restaurant)
                
                with col2:
                    # Enhanced status badges with Selenium automation
                    if restaurant.get("open_now"):
                        st.markdown('<span class="status-badge status-success">🟢 Open Now</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-badge status-warning">🔴 Closed</span>', unsafe_allow_html=True)
                    
                    if restaurant.get("source") == "gomaps_api":
                        st.markdown('<span class="status-badge status-info">✅ Real Data</span>', unsafe_allow_html=True)
                    
                    # Show availability source
                    availability_source = time_slot.get("availability_source", "unknown")
                    if availability_source == "google_calendar_api":
                        st.markdown('<span class="status-badge status-success">📅 Real Calendar</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-badge status-warning">📅 Demo Calendar</span>', unsafe_allow_html=True)
                    
                    # Selenium automation capability badge
                    if st.session_state.get('web_automation_verified') and restaurant.get('website') and restaurant.get('website').startswith('http'):
                        st.markdown('<span class="status-badge status-success">🔧 Selenium Ready</span>', unsafe_allow_html=True)
                    elif restaurant.get('website'):
                        st.markdown('<span class="status-badge status-warning">🌐 Website Available</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-badge status-error">📞 Phone Only</span>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown("**🎯 Actions:**")
                    
                    # Main selection button
                    try:
                        original_index = original_options.index(option)
                    except ValueError:
                        # If option not found in original list, use current index
                        original_index = i - 1
                    
                    select_key = f"select_{message_id}_{original_index}_{i}"
                    if st.button(f"✅ Select This Option", key=select_key, use_container_width=True, type="primary"):
                        # Store selection and trigger time selection with auto-scroll
                        st.session_state[f"selected_option_{message_id}"] = (original_index, options_data, option)
                        st.session_state[f"show_time_selection_{message_id}"] = True
                        st.session_state[f"scroll_to_reservation_{message_id}"] = True
                        st.rerun()
                    
                    # Secondary actions
                    map_key = f"map_{message_id}_{original_index}_{i}"
                    if st.button(f"📍 View on Map", key=map_key, use_container_width=True):
                        self.show_map(restaurant)
                    
                    details_key = f"details_{message_id}_{original_index}_{i}"
                    if st.button(f"📋 Full Details", key=details_key, use_container_width=True):
                        self.show_details(restaurant)
                
                st.divider()
        
        # Show time selection if triggered
        if st.session_state.get(f"show_time_selection_{message_id}"):
            selection_data = st.session_state.get(f"selected_option_{message_id}")
            if selection_data:
                if len(selection_data) == 3:
                    option_index, options_data, selected_option = selection_data
                else:
                    option_index, options_data = selection_data
                    selected_option = options_data["options"][option_index]
                self.render_reservation_menu(selected_option, options_data, message_id)
    
    def render_reservation_menu(self, selected_option: Dict, options_data: Dict, message_id: int):
        """FIXED reservation menu with proper session state management"""
        restaurant = selected_option.get("restaurant", {})
        
        # Get user input for smart recommendations
        user_input = st.session_state.get('last_user_input', '')
        
        # Auto-scroll implementation
        scroll_to_reservation = st.session_state.get(f"scroll_to_reservation_{message_id}", False)
        
        if scroll_to_reservation:
            st.session_state[f"scroll_to_reservation_{message_id}"] = False
            st.balloons()
            st.markdown("---" * 20)
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; 
                        padding: 2rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        margin: 2rem 0; 
                        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);">
                <h2>🎯 COMPLETE YOUR BOOKING BELOW 👇</h2>
                <h3>📍 {restaurant.get('name', 'Restaurant')}</h3>
                <p style="font-size: 1.2rem;">✨ Your table is waiting! ✨</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.success("🎉 **Great choice!** Complete your reservation details below ⬇️⬇️⬇️")
            st.info("📋 **Next Step:** Select your preferred date, time, and party size, then click 'Confirm Booking'")
        
        # Beautiful reservation section header
        st.markdown(f"""
        <div class="time-selection scroll-target">
            <h3>🕐 Select Your Reservation Time</h3>
            <p>You selected: <strong>{restaurant.get('name', 'Unknown')}</strong></p>
            <p>📍 {restaurant.get('address', 'N/A')[:60]}...</p>
            <p>⭐ {restaurant.get('rating', 'N/A')} stars • {restaurant.get('price_range', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("### 📅 Booking Details")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Date selection - Using current date from system
                current_date = self.current_time.date()  # 2025-07-20
                min_date = current_date
                max_date = current_date + timedelta(days=30)
                
                # Default to tomorrow (2025-07-21)
                default_date = current_date + timedelta(days=1)
                
                selected_date = st.date_input(
                    "📅 Select Date",
                    min_value=min_date,
                    max_value=max_date,
                    value=default_date,
                    key=f"date_selection_{message_id}",
                    help="Choose your preferred date"
                )
            
            with col2:
                # Time selection
                time_options = [
                    "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", 
                    "20:00", "20:30", "21:00", "21:30", "22:00"
                ]
                
                selected_time = st.selectbox(
                    "🕐 Select Time",
                    options=time_options,
                    index=5,  # Default to 19:30
                    key=f"time_selection_{message_id}",
                    help="Choose your preferred time"
                )
            
            with col3:
                # Party size
                party_size = st.number_input(
                    "👥 Party Size",
                    min_value=1,
                    max_value=20,
                    value=st.session_state.get('team_size', 6),
                    key=f"party_size_{message_id}",
                    help="Number of people dining"
                )
            
            # STREAMLINED REAL TEAM AVAILABILITY CHECK with MERGED smart recommendations
            if st.session_state.get('team_emails'):
                with st.spinner("📅 Analyzing team availability with smart recommendations..."):
                    availability_result = asyncio.run(
                        self.check_real_team_availability(
                            selected_date.strftime("%Y-%m-%d"), 
                            st.session_state['team_emails'][:party_size]
                        )
                    )
                
                if availability_result.get("success"):
                    # Use STREAMLINED enhanced availability analysis with merged smart recommendations
                    self.render_enhanced_availability_analysis(availability_result, user_input, selected_date)
                    
                    # Simple conflict warning for selected time
                    best_slots = availability_result.get("time_slots", [])
                    if best_slots:
                        current_slot = None
                        for slot in best_slots:
                            if slot['time'] == selected_time:
                                current_slot = slot
                                break
                        
                        if current_slot and current_slot.get('availability_percentage', 0) < 100:
                            best_available = best_slots[0]
                            if best_available.get('availability_percentage', 0) > current_slot.get('availability_percentage', 0):
                                st.warning(f"⚠️ **Selected time {selected_time} has conflicts!** Consider {best_available['time']} instead ({best_available['availability_percentage']:.0f}% available)")
            
            # Show booking summary
            st.markdown("### 📋 Booking Summary")
            
            booking_col1, booking_col2 = st.columns(2)
            
            with booking_col1:
                st.info(f"""
                **🍽️ Restaurant:** {restaurant.get('name', 'N/A')}
                **📞 Phone:** {restaurant.get('phone', 'N/A')}
                **⭐ Rating:** {restaurant.get('rating', 'N/A')}
                **💰 Price:** {restaurant.get('price_range', 'N/A')}
                """)
            
            with booking_col2:
                st.info(f"""
                **📅 Date:** {selected_date}
                **🕐 Time:** {selected_time}
                **👥 Party Size:** {party_size} people
                **👤 Booked by:** {self.current_user}
                **🕐 Booking Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
                """)
            
            # Enhanced confirmation buttons with Selenium automation - FIXED SESSION STATE HANDLING
            st.markdown("### 🎯 Confirm Your Booking")
            
            # Check if Selenium automation is available for this restaurant
            automation_available = (
                st.session_state.get('web_automation_enabled') and 
                st.session_state.get('web_automation_verified') and 
                restaurant.get('website') and 
                restaurant.get('website').startswith('http')
            )
            
            if automation_available:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"🔧 Selenium Auto-Book", key=f"confirm_selenium_booking_{message_id}", type="primary", use_container_width=True):
                        # FIXED: Create updated time slot BEFORE processing
                        updated_time_slot = {
                            "date": selected_date.strftime("%Y-%m-%d"),
                            "time": selected_time,
                            "available_attendees": party_size,
                            "total_attendees": party_size,
                            "attendee_emails": st.session_state.get('team_emails', [])[:party_size],
                            "availability_source": availability_result.get("source", "mock") if 'availability_result' in locals() else "mock",
                            "booking_method": "selenium_automated_booking"
                        }
                        
                        # Update the selected option
                        selected_option["time_slot"] = updated_time_slot
                        
                        # FIXED: Store booking in progress to prevent session reset
                        st.session_state[f"booking_in_progress_{message_id}"] = True
                        st.session_state[f"booking_restaurant_{message_id}"] = restaurant
                        st.session_state[f"booking_time_slot_{message_id}"] = updated_time_slot
                        
                        # Process the ENHANCED booking with Selenium automation
                        try:
                            result = self.attempt_selenium_automation_booking(restaurant, updated_time_slot, message_id)
                            # Don't clear session state immediately - let the booking complete
                            return result
                        except Exception as e:
                            st.error(f"❌ Selenium booking failed: {str(e)}")
                            # Clear booking in progress on error
                            st.session_state[f"booking_in_progress_{message_id}"] = False
                
                with col2:
                    if st.button(f"📞 Manual Booking", key=f"confirm_manual_booking_{message_id}", use_container_width=True):
                        # Update the time slot with user selections
                        updated_time_slot = {
                            "date": selected_date.strftime("%Y-%m-%d"),
                            "time": selected_time,
                            "available_attendees": party_size,
                            "total_attendees": party_size,
                            "attendee_emails": st.session_state.get('team_emails', [])[:party_size],
                            "availability_source": availability_result.get("source", "mock") if 'availability_result' in locals() else "mock",
                            "booking_method": "manual"
                        }
                        
                        # Update the selected option
                        selected_option["time_slot"] = updated_time_slot
                        
                        # Process manual booking directly
                        self.process_manual_booking(restaurant, updated_time_slot, message_id)
                        
                        # Clear selection state only after successful booking
                        st.session_state[f"show_time_selection_{message_id}"] = False
                        st.session_state[f"selected_option_{message_id}"] = None
                
                # Show automation status
                st.info(f"🔧 **Selenium Automation Available** - AI can automatically fill reservation forms on {restaurant.get('website', 'website')} using Selenium WebDriver")
            
            else:
                # Standard booking without automation
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"✅ Confirm Booking", key=f"confirm_booking_{message_id}", type="primary", use_container_width=True):
                        # Update the time slot with user selections
                        updated_time_slot = {
                            "date": selected_date.strftime("%Y-%m-%d"),
                            "time": selected_time,
                            "available_attendees": party_size,
                            "total_attendees": party_size,
                            "attendee_emails": st.session_state.get('team_emails', [])[:party_size],
                            "availability_source": availability_result.get("source", "mock") if 'availability_result' in locals() else "mock",
                            "booking_method": "manual"
                        }
                        
                        # Update the selected option
                        selected_option["time_slot"] = updated_time_slot
                        
                        # Process manual booking
                        self.process_manual_booking(restaurant, updated_time_slot, message_id)
                        
                        # Clear selection state
                        st.session_state[f"show_time_selection_{message_id}"] = False
                        st.session_state[f"selected_option_{message_id}"] = None
                
                with col2:
                    if st.button(f"❌ Cancel", key=f"cancel_booking_{message_id}", use_container_width=True):
                        # Clear selection state
                        st.session_state[f"show_time_selection_{message_id}"] = False
                        st.session_state[f"selected_option_{message_id}"] = None
                        st.info("Booking cancelled. You can select a different option above.")
                        st.rerun()
                
                # Show why automation isn't available
                if not st.session_state.get('web_automation_enabled'):
                    st.info("💡 **Enable Selenium Automation** in the sidebar to automatically fill reservation forms")
                elif not st.session_state.get('web_automation_verified'):
                    st.warning("⚠️ **Selenium Automation** enabled but not tested - verify in sidebar")
                elif not restaurant.get('website'):
                    st.info("📞 **Phone Booking Required** - This restaurant doesn't have an online booking website")
                else:
                    st.info("🌐 **Website Available** - Manual booking process will be used")
    
    def attempt_selenium_automation_booking(self, restaurant: Dict, time_slot: Dict, message_id: int):
        """FIXED Selenium automation booking with proper flow control"""
        try:
            if not self.web_automation:
                self.initialize_web_automation()
            
            if not self.web_automation:
                st.error("❌ Selenium automation not available")
                # Clear booking in progress
                st.session_state[f"booking_in_progress_{message_id}"] = False
                return self.process_manual_booking(restaurant, time_slot, message_id)
            
            st.markdown("### 🔧 Selenium Automated Booking in Progress")
            
            # Prepare booking details
            booking_details = {
                "date": time_slot.get('date'),
                "time": time_slot.get('time'),
                "party_size": time_slot.get('total_attendees'),
                "contact_name": self.current_user,
                "contact_phone": st.session_state.get('contact_phone', '+1234567890'),
                "contact_email": st.session_state.get('email_address', 'user@example.com')
            }
            
            with st.spinner("🔄 Analyzing restaurant website and attempting Selenium automation..."):
                # First analyze the website
                analysis_result = asyncio.run(
                    self.web_automation.analyze_restaurant_website(restaurant.get('website'))
                )
                
                if analysis_result.get("success"):
                    analysis = analysis_result.get("analysis", {})
                    
                    st.markdown("""
                    <div class="automation-status">
                        <h4>🔍 Website Analysis Complete</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**🌐 Website:** {restaurant.get('website')[:40]}...")
                        st.info(f"**📋 Booking Method:** {analysis.get('booking_method', 'Unknown')}")
                        st.info(f"**🎯 Feasibility:** {analysis.get('automation_feasibility', 'Unknown')}")
                    
                    with col2:
                        st.info(f"**📝 Has Online Booking:** {'✅ Yes' if analysis.get('has_online_booking') else '❌ No'}")
                        
                        technical = analysis_result.get("technical_details", {})
                        st.info(f"**🔍 Forms Found:** {technical.get('forms_found', 0)}")
                        st.info(f"**📊 Booking Elements:** {technical.get('potential_booking_elements', 0)}")
                    
                    # Show required fields
                    if analysis.get('required_fields'):
                        st.markdown("**📝 Required Fields Detected:**")
                        fields_text = ", ".join(analysis['required_fields'])
                        st.text(fields_text)
                    
                    # Attempt automation if feasible
                    if analysis.get('automation_feasibility') in ['high', 'medium']:
                        st.info("🔧 **Attempting Selenium automated booking...** This may take 30-60 seconds.")
                        
                        # Attempt the actual booking
                        booking_result = asyncio.run(
                            self.web_automation.attempt_automated_booking(restaurant, booking_details)
                        )
                        
                        if booking_result.get("success"):
                            st.markdown("""
                            <div class="automation-status">
                                <h4>🎉 Selenium Automated Booking Successful!</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.success(f"✅ **Booking Confirmation:** {booking_result.get('confirmation', 'SELENIUM_BOOKING')}")
                            
                            # Show automation log
                            if booking_result.get('automation_log'):
                                with st.expander("🔍 Selenium Automation Log", expanded=False):
                                    st.markdown('<div class="automation-log">', unsafe_allow_html=True)
                                    for log_entry in booking_result['automation_log']:
                                        st.text(log_entry)
                                    st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Complete booking process and clear session
                            result = self.complete_selenium_automated_booking(restaurant, time_slot, booking_result, message_id)
                            
                            # Clear session state after successful booking
                            st.session_state[f"show_time_selection_{message_id}"] = False
                            st.session_state[f"selected_option_{message_id}"] = None
                            st.session_state[f"booking_in_progress_{message_id}"] = False
                            
                            return result
                        
                        else:
                            st.warning("⚠️ **Selenium automation partially completed** - Manual verification may be required")
                            
                            # Show what was attempted
                            if booking_result.get('automation_log'):
                                with st.expander("🔍 Selenium Attempt Log", expanded=True):
                                    st.markdown('<div class="automation-log">', unsafe_allow_html=True)
                                    for log_entry in booking_result['automation_log']:
                                        st.text(log_entry)
                                    st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.error(f"❌ {booking_result.get('error', 'Selenium automation failed')}")
                            
                            # Clear booking in progress and fallback to manual
                            st.session_state[f"booking_in_progress_{message_id}"] = False
                            st.info("📞 **Falling back to manual booking process...**")
                            return self.process_manual_booking(restaurant, time_slot, message_id)
                    
                    else:
                        st.warning(f"⚠️ **Website automation not feasible** - {analysis.get('automation_feasibility', 'Unknown')} feasibility")
                        
                        # Show challenges
                        if analysis.get('challenges'):
                            st.markdown("**🚧 Automation Challenges:**")
                            for challenge in analysis['challenges']:
                                st.text(f"• {challenge}")
                        
                        # Clear booking in progress and fallback to manual
                        st.session_state[f"booking_in_progress_{message_id}"] = False
                        return self.process_manual_booking(restaurant, time_slot, message_id)
                
                else:
                    st.error(f"❌ **Website analysis failed:** {analysis_result.get('error', 'Unknown error')}")
                    # Clear booking in progress and fallback to manual
                    st.session_state[f"booking_in_progress_{message_id}"] = False
                    return self.process_manual_booking(restaurant, time_slot, message_id)
        
        except Exception as e:
            st.error(f"❌ **Selenium automation error:** {str(e)}")
            logger.error(f"Selenium automation failed: {str(e)}")
            # Clear booking in progress and fallback to manual
            st.session_state[f"booking_in_progress_{message_id}"] = False
            return self.process_manual_booking(restaurant, time_slot, message_id)
    
    def complete_selenium_automated_booking(self, restaurant: Dict, time_slot: Dict, booking_result: Dict, message_id: int):
        """Complete the Selenium automated booking process"""
        try:
            # Generate confirmation ID
            confirmation_id = booking_result.get('confirmation', f"SELENIUM_{self.current_time.strftime('%Y%m%d%H%M%S')}")
            
            # Create calendar link
            calendar_result = self.create_working_calendar_link(restaurant, time_slot, confirmation_id)
            
            # Send email invitations
            email_result = asyncio.run(self.send_real_email_invitations(restaurant, time_slot, calendar_result))
            
            # Show comprehensive results
            st.markdown("### ✅ Selenium Automated Booking Complete!")
            
            with st.expander("📋 Complete Selenium Booking Results", expanded=True):
                # Automated reservation success
                st.markdown("**🔧 Selenium Automated Reservation:**")
                st.success(f"✅ **Confirmation ID:** {confirmation_id}")
                st.success(f"✅ **Method:** Selenium automated web booking")
                st.info(f"🕐 **Completed at:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                if booking_result.get('final_url'):
                    st.info(f"🌐 **Final URL:** {booking_result['final_url'][:60]}...")
                
                if booking_result.get('screenshot'):
                    st.info(f"📸 **Screenshot saved:** {booking_result['screenshot']}")
                
                # Calendar event
                st.markdown("**📅 Calendar Event:**")
                if calendar_result.get("success"):
                    st.success("✅ Universal calendar link created!")
                    
                    if calendar_result.get('event_link'):
                        st.markdown(f"🔗 [Add to Your Calendar]({calendar_result['event_link']})")
                    
                    st.success("📊 **Time selected based on Selenium automation + real team availability**")
                else:
                    st.error(f"❌ Calendar event failed: {calendar_result.get('error', 'Unknown error')}")
                
                # Email invitations
                st.markdown("**📧 Email Invitations:**")
                if email_result.get("success"):
                    st.success(f"✅ Email invitations sent to {email_result.get('sent_count', 0)} team members!")
                    
                    if email_result.get('sent_emails'):
                        st.markdown("**📧 Invitations sent to:**")
                        for email in email_result['sent_emails']:
                            st.write(f"• ✅ {email}")
                else:
                    st.warning(f"⚠️ Email sending failed: {email_result.get('error', 'Email not configured')}")
            
            # Next steps for Selenium automated booking
            with st.expander("📋 Selenium Automation - What's Next?", expanded=True):
                steps = [
                    "🎉 **Selenium automated booking completed successfully!**",
                    f"📞 **Optional:** Call {restaurant.get('phone', 'restaurant')} to double-confirm reservation",
                    f"📅 Click the calendar link to add event for {time_slot.get('date')} at {time_slot.get('time')}",
                    "📧 Team members received email invitations with calendar links",
                    "🔧 **Selenium automation log available** for technical review",
                    "📸 **Screenshot captured** of final booking state",
                    "🍽️ **Enjoy your Selenium-automated dining experience!**",
                    f"⏰ **Selenium booking completed at:** {self.current_time.strftime('%H:%M:%S')} UTC on {self.current_time.strftime('%Y-%m-%d')}"
                ]
                
                for step in steps:
                    st.markdown(f"• {step}")
            
            # Celebration for successful Selenium automation
            st.balloons()
            st.success("🔧✨ **Congratulations!** Your reservation was booked automatically using Selenium-powered web automation!")
            
        except Exception as e:
            st.error(f"❌ Error completing Selenium automated booking: {str(e)}")
            logger.error(f"Error completing Selenium automated booking: {str(e)}")
    
    def process_manual_booking(self, restaurant: Dict, time_slot: Dict, message_id: int):
        """Process manual booking (fallback from Selenium automation)"""
        try:
            # Generate reservation confirmation with current timestamp
            confirmation_id = f"MANUAL_{self.current_time.strftime('%Y%m%d%H%M%S')}"
            reservation_result = {
                "success": True,
                "confirmation": confirmation_id,
                "method": "manual",
                "restaurant_phone": restaurant.get('phone'),
                "booking_timestamp": self.current_time.isoformat()
            }
            
            # Create calendar link
            calendar_result = self.create_working_calendar_link(restaurant, time_slot, confirmation_id)
            
            # Send email invitations
            email_result = asyncio.run(self.send_real_email_invitations(restaurant, time_slot, calendar_result))
            
            # Show results
            st.markdown("### ✅ Manual Booking Process Complete!")
            
            with st.expander("📋 Manual Booking Results", expanded=True):
                # Restaurant reservation
                st.markdown("**🍽️ Restaurant Reservation:**")
                if reservation_result["success"]:
                    st.success(f"✅ Reservation ID: {reservation_result['confirmation']}")
                    st.info(f"🕐 **Booking processed at:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    if reservation_result.get("method") == "manual":
                        st.warning(f"📞 **Action Required:** Please call {restaurant.get('phone', 'the restaurant')} to confirm your reservation.")
                
                # Calendar event
                st.markdown("**📅 Calendar Event:**")
                if calendar_result.get("success"):
                    st.success("✅ Universal calendar link created!")
                    
                    user_date = time_slot.get('date')
                    user_time = time_slot.get('time')
                    st.info(f"📅 **Event created for:** {user_date} at {user_time}")
                    
                    if calendar_result.get('event_link'):
                        st.markdown(f"🔗 [Add to Your Calendar]({calendar_result['event_link']})")
                    st.info("📅 Works with Google Calendar, Outlook, Apple Calendar, and more!")
                    
                    # Show availability source
                    if time_slot.get("availability_source") == "google_calendar_api":
                        st.success("📊 **Time selected based on REAL team calendar availability**")
                    else:
                        st.info("📊 **Time selected based on simulated availability**")
                else:
                    st.error(f"❌ Calendar event failed: {calendar_result.get('error', 'Unknown error')}")
                
                # Email invitations
                st.markdown("**📧 Email Invitations:**")
                if email_result.get("success"):
                    st.success(f"✅ Email invitations sent to {email_result.get('sent_count', 0)} team members!")
                    
                    if email_result.get('sent_emails'):
                        st.markdown("**📧 Invitations sent to:**")
                        for email in email_result['sent_emails']:
                            st.write(f"• ✅ {email}")
                    
                    st.info("📅 Each email includes a working 'Add to Calendar' button!")
                else:
                    st.warning(f"⚠️ Email sending failed: {email_result.get('error', 'Email not configured')}")
                    st.info("💡 Configure email settings in the sidebar to send real invitations")
            
            # Next steps with updated current time
            with st.expander("📋 Manual Booking - What's Next?", expanded=True):
                steps = [
                    f"📞 **IMPORTANT:** Call {restaurant.get('phone', 'the restaurant')} to confirm reservation",
                    f"📅 Click the calendar link to add event for {time_slot.get('date')} at {time_slot.get('time')}",
                    "📧 Team members will receive email invitations with calendar links",
                    "👥 Follow up with team for attendance confirmations",
                    "📍 Save restaurant contact information",
                    "🍽️ Prepare for your team dinner!",
                    "📸 Don't forget to take photos and share the experience!",
                    f"⏰ **Reminder:** Manual booking processed at {self.current_time.strftime('%H:%M:%S')} UTC on {self.current_time.strftime('%Y-%m-%d')}"
                ]
                
                for step in steps:
                    st.markdown(f"• {step}")
            
            # Success celebration
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Manual booking error: {str(e)}")
            logger.error(f"Error processing manual booking: {str(e)}")
    
    def create_working_calendar_link(self, restaurant: Dict, time_slot: Dict, confirmation_id: str) -> Dict:
        """Create WORKING universal calendar link with CORRECT date and time"""
        try:
            import urllib.parse
            
            # Event details
            title = f"Team Dinner at {restaurant.get('name', 'Restaurant')}"
            location = restaurant.get('address', 'Restaurant Location')
            
            description = f"""Team Dinner - {confirmation_id}

Restaurant: {restaurant.get('name', 'Unknown')}
Phone: {restaurant.get('phone', 'N/A')}
Rating: {restaurant.get('rating', 'N/A')} stars
Address: {location}

Organized by: {self.current_user}
Reservation ID: {confirmation_id}
Booking Time: {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

Please bring ID for reservation."""
            
            # Parse date and time correctly from user selection
            event_date_str = time_slot.get('date', '2025-07-21')
            event_time_str = time_slot.get('time', '19:30')
            
            try:
                # Parse the date
                if isinstance(event_date_str, str):
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                else:
                    event_date = event_date_str
                
                # Parse time
                if ':' in event_time_str:
                    time_parts = event_time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                else:
                    hour = int(event_time_str)
                    minute = 0
                
                # Create start datetime (LOCAL TIME)
                start_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=hour, minute=minute))
                end_datetime = start_datetime + timedelta(hours=2)
                
            except Exception as e:
                logger.error(f"Date parsing error: {str(e)}")
                # Fallback to tomorrow at user's time
                start_datetime = datetime(2025, 7, 21, 19, 30)
                end_datetime = start_datetime + timedelta(hours=2)
            
            # Format for Google Calendar (LOCAL TIME - NO Z suffix)
            start_formatted = start_datetime.strftime("%Y%m%dT%H%M%S")
            end_formatted = end_datetime.strftime("%Y%m%dT%H%M%S")
            
            # Create Google Calendar universal link
            calendar_params = {
                'action': 'TEMPLATE',
                'text': title,
                'dates': f"{start_formatted}/{end_formatted}",
                'details': description[:400],
                'location': location[:100],
                'sf': 'true',
                'output': 'xml'
            }
            
            # Build URL with proper encoding
            base_url = "https://calendar.google.com/calendar/render"
            encoded_params = []
            
            for key, value in calendar_params.items():
                encoded_value = urllib.parse.quote(str(value), safe='')
                encoded_params.append(f"{key}={encoded_value}")
            
            calendar_link = f"{base_url}?{'&'.join(encoded_params)}"
            
            return {
                "success": True,
                "source": "universal_calendar_link",
                "event_id": f"universal_{confirmation_id}",
                "event_link": calendar_link,
                "message": f"Calendar event for {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%H:%M')}",
                "start_time": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "creation_time": self.current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Calendar link creation error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_real_email_invitations(self, restaurant: Dict, time_slot: Dict, calendar_result: Dict) -> Dict:
        """Send real email invitations with WORKING calendar links"""
        try:
            if not st.session_state.get('email_configured'):
                return {
                    "success": False,
                    "error": "Email not configured - configure SMTP settings in sidebar"
                }
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Get email configuration
            smtp_server = st.session_state.get('smtp_server')
            smtp_port = st.session_state.get('smtp_port')
            sender_email = st.session_state.get('email_address')
            sender_password = st.session_state.get('email_password')
            
            # Get recipient emails
            recipient_emails = time_slot.get('attendee_emails', st.session_state.get('team_emails', []))
            
            if not recipient_emails:
                return {
                    "success": False,
                    "error": "No team emails configured"
                }
            
            # Prepare email content
            subject = f"Team Dinner Invitation - {restaurant.get('name', 'Restaurant')}"
            calendar_link = calendar_result.get('event_link', 'https://calendar.google.com')
            
            # Enhanced email content with Selenium automation info
            automation_text = ""
            if time_slot.get('booking_method') == 'selenium_automated_booking':
                automation_text = """
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #4caf50;">
                    <h4 style="color: #2e7d32; margin-top: 0;">🔧 Selenium Automated Booking</h4>
                    <p style="color: #2e7d32; margin-bottom: 0;">This reservation was booked automatically using Selenium-powered web automation!</p>
                </div>
                """
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #667eea;">🍽️ Team Dinner Invitation</h2>
                    
                    <p>Hi there!</p>
                    
                    <p>You're invited to our team dinner! Here are the details:</p>
                    
                    {automation_text}
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #2d3748; margin-top: 0;">📋 Event Details</h3>
                        <p><strong>🍽️ Restaurant:</strong> {restaurant.get('name', 'Unknown')}</p>
                        <p><strong>📅 Date:</strong> {time_slot.get('date', 'N/A')}</p>
                        <p><strong>🕐 Time:</strong> {time_slot.get('time', 'N/A')}</p>
                        <p><strong>📍 Address:</strong> {restaurant.get('address', 'N/A')}</p>
                        {f"<p><strong>📞 Phone:</strong> {restaurant['phone']}</p>" if restaurant.get('phone') else ""}
                        <p><strong>⭐ Rating:</strong> {restaurant.get('rating', 'N/A')} ({restaurant.get('user_ratings_total', 0)} reviews)</p>
                        <p><strong>👥 Party Size:</strong> {time_slot.get('total_attendees', 'N/A')} people</p>
                        <p><strong>🕐 Invitation sent:</strong> {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{calendar_link}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  padding: 15px 30px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: 600;
                                  display: inline-block;
                                  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);">
                            📅 Add to Calendar
                        </a>
                    </div>
                    
                    <p><strong>Please confirm your attendance by replying to this email.</strong></p>
                    
                    <p>Looking forward to seeing everyone there!</p>
                    
                    <p>Best regards,<br>
                    {self.current_user}<br>
                    <em>Organized by ProActive Assistant with Selenium Automation</em></p>
                    
                    <hr style="border: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        This invitation was sent via ProActive Work-Life Assistant<br>
                        Sent on: {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                        Calendar integration: {calendar_result.get('source', 'universal')}<br>
                        Booking method: {time_slot.get('booking_method', 'manual')}
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send emails
            sent_emails = []
            failed_emails = []
            
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                
                for recipient_email in recipient_emails:
                    try:
                        msg = MIMEMultipart('alternative')
                        msg['From'] = sender_email
                        msg['To'] = recipient_email
                        msg['Subject'] = subject
                        
                        html_part = MIMEText(html_content, 'html')
                        msg.attach(html_part)
                        
                        server.send_message(msg)
                        sent_emails.append(recipient_email)
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
                        failed_emails.append(recipient_email)
                
                server.quit()
                
                return {
                    "success": True,
                    "sent_count": len(sent_emails),
                    "sent_emails": sent_emails,
                    "failed_emails": failed_emails,
                    "calendar_link": calendar_link,
                    "send_time": self.current_time.isoformat(),
                    "message": f"Successfully sent {len(sent_emails)} invitations"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Email server error: {str(e)}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def show_details(self, restaurant: Dict):
        """Show detailed restaurant information with Selenium automation status"""
        with st.expander(f"📋 Details: {restaurant.get('name', 'Unknown')}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🍽️ Basic Information:**")
                st.write(f"**Name:** {restaurant.get('name', 'N/A')}")
                st.write(f"**Rating:** {restaurant.get('rating', 'N/A')} ⭐ ({restaurant.get('user_ratings_total', 0)} reviews)")
                st.write(f"**Price Range:** {restaurant.get('price_range', 'N/A')}")
                st.write(f"**Cuisine:** {', '.join(restaurant.get('cuisine', ['N/A']))}")
                st.write(f"**Status:** {restaurant.get('business_status', 'N/A')}")
                
                # Opening hours if available
                if restaurant.get('opening_hours'):
                    st.markdown("**🕐 Opening Hours:**")
                    hours_list = restaurant.get('opening_hours', [])
                    for hours in hours_list[:3]:
                        st.write(f"• {hours}")
                    if len(hours_list) > 3:
                        st.write("• ...")
            
            with col2:
                st.markdown("**📍 Contact & Location:**")
                st.write(f"**Address:** {restaurant.get('address', 'N/A')}")
                if restaurant.get('phone'):
                    st.write(f"**Phone:** {restaurant['phone']}")
                if restaurant.get('website') and restaurant.get('website') != 'Not available':
                    if restaurant['website'].startswith('http'):
                        st.write(f"**Website:** [Visit Website]({restaurant['website']})")
                    else:
                        st.write(f"**Website:** {restaurant['website']}")
                
                # Selenium automation compatibility
                st.markdown("**🔧 Selenium Automation Compatibility:**")
                if st.session_state.get('web_automation_verified') and restaurant.get('website') and restaurant.get('website').startswith('http'):
                    st.success("✅ **Selenium auto-booking supported** - AI can attempt reservation using Selenium WebDriver")
                elif restaurant.get('website'):
                    st.warning("🟡 **Website available** - Manual booking recommended")
                else:
                    st.info("📞 **Phone booking only** - No website available")
                
                # Location coordinates
                location = restaurant.get('location', {})
                if location.get('lat') and location.get('lng'):
                    st.write(f"**Coordinates:** {location['lat']}, {location['lng']}")
            
            # Enhanced Reviews section with ALL reviews
            st.markdown("---")
            st.markdown("### 📝 Complete Customer Reviews")
            
            reviews = self.get_restaurant_reviews(restaurant)
            
            if reviews:
                for i, review in enumerate(reviews, 1):
                    st.markdown(f"""
                    <div class="review-item" style="margin: 1rem 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span class="review-author">👤 {review.get('author', 'Anonymous')}</span>
                            <div>
                                <span class="review-rating">{'⭐' * int(review.get('rating', 0))}</span>
                                <small style="color: #6c757d; margin-left: 0.5rem;">({review.get('rating', 0)}/5)</small>
                            </div>
                        </div>
                        <div class="review-text">"{review.get('text', 'No review text')}"</div>
                        <div class="review-time">🕐 {review.get('time', 'Recently')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📝 No reviews available for this restaurant")
            
            # Additional info section
            st.markdown("---")
            st.markdown("### 📊 Additional Information")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if restaurant.get('open_now'):
                    st.success("🟢 Currently Open")
                else:
                    st.error("🔴 Currently Closed")
            
            with col2:
                if restaurant.get('source') == 'gomaps_api':
                    st.info("✅ Real Data from GoMaps")
                else:
                    st.info("📋 Demo Data")
            
            with col3:
                total_reviews = restaurant.get('user_ratings_total', 0)
                if total_reviews > 0:
                    st.metric("Total Reviews", total_reviews)
                else:
                    st.metric("Total Reviews", "N/A")
    
    def show_map(self, restaurant: Dict):
        """Show restaurant on map"""
        location = restaurant.get("location", {})
        if location and location.get("lat") and location.get("lng"):
            try:
                import pandas as pd
                
                map_data = pd.DataFrame({
                    'lat': [float(location["lat"])],
                    'lon': [float(location["lng"])]
                })
                st.map(map_data)
                
                lat, lng = location["lat"], location["lng"]
                maps_url = f"https://www.google.com/maps?q={lat},{lng}"
                st.markdown(f"🗺️ [Open in Google Maps]({maps_url})")
            except Exception as e:
                st.error(f"Map error: {e}")
        else:
            st.error("📍 Location coordinates not available")
    
    def render_chat_interface(self):
        """Render chat interface"""
        # Display messages
        for i, message in enumerate(st.session_state.messages):
            if message["type"] == "text":
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>Assistant:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
            elif message["type"] == "options":
                self.render_options(message["content"], i)
        
        # Handle pending prompts
        if hasattr(st.session_state, 'pending_prompt'):
            prompt = st.session_state.pending_prompt
            del st.session_state.pending_prompt
            
            st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
            
            # Show user message
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong> {prompt}
            </div>
            """, unsafe_allow_html=True)
            
            with st.spinner("🤔 Processing your request..."):
                asyncio.run(self.process_request(prompt))
            st.rerun()
        
        # Chat input
        if prompt := st.chat_input("What would you like me to help you with?"):
            st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
            
            # Show user message immediately
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong> {prompt}
            </div>
            """, unsafe_allow_html=True)
            
            with st.spinner("🤔 Processing your request..."):
                asyncio.run(self.process_request(prompt))
            st.rerun()
    
    async def process_request(self, user_input: str):
        """Enhanced process request with user input tracking"""
        try:
            if not self.validate_configuration():
                return
            
            # Store user input for smart recommendations
            st.session_state['last_user_input'] = user_input
            
            result = await self.orchestrator.process_goal(user_input, st.session_state)
            
            if result["type"] == "options":
                st.session_state.message_counter = st.session_state.get('message_counter', 0) + 1
                st.session_state.messages.append({"role": "assistant", "type": "options", "content": result["content"]})
            
            elif result["type"] == "error":
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": f"❌ {result['content']}"})
            
            else:
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": str(result.get("content", "Task completed"))})
        
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            st.session_state.messages.append({"role": "assistant", "type": "text", "content": f"❌ An error occurred: {str(e)}"})
    
    def validate_configuration(self) -> bool:
        """Validate configuration"""
        if not st.session_state.get('gemini_verified'):
            st.error("❌ Please configure Gemini API key in the sidebar")
            return False
        return True
    
    def render_main_interface(self):
        """Render main interface with updated current time"""
        # Update current time to exact UTC time provided by user
        self.current_time = datetime.now(timezone.utc)+ timedelta(hours=5, minutes=30)  # Adjusted to user's timezone

        self.render_main_header()
        
        if not st.session_state.get('gemini_verified'):
            st.warning("⚠️ **Setup Required:** Configure your Gemini API key in the sidebar to get started.")
            
            with st.expander("💡 Advanced System Capabilities with Selenium Web Automation", expanded=True):
                st.markdown(f"""
                **🎯 AI-Powered Multi-Tool Coordination System with Selenium Automation**
                - **🔧 Selenium Automation:** LLM-driven Selenium WebDriver automation for restaurant bookings
                - **🌐 Enhanced Web Control:** Better browser compatibility and control than Playwright
                - **REAL Calendar Integration:** Google Calendar API for actual team availability
                - **Streamlined Smart Analysis:** Merged AI recommendations with availability data
                - **Enhanced Conflict Detection:** Improved parsing of calendar events and overlaps
                - **Restaurant Booking:** Find and book restaurants with Selenium automated form filling
                - **Universal Calendar Links:** Works with Google Calendar, Outlook, Apple Calendar
                - **Email Invitations:** Send real email invitations with working calendar links
                - **Team Coordination:** Check real team availability across multiple calendars
                - **Website Analysis:** AI analyzes restaurant websites for booking automation
                
                **🔧 Enhanced Selenium Automation Features:**
                - **Multi-Browser Support:** Chrome, Firefox, Edge with automatic driver management
                - **WebDriver Manager:** Automatic ChromeDriver installation and management
                - **Better Error Handling:** Clear installation guidance with specific error steps
                - **LLM-Guided Navigation:** AI directs browser actions step-by-step using Selenium
                - **Form Auto-Fill:** Automatically fills reservation forms using Selenium WebDriver
                - **Screenshot Capture:** Visual confirmation of booking attempts
                - **Fallback Support:** Graceful degradation to manual booking if automation fails
                - **Installation Helper:** Simple pip install commands for easy setup
                
                **📧 Gmail Users:** Use App Password (not regular password) for email functionality
                **📅 Calendar:** Real Google Calendar API integration + universal link fallback
                **🔗 Auto-Scroll:** Time selection appears prominently when you select a restaurant
                **👤 Current User:** {self.current_user}
                **🕐 System Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
                
                **🆕 Latest Selenium Features:**
                - ✅ **Selenium WebDriver Integration** - Reliable web automation with better browser support
                - ✅ **WebDriver Manager Support** - Automatic driver installation and management
                - ✅ **Multi-Browser Fallback** - Chrome → Firefox → Edge if one fails
                - ✅ **Enhanced Error Messages** - Specific guidance for Selenium installation
                - ✅ **Browser Status Display** - Detailed status for Chrome, Firefox, Edge
                - ✅ **LLM-Driven Selenium Automation** - AI guides browser to fill reservation forms
                - ✅ **Website Compatibility Analysis** - AI evaluates booking automation feasibility
                - ✅ **Visual Confirmation** - Screenshots and automation logs for verification
                - ✅ **Updated to current time:** 2025-07-20 17:39:45 UTC
                - ✅ **Production-Ready Selenium** - Robust error handling and testing
                - ✅ **Fixed Session State Management** - Proper booking flow without redirects
                
                **🚀 Quick Selenium Setup:**
                ```bash
                # Install Selenium and WebDriver Manager
                pip install selenium webdriver-manager
                ```
                
                **Why Selenium over Playwright?**
                - ✅ More mature and stable web automation framework
                - ✅ Better browser compatibility and driver management
                - ✅ Extensive community support and documentation
                - ✅ Easier installation and configuration
                - ✅ Better handling of dynamic content and JavaScript
                """)
            return
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Initialize web automation if not already done
        if not self.web_automation and st.session_state.get('gemini_verified'):
            self.initialize_web_automation()
        
        # Show examples if no messages
        if not st.session_state.messages:
            self.render_task_examples()
            st.divider()
        
        # Chat interface
        self.render_chat_interface()
    
    def run(self):
        # Update current time to exact UTC time provided by user
        self.current_time = datetime.now(timezone.utc) 

        # Load CSS and render interface
        self.load_css()
        self.render_sidebar()
        self.render_main_interface()

# Main entry point
if __name__ == "__main__":
    app = WorkLifeAssistantApp()
    app.run()