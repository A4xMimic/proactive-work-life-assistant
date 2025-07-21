import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RestaurantAgent:
    def __init__(self, config):
        self.config = config
        
    async def search_restaurants(self, location: str, cuisine: List[str] = None, party_size: int = 6, session_state: Dict = None) -> Dict:
        """Search for restaurants based on criteria"""
        try:
            # Check if we have GoMaps API key for real data
            if session_state and session_state.get('gomaps_verified') and session_state.get('gomaps_key'):
                return await self.search_real_restaurants(location, cuisine, party_size, session_state)
            else:
                return await self.search_mock_restaurants(location, cuisine, party_size)
                
        except Exception as e:
            logger.error(f"Restaurant search error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_real_restaurants(self, location: str, cuisine: List[str], party_size: int, session_state: Dict) -> Dict:
        """Search for real restaurants using GoMaps API with unique results"""
        try:
            import aiohttp
            
            gomaps_key = session_state.get('gomaps_key')
            
            # Prepare search query
            if cuisine and cuisine != ['indian']:
                cuisine_query = ' '.join(cuisine)
                query = f"{cuisine_query} restaurants in {location}"
            else:
                query = f"restaurants in {location}"
            
            # Search for places
            search_url = "https://maps.gomaps.pro/maps/api/place/textsearch/json"
            search_params = {
                "query": query,
                "key": gomaps_key,
                "type": "restaurant",
                "region": "in"  # India
            }
            
            restaurants = []
            seen_places = set()  # Track unique places by place_id
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=search_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK":
                            places = data.get("results", [])
                            
                            for place in places:
                                place_id = place.get("place_id")
                                
                                # Skip if we've already seen this place
                                if place_id in seen_places:
                                    continue
                                seen_places.add(place_id)
                                
                                # Skip if we have enough restaurants
                                if len(restaurants) >= 8:
                                    break
                                
                                restaurant = {
                                    "name": place.get("name", "Unknown Restaurant"),
                                    "address": place.get("formatted_address", "Address not available"),
                                    "rating": place.get("rating", 0),
                                    "user_ratings_total": place.get("user_ratings_total", 0),
                                    "price_level": place.get("price_level", 2),
                                    "place_id": place_id,
                                    "source": "gomaps_api",
                                    "location": {
                                        "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                                        "lng": place.get("geometry", {}).get("location", {}).get("lng")
                                    }
                                }
                                
                                # Add cuisine types (clean them up)
                                types = place.get("types", ["restaurant"])
                                clean_cuisine = [t.replace("_", " ").title() for t in types if t not in ["point_of_interest", "establishment"]]
                                restaurant["cuisine"] = clean_cuisine[:3] if clean_cuisine else ["Restaurant"]
                                
                                # Convert price level to range
                                price_levels = {
                                    1: "₹ (Budget)",
                                    2: "₹₹ (Moderate)", 
                                    3: "₹₹₹ (Expensive)",
                                    4: "₹₹₹₹ (Very Expensive)"
                                }
                                restaurant["price_range"] = price_levels.get(restaurant["price_level"], "₹₹ (Moderate)")
                                
                                # Check if open now
                                restaurant["open_now"] = place.get("opening_hours", {}).get("open_now", False)
                                
                                # Get photo reference if available
                                photos = place.get("photos", [])
                                if photos:
                                    restaurant["photo_reference"] = photos[0].get("photo_reference")
                                
                                # Get additional details (phone, website, reviews)
                                details = await self.get_place_details(place_id, gomaps_key)
                                if details:
                                    restaurant.update(details)
                                
                                restaurants.append(restaurant)
                        
                        else:
                            logger.warning(f"GoMaps API returned status: {data.get('status')}")
                            return await self.search_mock_restaurants(location, cuisine, party_size)
                    
                    else:
                        logger.warning(f"GoMaps API request failed: {response.status}")
                        return await self.search_mock_restaurants(location, cuisine, party_size)
            
            if restaurants:
                # Sort by rating and ensure uniqueness
                unique_restaurants = []
                seen_names = set()
                
                # Sort by rating first
                restaurants.sort(key=lambda x: x.get("rating", 0), reverse=True)
                
                for restaurant in restaurants:
                    name_key = restaurant["name"].lower().strip()
                    if name_key not in seen_names:
                        seen_names.add(name_key)
                        unique_restaurants.append(restaurant)
                
                return {
                    "success": True,
                    "restaurants": unique_restaurants,
                    "source": "gomaps_api",
                    "location": location,
                    "count": len(unique_restaurants)
                }
            else:
                return await self.search_mock_restaurants(location, cuisine, party_size)
                
        except Exception as e:
            logger.error(f"Real restaurant search error: {str(e)}")
            return await self.search_mock_restaurants(location, cuisine, party_size)
    
    async def get_place_details(self, place_id: str, api_key: str) -> Dict:
        """Get additional details for a place including reviews"""
        try:
            import aiohttp
            
            details_url = "https://maps.gomaps.pro/maps/api/place/details/json"
            details_params = {
                "place_id": place_id,
                "fields": "name,formatted_phone_number,website,business_status,reviews,opening_hours,price_level",
                "key": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(details_url, params=details_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK":
                            result = data.get("result", {})
                            
                            details = {}
                            
                            # Phone number
                            if result.get("formatted_phone_number"):
                                details["phone"] = result["formatted_phone_number"]
                            
                            # Website
                            if result.get("website"):
                                details["website"] = result["website"]
                            
                            # Business status
                            if result.get("business_status"):
                                details["business_status"] = result["business_status"]
                            
                            # Opening hours
                            opening_hours = result.get("opening_hours", {})
                            if opening_hours:
                                details["opening_hours"] = opening_hours.get("weekday_text", [])
                                details["open_now"] = opening_hours.get("open_now", False)
                            
                            # Reviews - Enhanced with proper formatting
                            reviews = result.get("reviews", [])
                            if reviews:
                                formatted_reviews = []
                                for review in reviews[:5]:  # Get top 5 reviews
                                    formatted_review = {
                                        "author": review.get("author_name", "Anonymous"),
                                        "rating": review.get("rating", 0),
                                        "text": review.get("text", "No review text"),
                                        "time": review.get("relative_time_description", "Recently"),
                                        "profile_photo": review.get("profile_photo_url", "")
                                    }
                                    
                                    # Clean up review text - limit length but don't cut off mid-sentence
                                    review_text = formatted_review["text"]
                                    if len(review_text) > 150:
                                        # Find last sentence ending before 150 chars
                                        truncate_at = 150
                                        for i in range(min(150, len(review_text)), 0, -1):
                                            if review_text[i] in '.!?':
                                                truncate_at = i + 1
                                                break
                                        formatted_review["text"] = review_text[:truncate_at].strip()
                                        if not formatted_review["text"].endswith(('.', '!', '?')):
                                            formatted_review["text"] += "..."
                                    
                                    formatted_reviews.append(formatted_review)
                                
                                details["recent_reviews"] = formatted_reviews
                                details["review_count"] = len(reviews)
                            
                            return details
            
            return {}
            
        except Exception as e:
            logger.error(f"Place details error: {str(e)}")
            return {}
    
    async def search_mock_restaurants(self, location: str, cuisine: List[str], party_size: int) -> Dict:
        """Search for mock restaurants as fallback with unique results"""
        try:
            # Enhanced mock restaurant data with reviews
            mock_restaurants = {
                "hyderabad": [
                    {
                        "name": "Naidu Gari Kunda Biryani-KPHB",
                        "address": "1st Floor, BSR Belleza, above HDFC Bank, near JNTU, KPHB Colony, Kukatpally, Hyderabad, Telangana 500085",
                        "rating": 4.5,
                        "user_ratings_total": 1250,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Biryani", "North Indian", "Hyderabadi"],
                        "phone": "040 2930 1114",
                        "website": "https://naidubiriayni.com",
                        "open_now": True,
                        "location": {"lat": 17.4875, "lng": 78.3953},
                        "recent_reviews": [
                            {
                                "author": "Priya Sharma",
                                "rating": 5,
                                "text": "Authentic Hyderabadi biryani with perfectly cooked mutton. The aroma and taste are exceptional!",
                                "time": "2 weeks ago"
                            },
                            {
                                "author": "Ravi Kumar",
                                "rating": 4,
                                "text": "Great taste and good portion sizes. Service is quick and staff is courteous.",
                                "time": "1 month ago"
                            },
                            {
                                "author": "Anjali Reddy",
                                "rating": 5,
                                "text": "Best biryani in KPHB area. Must try their chicken biryani and raita.",
                                "time": "3 weeks ago"
                            }
                        ]
                    },
                    {
                        "name": "Sarvi Restaurant",
                        "address": "Ambedkar Nagar, Masab Tank, Hyderabad, Telangana 500028",
                        "rating": 4.4,
                        "user_ratings_total": 890,
                        "price_range": "₹₹₹ (Expensive)",
                        "cuisine": ["Hyderabadi", "Biryani", "Mutton"],
                        "phone": "040 2930 1114",
                        "website": "https://sarvirestaurant.com",
                        "open_now": True,
                        "location": {"lat": 17.4065, "lng": 78.4772},
                        "recent_reviews": [
                            {
                                "author": "Ahmed Ali",
                                "rating": 5,
                                "text": "Traditional Hyderabadi flavors at their best. The mutton biryani is a must-try!",
                                "time": "1 week ago"
                            },
                            {
                                "author": "Fatima Sheikh",
                                "rating": 4,
                                "text": "Rich taste and generous portions. Slightly expensive but worth it for special occasions.",
                                "time": "2 weeks ago"
                            }
                        ]
                    },
                    {
                        "name": "Paradise Restaurant",
                        "address": "SD Road, Secunderabad, Hyderabad, Telangana 500003",
                        "rating": 4.3,
                        "user_ratings_total": 2150,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Biryani", "Indian", "Hyderabadi"],
                        "phone": "040 2784 2020",
                        "website": "https://paradisebiryani.com",
                        "open_now": True,
                        "location": {"lat": 17.4399, "lng": 78.4983},
                        "recent_reviews": [
                            {
                                "author": "Deepak Agarwal",
                                "rating": 4,
                                "text": "Consistent quality across all branches. Their chicken biryani never disappoints.",
                                "time": "5 days ago"
                            },
                            {
                                "author": "Meera Iyer",
                                "rating": 4,
                                "text": "Good food and quick service. Perfect for family dinners and group celebrations.",
                                "time": "1 week ago"
                            }
                        ]
                    },
                    {
                        "name": "Bawarchi Restaurant",
                        "address": "RTC X Roads, Hyderabad, Telangana 500020",
                        "rating": 4.2,
                        "user_ratings_total": 1680,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Biryani", "North Indian", "Tandoor"],
                        "phone": "040 2761 8593",
                        "website": "https://bawarchi.com",
                        "open_now": False,
                        "location": {"lat": 17.4239, "lng": 78.4738},
                        "recent_reviews": [
                            {
                                "author": "Suresh Reddy",
                                "rating": 4,
                                "text": "Famous for biryani but their kebabs are equally good. Try the mutton seekh kebab.",
                                "time": "3 days ago"
                            }
                        ]
                    },
                    {
                        "name": "Shah Ghouse Cafe & Restaurant",
                        "address": "Tolichowki, Hyderabad, Telangana 500008",
                        "rating": 4.1,
                        "user_ratings_total": 1320,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Hyderabadi", "Biryani", "Haleem"],
                        "phone": "040 2341 6139",
                        "open_now": True,
                        "location": {"lat": 17.3850, "lng": 78.4867},
                        "recent_reviews": [
                            {
                                "author": "Zara Khan",
                                "rating": 4,
                                "text": "Authentic taste and reasonable prices. Their haleem during Ramadan is legendary.",
                                "time": "1 week ago"
                            }
                        ]
                    }
                ],
                "mumbai": [
                    {
                        "name": "Trishna",
                        "address": "7, Sai Baba Marg, Kala Ghoda, Fort, Mumbai, Maharashtra 400001",
                        "rating": 4.6,
                        "user_ratings_total": 980,
                        "price_range": "₹₹₹₹ (Very Expensive)",
                        "cuisine": ["Seafood", "Contemporary", "Indian"],
                        "phone": "022 2270 3213",
                        "website": "https://trishnamumbai.com",
                        "open_now": True,
                        "location": {"lat": 18.9220, "lng": 72.8347},
                        "recent_reviews": [
                            {
                                "author": "Rohit Malhotra",
                                "rating": 5,
                                "text": "Exceptional seafood preparation with innovative flavors. Fine dining at its best!",
                                "time": "4 days ago"
                            },
                            {
                                "author": "Priyanka Joshi",
                                "rating": 5,
                                "text": "Amazing coastal cuisine. The koliwada prawns and black pepper soft shell crab are must-tries.",
                                "time": "1 week ago"
                            }
                        ]
                    },
                    {
                        "name": "Leopold Cafe",
                        "address": "Shahid Bhagat Singh Rd, Colaba Causeway, Colaba, Mumbai, Maharashtra 400001",
                        "rating": 4.2,
                        "user_ratings_total": 1567,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Continental", "Indian", "Chinese"],
                        "phone": "022 2202 0131",
                        "website": "https://leopoldcafe.com",
                        "open_now": True,
                        "location": {"lat": 18.9067, "lng": 72.8147},
                        "recent_reviews": [
                            {
                                "author": "Vikram Singh",
                                "rating": 4,
                                "text": "Historic cafe with great ambiance. Their breakfast menu is excellent for tourists.",
                                "time": "2 weeks ago"
                            }
                        ]
                    }
                ],
                "delhi": [
                    {
                        "name": "Indian Accent",
                        "address": "The Manor Hotel, 77, Friends Colony West, New Delhi, Delhi 110065",
                        "rating": 4.7,
                        "user_ratings_total": 1890,
                        "price_range": "₹₹₹₹ (Very Expensive)",
                        "cuisine": ["Contemporary Indian", "Fine Dining"],
                        "phone": "011 4323 5151",
                        "website": "https://indianaccent.com",
                        "open_now": True,
                        "location": {"lat": 28.5494, "lng": 77.2320},
                        "recent_reviews": [
                            {
                                "author": "Arjun Kapoor",
                                "rating": 5,
                                "text": "World-class Indian cuisine with modern presentation. Every dish is a masterpiece!",
                                "time": "1 week ago"
                            }
                        ]
                    },
                    {
                        "name": "Karim's",
                        "address": "16, Gali Kababian, Jama Masjid, New Delhi, Delhi 110006",
                        "rating": 4.1,
                        "user_ratings_total": 2340,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Mughlai", "North Indian", "Biryani"],
                        "phone": "011 2326 9880",
                        "open_now": True,
                        "location": {"lat": 28.6507, "lng": 77.2334},
                        "recent_reviews": [
                            {
                                "author": "Sameer Ahmed",
                                "rating": 4,
                                "text": "Legendary Mughlai restaurant. Their mutton korma and roomali roti are exceptional.",
                                "time": "3 days ago"
                            }
                        ]
                    }
                ],
                "bangalore": [
                    {
                        "name": "Koshy's Restaurant",
                        "address": "39, St Mark's Rd, Bengaluru, Karnataka 560001",
                        "rating": 4.3,
                        "user_ratings_total": 1456,
                        "price_range": "₹₹ (Moderate)",
                        "cuisine": ["Continental", "Indian", "South Indian"],
                        "phone": "080 2221 3793",
                        "website": "https://koshys.com",
                        "open_now": True,
                        "location": {"lat": 12.9716, "lng": 77.5946},
                        "recent_reviews": [
                            {
                                "author": "Rahul Dravid",
                                "rating": 4,
                                "text": "Classic Bangalore establishment. Their breakfast and coffee are legendary among locals.",
                                "time": "5 days ago"
                            }
                        ]
                    },
                    {
                        "name": "Vidyarthi Bhavan",
                        "address": "32, Gandhi Bazaar Main Rd, Basavanagudi, Bengaluru, Karnataka 560004",
                        "rating": 4.4,
                        "user_ratings_total": 890,
                        "price_range": "₹ (Budget)",
                        "cuisine": ["South Indian", "Breakfast", "Vegetarian"],
                        "phone": "080 2657 5897",
                        "open_now": True,
                        "location": {"lat": 12.9424, "lng": 77.5736},
                        "recent_reviews": [
                            {
                                "author": "Lakshmi Rao",
                                "rating": 5,
                                "text": "Best masala dosa in Bangalore! Crispy, perfectly spiced, and served with amazing chutneys.",
                                "time": "2 days ago"
                            }
                        ]
                    }
                ]
            }
            
            # Get restaurants for the location
            location_key = location.lower()
            restaurants = mock_restaurants.get(location_key, [])
            
            # If no specific restaurants for location, use Hyderabad as default
            if not restaurants:
                restaurants = mock_restaurants["hyderabad"].copy()
                # Update location in restaurant data
                for restaurant in restaurants:
                    restaurant["address"] = restaurant["address"].replace("Hyderabad", location.title())
            
            # Filter by cuisine if specified
            if cuisine and cuisine != ['indian']:
                filtered_restaurants = []
                for restaurant in restaurants:
                    restaurant_cuisines = [c.lower() for c in restaurant.get("cuisine", [])]
                    user_cuisines = [c.lower() for c in cuisine]
                    
                    # Check if any user cuisine matches restaurant cuisines
                    if any(uc in ' '.join(restaurant_cuisines) for uc in user_cuisines):
                        filtered_restaurants.append(restaurant)
                
                if filtered_restaurants:
                    restaurants = filtered_restaurants
            
            # Add mock data fields and ensure uniqueness
            unique_restaurants = []
            seen_names = set()
            
            for restaurant in restaurants:
                name_key = restaurant["name"].lower().strip()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    restaurant["source"] = "mock_data"
                    restaurant["business_status"] = "OPERATIONAL"
                    restaurant["place_id"] = f"mock_{name_key.replace(' ', '_')}"
                    
                    # Add some variety in opening status
                    import random
                    restaurant["open_now"] = random.choice([True, True, True, False])  # 75% chance open
                    
                    unique_restaurants.append(restaurant)
            
            return {
                "success": True,
                "restaurants": unique_restaurants,
                "source": "mock_data",
                "location": location,
                "count": len(unique_restaurants)
            }
            
        except Exception as e:
            logger.error(f"Mock restaurant search error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_restaurant_details(self, place_id: str, session_state: Dict) -> Dict:
        """Get detailed information about a specific restaurant"""
        try:
            if session_state and session_state.get('gomaps_verified'):
                return await self.get_real_restaurant_details(place_id, session_state)
            else:
                return await self.get_mock_restaurant_details(place_id)
                
        except Exception as e:
            logger.error(f"Restaurant details error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_real_restaurant_details(self, place_id: str, session_state: Dict) -> Dict:
        """Get real restaurant details using GoMaps API"""
        try:
            gomaps_key = session_state.get('gomaps_key')
            details = await self.get_place_details(place_id, gomaps_key)
            
            return {
                "success": True,
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Real restaurant details error: {str(e)}")
            return await self.get_mock_restaurant_details(place_id)
    
    async def get_mock_restaurant_details(self, place_id: str) -> Dict:
        """Get mock restaurant details with proper reviews"""
        mock_reviews = [
            {
                "author": "Food Enthusiast",
                "rating": 5,
                "text": "Absolutely amazing food and excellent service! The ambiance is perfect for team dinners and celebrations.",
                "time": "1 week ago"
            },
            {
                "author": "Local Foodie",
                "rating": 4,
                "text": "Great taste and reasonable prices. The staff is courteous and the food quality is consistent.",
                "time": "2 weeks ago"
            },
            {
                "author": "Team Dinner Expert",
                "rating": 4,
                "text": "Perfect venue for group dining. They accommodate large parties well and the food arrives quickly.",
                "time": "3 weeks ago"
            },
            {
                "author": "Regular Customer",
                "rating": 5,
                "text": "One of my favorite restaurants in the city. Fresh ingredients and authentic flavors every time.",
                "time": "1 month ago"
            }
        ]
        
        return {
            "success": True,
            "details": {
                "phone": "Available on booking",
                "website": "Contact for details", 
                "business_status": "OPERATIONAL",
                "opening_hours": [
                    "Monday: 11:00 AM – 11:00 PM",
                    "Tuesday: 11:00 AM – 11:00 PM", 
                    "Wednesday: 11:00 AM – 11:00 PM",
                    "Thursday: 11:00 AM – 11:00 PM",
                    "Friday: 11:00 AM – 11:30 PM",
                    "Saturday: 11:00 AM – 11:30 PM",
                    "Sunday: 11:00 AM – 11:00 PM"
                ],
                "recent_reviews": mock_reviews,
                "review_count": len(mock_reviews)
            }
        }
    
    async def check_availability(self, restaurant_id: str, date: str, time: str, party_size: int) -> Dict:
        """Check restaurant availability for booking"""
        try:
            # Mock availability check
            import random
            
            # Simulate availability based on time and party size
            peak_times = ["19:00", "19:30", "20:00"]
            is_peak = time in peak_times
            is_weekend = datetime.strptime(date, "%Y-%m-%d").weekday() >= 5
            
            # Calculate availability probability
            base_probability = 0.8
            if is_peak:
                base_probability -= 0.3
            if is_weekend:
                base_probability -= 0.2
            if party_size > 8:
                base_probability -= 0.2
            
            is_available = random.random() < max(0.2, base_probability)
            
            return {
                "success": True,
                "available": is_available,
                "restaurant_id": restaurant_id,
                "date": date,
                "time": time,
                "party_size": party_size,
                "message": "Available for booking" if is_available else "Not available at this time"
            }
            
        except Exception as e:
            logger.error(f"Availability check error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }