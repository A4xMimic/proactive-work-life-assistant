import asyncio
import aiohttp
from typing import Dict, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)

class ReservationAgent:
    """Agent responsible for making restaurant reservations using web automation"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        
    def initialize_model(self, api_key: str):
        """Initialize the Gemini model for web automation guidance"""
        if not self.model:
            try:
                genai.configure(api_key=api_key)
                
                # Try models in order of preference
                model_preferences = [
                    'gemini-1.5-pro',
                    'gemini-1.5-flash', 
                    'gemini-1.0-pro'
                ]
                
                for model_name in model_preferences:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        logger.info(f"Successfully initialized reservation model: {model_name}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to initialize {model_name}: {str(e)}")
                        continue
                        
                # Fallback to any available model
                available_models = [m.name for m in genai.list_models() 
                                 if 'generateContent' in m.supported_generation_methods]
                if available_models:
                    self.model = genai.GenerativeModel(available_models[0])
                    logger.info(f"Using fallback model: {available_models[0]}")
                    return True
                    
                return False
                
            except Exception as e:
                logger.error(f"Failed to initialize reservation model: {str(e)}")
                return False
        return True
    
    async def make_reservation(self, restaurant: Dict, time_slot: Dict, 
                             party_size: int, session_state: Dict) -> Dict:
        """Attempt to make a restaurant reservation"""
        try:
            # Initialize model for web automation
            if not self.model and session_state.get('gemini_key'):
                if not self.initialize_model(session_state['gemini_key']):
                    logger.warning("Could not initialize model for web automation")
            
            # Try different reservation methods
            reservation_result = await self.attempt_web_reservation(
                restaurant, time_slot, party_size, session_state
            )
            
            if not reservation_result["success"]:
                # Fallback to phone/email recommendation
                reservation_result = self.create_manual_reservation_plan(
                    restaurant, time_slot, party_size
                )
            
            return reservation_result
            
        except Exception as e:
            logger.error(f"Error making reservation: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to make reservation: {str(e)}",
                "fallback": self.create_manual_reservation_plan(restaurant, time_slot, party_size)
            }
    
    async def attempt_web_reservation(self, restaurant: Dict, time_slot: Dict, 
                                    party_size: int, session_state: Dict) -> Dict:
        """Attempt automated web reservation using Selenium"""
        try:
            website = restaurant.get("website")
            if not website:
                return {"success": False, "message": "No website available for automation"}
            
            # Setup Chrome driver
            driver = self.setup_chrome_driver()
            
            try:
                # Navigate to restaurant website
                driver.get(website)
                
                # Use LLM to guide the reservation process if available
                if self.model:
                    automation_result = await self.llm_guided_reservation(
                        driver, restaurant, time_slot, party_size
                    )
                else:
                    automation_result = await self.rule_based_reservation(
                        driver, restaurant, time_slot, party_size
                    )
                
                return automation_result
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Web automation error: {str(e)}")
            return {"success": False, "message": f"Web automation failed: {str(e)}"}
    
    def setup_chrome_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        return driver
    
    async def llm_guided_reservation(self, driver: webdriver.Chrome, restaurant: Dict, 
                                   time_slot: Dict, party_size: int) -> Dict:
        """Use LLM to guide the reservation process"""
        try:
            # Get page content
            page_source = driver.page_source
            page_url = driver.current_url
            
            # Create prompt for LLM
            prompt = f"""
You are helping automate a restaurant reservation. Analyze this webpage and provide step-by-step instructions.

Restaurant: {restaurant['name']}
Date: {time_slot['date']}
Time: {time_slot['time']}
Party Size: {party_size}
Website: {page_url}

Current page content (first 2000 chars):
{page_source[:2000]}

Please provide specific CSS selectors or XPath expressions for:
1. Reservation/booking button or link
2. Date selection field
3. Time selection field  
4. Party size selection field
5. Submit/confirm button

Format your response as a JSON object with these fields:
{{
    "reservation_button": "CSS selector or XPath",
    "date_field": "CSS selector or XPath",
    "time_field": "CSS selector or XPath", 
    "party_size_field": "CSS selector or XPath",
    "submit_button": "CSS selector or XPath",
    "instructions": "Step by step instructions"
}}
"""
            
            response = self.model.generate_content(prompt)
            
            # Parse LLM response and execute automation
            automation_steps = self.parse_llm_automation_response(response.text)
            
            if automation_steps:
                return await self.execute_automation_steps(
                    driver, automation_steps, restaurant, time_slot, party_size
                )
            else:
                return {"success": False, "message": "Could not parse automation instructions"}
                
        except Exception as e:
            logger.error(f"LLM guided automation error: {str(e)}")
            return {"success": False, "message": f"LLM automation failed: {str(e)}"}
    
    def parse_llm_automation_response(self, response_text: str) -> Dict:
        """Parse LLM response for automation steps"""
        try:
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON block in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return None
    
    async def execute_automation_steps(self, driver: webdriver.Chrome, steps: Dict,
                                     restaurant: Dict, time_slot: Dict, party_size: int) -> Dict:
        """Execute the automation steps provided by LLM"""
        try:
            wait = WebDriverWait(driver, 10)
            
            # Step 1: Click reservation button
            if steps.get("reservation_button"):
                reservation_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, steps["reservation_button"]))
                )
                reservation_btn.click()
                await asyncio.sleep(2)
            
            # Step 2: Fill date
            if steps.get("date_field"):
                date_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, steps["date_field"]))
                )
                date_field.clear()
                date_field.send_keys(time_slot["date"])
                await asyncio.sleep(1)
            
            # Step 3: Fill time
            if steps.get("time_field"):
                time_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, steps["time_field"]))
                )
                time_field.clear()
                time_field.send_keys(time_slot["time"])
                await asyncio.sleep(1)
            
            # Step 4: Fill party size
            if steps.get("party_size_field"):
                party_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, steps["party_size_field"]))
                )
                party_field.clear()
                party_field.send_keys(str(party_size))
                await asyncio.sleep(1)
            
            # Step 5: Submit
            if steps.get("submit_button"):
                submit_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, steps["submit_button"]))
                )
                submit_btn.click()
                await asyncio.sleep(3)
            
            # Check if reservation was successful
            success_indicators = ["confirmation", "confirmed", "booked", "reserved", "success"]
            page_text = driver.page_source.lower()
            
            if any(indicator in page_text for indicator in success_indicators):
                return {
                    "success": True,
                    "confirmation": f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "message": "Reservation completed via web automation",
                    "method": "automated"
                }
            else:
                return {
                    "success": False,
                    "message": "Automation completed but confirmation unclear",
                    "method": "automated_uncertain"
                }
                
        except Exception as e:
            logger.error(f"Error executing automation steps: {str(e)}")
            return {"success": False, "message": f"Automation execution failed: {str(e)}"}
    
    async def rule_based_reservation(self, driver: webdriver.Chrome, restaurant: Dict,
                                   time_slot: Dict, party_size: int) -> Dict:
        """Fallback rule-based reservation attempt"""
        try:
            # Common reservation button texts/selectors
            reservation_selectors = [
                "a[href*='reservation']",
                "button[class*='reservation']", 
                "a[class*='book']",
                "button[class*='book']",
                ".reserve-button",
                "#reservation-button"
            ]
            
            # Try to find and click reservation button
            for selector in reservation_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed() and element.is_enabled():
                        element.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # This is a simplified version - in practice you'd have more sophisticated logic
            return {
                "success": False,
                "message": "Rule-based automation requires manual completion",
                "method": "rule_based_partial"
            }
            
        except Exception as e:
            logger.error(f"Rule-based automation error: {str(e)}")
            return {"success": False, "message": f"Rule-based automation failed: {str(e)}"}
    
    def create_manual_reservation_plan(self, restaurant: Dict, time_slot: Dict, 
                                     party_size: int) -> Dict:
        """Create a manual reservation plan when automation fails"""
        contact_info = []
        
        if restaurant.get("phone"):
            contact_info.append(f"📞 Phone: {restaurant['phone']}")
        
        if restaurant.get("website"):
            contact_info.append(f"🌐 Website: {restaurant['website']}")
        
        contact_info.append(f"📍 Address: {restaurant.get('address', 'Contact restaurant directly')}")
        
        return {
            "success": True,
            "confirmation": f"MANUAL_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message": "Manual reservation required - contact details provided",
            "method": "manual",
            "instructions": {
                "restaurant": restaurant["name"],
                "date": time_slot["date"],
                "time": time_slot["time"],
                "party_size": party_size,
                "contact_info": contact_info,
                "script": f"Hi, I'd like to make a reservation for {party_size} people on {time_slot['date']} at {time_slot['time']}. Thank you!"
            }
        }