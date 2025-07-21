import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
import json
import urllib.parse

from utils.logger import setup_logger

logger = setup_logger(__name__)

class ResearchAgent:
    """Agent responsible for researching restaurants using ONLY GoMaps API - REAL DATA ONLY"""
    
    def __init__(self, config):
        self.config = config
        self.gomaps_base_url = "https://maps.gomaps.pro/maps/api"
        
    async def find_restaurants(self, location: str, cuisine: Optional[List[str]], 
                             party_size: int, session_state: Dict) -> Dict:
        """Find restaurants using ONLY GoMaps API with proper location filtering"""
        try:
            gomaps_key = session_state.get('gomaps_key')
            
            if not gomaps_key:
                return {
                    "success": False,
                    "message": "GoMaps API key required for real restaurant data. Please add your API key in the sidebar."
                }
            
            logger.info(f"🔍 Searching for restaurants in {location}")
            
            # First try: Specific location search for Hyderabad
            restaurants = await self.search_restaurants_with_location_filter(
                location=location,
                cuisine=cuisine,
                api_key=gomaps_key
            )
            
            logger.info(f"🎯 Found {len(restaurants)} restaurants, filtering by location...")
            
            # Filter restaurants to ensure they're actually in Hyderabad
            hyderabad_restaurants = self.filter_by_hyderabad_location(restaurants)
            
            logger.info(f"📍 After location filtering: {len(hyderabad_restaurants)} Hyderabad restaurants")
            
            if not hyderabad_restaurants:
                logger.warning("🔍 No Hyderabad restaurants found, trying alternative search...")
                # Try alternative search specifically for Hyderabad
                hyderabad_restaurants = await self.search_hyderabad_specifically(api_key=gomaps_key, cuisine=cuisine)
            
            if not hyderabad_restaurants:
                return {
                    "success": False,
                    "message": f"❌ No restaurants found in Hyderabad via GoMaps API. The API may have returned restaurants from other cities."
                }
            
            # Get detailed information for restaurants
            enhanced_restaurants = await self.enhance_restaurants_with_details(
                hyderabad_restaurants[:10], gomaps_key  # Limit to 10 for performance
            )
            
            # Rank restaurants
            ranked_restaurants = self.rank_restaurants(enhanced_restaurants, cuisine, party_size)
            
            logger.info(f"✅ Returning {len(ranked_restaurants)} Hyderabad restaurants")
            
            return {
                "success": True,
                "restaurants": ranked_restaurants,
                "total_found": len(ranked_restaurants),
                "source": "gomaps_api_hyderabad_filtered"
            }
            
        except Exception as e:
            logger.error(f"❌ Error in restaurant search: {str(e)}")
            return {
                "success": False,
                "message": f"Error searching restaurants: {str(e)}"
            }
    
    async def search_restaurants_with_location_filter(self, location: str, cuisine: Optional[List[str]], 
                                                     api_key: str) -> List[Dict]:
        """Search restaurants with specific location focus"""
        try:
            # Build very specific query for Hyderabad
            if cuisine and any('biryani' in c.lower() for c in cuisine):
                queries = [
                    "biryani restaurants Hyderabad Telangana",
                    "best biryani Hyderabad India",
                    "restaurants Hyderabad Gachibowli biryani"
                ]
            else:
                queries = [
                    "restaurants Hyderabad Telangana India",
                    "best restaurants Hyderabad Gachibowli",
                    "dining Hyderabad India"
                ]
            
            all_restaurants = []
            
            for query in queries:
                logger.info(f"🌐 GoMaps query: {query}")
                
                url = f"{self.gomaps_base_url}/place/textsearch/json"
                
                params = {
                    "query": query,
                    "key": api_key,
                    "type": "restaurant",
                    "language": "en"
                }
                
                timeout = aiohttp.ClientTimeout(total=30)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("status") == "OK":
                                results = data.get("results", [])
                                logger.info(f"📊 Query '{query}' returned {len(results)} results")
                                
                                for place in results:
                                    restaurant = self.parse_gomaps_restaurant(place)
                                    # Add to list if not already present
                                    if not any(r['id'] == restaurant['id'] for r in all_restaurants):
                                        all_restaurants.append(restaurant)
                            else:
                                logger.warning(f"⚠️ Query '{query}' failed: {data.get('status')}")
                
                # Small delay between queries
                await asyncio.sleep(0.5)
            
            logger.info(f"🎉 Total unique restaurants found: {len(all_restaurants)}")
            return all_restaurants
            
        except Exception as e:
            logger.error(f"💥 Search error: {str(e)}")
            return []
    
    async def search_hyderabad_specifically(self, api_key: str, cuisine: Optional[List[str]]) -> List[Dict]:
        """Backup search specifically for Hyderabad using nearby search with coordinates"""
        try:
            # Hyderabad coordinates
            hyderabad_lat = 17.3850
            hyderabad_lng = 78.4867
            
            url = f"{self.gomaps_base_url}/place/nearbysearch/json"
            
            params = {
                "location": f"{hyderabad_lat},{hyderabad_lng}",
                "radius": "20000",  # 20km radius
                "type": "restaurant",
                "key": api_key,
                "language": "en"
            }
            
            if cuisine and any('biryani' in c.lower() for c in cuisine):
                params["keyword"] = "biryani"
            
            logger.info(f"🎯 Nearby search around Hyderabad coordinates")
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK":
                            results = data.get("results", [])
                            logger.info(f"📍 Nearby search found {len(results)} restaurants")
                            
                            restaurants = []
                            for place in results:
                                restaurant = self.parse_gomaps_restaurant(place)
                                restaurants.append(restaurant)
                            
                            return restaurants
                        else:
                            logger.warning(f"Nearby search failed: {data.get('status')}")
                            return []
                    else:
                        logger.error(f"Nearby search HTTP error: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"Nearby search error: {str(e)}")
            return []
    
    def filter_by_hyderabad_location(self, restaurants: List[Dict]) -> List[Dict]:
        """Filter restaurants to only include those actually in Hyderabad/Telangana"""
        hyderabad_restaurants = []
        
        hyderabad_indicators = [
            'hyderabad', 'telangana', 'secunderabad', 'cyberabad',
            'gachibowli', 'hitec city', 'madhapur', 'kondapur',
            'jubilee hills', 'banjara hills', 'begumpet', 'mehdipatnam',
            'tolichowki', 'ameerpet', 'kukatpally', 'miyapur'
        ]
        
        for restaurant in restaurants:
            address = restaurant.get("address", "").lower()
            
            # Check if any Hyderabad indicator is in the address
            is_hyderabad = any(indicator in address for indicator in hyderabad_indicators)
            
            # Also check coordinates if available
            location = restaurant.get("location", {})
            if location and location.get("lat") and location.get("lng"):
                lat = float(location["lat"])
                lng = float(location["lng"])
                
                # Hyderabad bounding box (approximate)
                if 17.2 <= lat <= 17.6 and 78.2 <= lng <= 78.8:
                    is_hyderabad = True
            
            if is_hyderabad:
                logger.info(f"✅ Keeping: {restaurant['name']} - {address[:50]}...")
                hyderabad_restaurants.append(restaurant)
            else:
                logger.info(f"❌ Filtering out: {restaurant['name']} - {address[:50]}... (not in Hyderabad)")
        
        return hyderabad_restaurants
    
    def parse_gomaps_restaurant(self, place_data: Dict) -> Dict:
        """Parse GoMaps place data with enhanced details"""
        try:
            place_name = place_data.get("name", "Unknown")
            place_address = place_data.get("formatted_address", "Unknown address")
            
            restaurant = {
                "id": place_data.get("place_id", f"gomaps_{hash(str(place_data))}"),
                "name": place_name,
                "address": place_address,
                "rating": place_data.get("rating", 0.0),
                "price_level": place_data.get("price_level"),
                "price_range": self.convert_price_level(place_data.get("price_level")),
                "types": place_data.get("types", []),
                "cuisine": self.extract_cuisine_from_types(place_data.get("types", [])),
                "user_ratings_total": place_data.get("user_ratings_total", 0),
                "business_status": place_data.get("business_status", "OPERATIONAL"),
                "description": f"Real restaurant from GoMaps API with {place_data.get('user_ratings_total', 0)} reviews",
                "source": "gomaps_api"
            }
            
            # Add location coordinates
            geometry = place_data.get("geometry", {})
            location = geometry.get("location", {})
            if location:
                restaurant["location"] = {
                    "lat": location.get("lat"),
                    "lng": location.get("lng")
                }
            
            # Add photos
            photos = place_data.get("photos", [])
            if photos:
                restaurant["photos"] = photos
                restaurant["photo_reference"] = photos[0].get("photo_reference")
            
            # Add opening hours
            opening_hours = place_data.get("opening_hours", {})
            if opening_hours:
                restaurant["opening_hours"] = opening_hours
                restaurant["open_now"] = opening_hours.get("open_now", False)
            
            # Add icon information
            restaurant["icon"] = place_data.get("icon")
            restaurant["icon_background_color"] = place_data.get("icon_background_color")
            
            return restaurant
            
        except Exception as e:
            logger.error(f"💥 Error parsing restaurant: {e}")
            return {
                "id": f"error_{hash(str(place_data))}",
                "name": place_data.get("name", "Parse Error"),
                "address": place_data.get("formatted_address", "Address parsing failed"),
                "rating": place_data.get("rating", 0.0),
                "price_range": "Unknown",
                "cuisine": ["Restaurant"],
                "user_ratings_total": place_data.get("user_ratings_total", 0),
                "description": "Restaurant with parsing issues",
                "source": "gomaps_api_partial"
            }
    
    async def enhance_restaurants_with_details(self, restaurants: List[Dict], api_key: str) -> List[Dict]:
        """Get detailed information using Place Details API"""
        enhanced = []
        
        logger.info(f"🔍 Enhancing {len(restaurants)} restaurants with details...")
        
        for i, restaurant in enumerate(restaurants):
            place_id = restaurant.get("id")
            if place_id and not place_id.startswith("error_"):
                logger.info(f"📋 Getting details for {restaurant['name']}...")
                details = await self.get_place_details(place_id, api_key)
                if details:
                    restaurant.update(details)
                    logger.info(f"✅ Enhanced {restaurant['name']}")
                else:
                    logger.warning(f"⚠️ No additional details for {restaurant['name']}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.3)
            
            enhanced.append(restaurant)
            
            # Progress logging
            if (i + 1) % 3 == 0:
                logger.info(f"📊 Enhanced {i + 1}/{len(restaurants)} restaurants")
        
        logger.info(f"🎉 Enhanced all {len(enhanced)} restaurants")
        return enhanced
    
    async def get_place_details(self, place_id: str, api_key: str) -> Dict:
        """Get detailed place information using GoMaps Place Details API"""
        try:
            url = f"{self.gomaps_base_url}/place/details/json"
            
            # Request comprehensive details
            fields = [
                "name", "rating", "formatted_phone_number", "formatted_address", 
                "opening_hours", "website", "photos", "reviews", "price_level",
                "types", "user_ratings_total", "geometry", "business_status",
                "vicinity", "plus_code"
            ]
            
            params = {
                "place_id": place_id,
                "key": api_key,
                "fields": ",".join(fields),
                "language": "en"
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK":
                            result = data.get("result", {})
                            
                            details = {}
                            
                            # Contact information
                            if "formatted_phone_number" in result:
                                details["phone"] = result["formatted_phone_number"]
                            if "website" in result:
                                details["website"] = result["website"]
                            
                            # Enhanced address info
                            if "vicinity" in result:
                                details["vicinity"] = result["vicinity"]
                            if "plus_code" in result:
                                details["plus_code"] = result["plus_code"]
                            
                            # Opening hours
                            if "opening_hours" in result:
                                opening_hours = result["opening_hours"]
                                details["opening_hours"] = opening_hours
                                details["open_now"] = opening_hours.get("open_now", False)
                                
                                # Extract weekday text for display
                                weekday_text = opening_hours.get("weekday_text", [])
                                if weekday_text:
                                    details["hours_display"] = weekday_text
                            
                            # Photos
                            if "photos" in result:
                                photos = result["photos"]
                                details["photos"] = photos
                                if photos:
                                    details["photo_reference"] = photos[0].get("photo_reference")
                            
                            # Reviews with proper parsing
                            if "reviews" in result:
                                reviews = result["reviews"]
                                details["reviews_data"] = reviews
                                
                                # Extract review texts
                                review_texts = []
                                for review in reviews[:5]:  # Top 5 reviews
                                    text = review.get("text", "")
                                    author = review.get("author_name", "Anonymous")
                                    rating = review.get("rating", 0)
                                    review_texts.append({
                                        "text": text[:200] + "..." if len(text) > 200 else text,
                                        "author": author,
                                        "rating": rating
                                    })
                                
                                details["recent_reviews"] = review_texts
                            
                            # Update price level
                            if "price_level" in result:
                                details["price_level"] = result["price_level"]
                                details["price_range"] = self.convert_price_level(result["price_level"])
                            
                            # Update ratings info
                            if "user_ratings_total" in result:
                                details["user_ratings_total"] = result["user_ratings_total"]
                            if "rating" in result:
                                details["rating"] = result["rating"]
                            
                            return details
                        else:
                            logger.warning(f"Place details failed for {place_id}: {data.get('status')}")
                            return {}
                    else:
                        logger.error(f"Place details HTTP {response.status} for {place_id}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error getting details for {place_id}: {str(e)}")
            return {}
    
    def convert_price_level(self, price_level: Optional[int]) -> str:
        """Convert price level to readable format"""
        if price_level is None:
            return "Price not available"
        
        price_map = {
            0: "Free",
            1: "Inexpensive ($)",
            2: "Moderate ($$)", 
            3: "Expensive ($$$)",
            4: "Very Expensive ($$$$)"
        }
        
        return price_map.get(price_level, "Price not available")
    
    def extract_cuisine_from_types(self, types: List[str]) -> List[str]:
        """Extract cuisine from GoMaps types"""
        cuisine_mapping = {
            "indian_restaurant": "Indian",
            "chinese_restaurant": "Chinese", 
            "italian_restaurant": "Italian",
            "mexican_restaurant": "Mexican",
            "thai_restaurant": "Thai",
            "mediterranean_restaurant": "Mediterranean",
            "japanese_restaurant": "Japanese",
            "korean_restaurant": "Korean",
            "fast_food_restaurant": "Fast Food",
            "fine_dining_restaurant": "Fine Dining",
            "restaurant": "Restaurant"
        }
        
        cuisines = []
        types_str = " ".join(types).lower()
        
        # Check mappings
        for place_type in types:
            if place_type in cuisine_mapping:
                cuisines.append(cuisine_mapping[place_type])
        
        # Check keywords
        if "indian" in types_str:
            cuisines.append("Indian")
        if "chinese" in types_str:
            cuisines.append("Chinese")
        if "biryani" in types_str:
            cuisines.append("Biryani")
        if "fast" in types_str and "food" in types_str:
            cuisines.append("Fast Food")
        
        if not cuisines:
            cuisines = ["Restaurant"]
        
        return list(set(cuisines))
    
    def rank_restaurants(self, restaurants: List[Dict], preferred_cuisine: Optional[List[str]], 
                        party_size: int) -> List[Dict]:
        """Rank restaurants ensuring variety"""
        
        def calculate_score(restaurant: Dict) -> float:
            score = 0.0
            
            # Rating weight (40%)
            rating = restaurant.get("rating", 0)
            if rating > 0:
                score += (rating / 5.0) * 0.4
            
            # Cuisine match (25%)
            if preferred_cuisine:
                restaurant_cuisines = [c.lower() for c in restaurant.get("cuisine", [])]
                matches = 0
                for preferred in preferred_cuisine:
                    preferred_lower = preferred.lower()
                    if preferred_lower in restaurant_cuisines:
                        matches += 1
                    elif 'biryani' in preferred_lower and 'indian' in restaurant_cuisines:
                        matches += 1
                
                if matches > 0:
                    score += min(0.25, matches * 0.1)
            
            # Review count (20%)
            review_count = restaurant.get("user_ratings_total", 0)
            if review_count > 1000:
                score += 0.20
            elif review_count > 500:
                score += 0.15
            elif review_count > 100:
                score += 0.10
            elif review_count > 50:
                score += 0.05
            
            # Business status (10%)
            if restaurant.get("business_status") == "OPERATIONAL":
                score += 0.10
            
            # Open now (5%)
            if restaurant.get("open_now") is True:
                score += 0.05
            
            return score
        
        # Score all restaurants
        for restaurant in restaurants:
            restaurant["score"] = calculate_score(restaurant)
        
        # Sort by score descending
        ranked = sorted(restaurants, key=lambda x: x["score"], reverse=True)
        
        # Ensure variety by removing duplicates with same name
        unique_restaurants = []
        seen_names = set()
        
        for restaurant in ranked:
            name = restaurant["name"].lower()
            if name not in seen_names:
                unique_restaurants.append(restaurant)
                seen_names.add(name)
        
        # Log ranking
        logger.info("🏆 Top restaurants (unique):")
        for i, restaurant in enumerate(unique_restaurants[:5]):
            logger.info(f"{i+1}. {restaurant['name']} - Score: {restaurant['score']:.3f} - {restaurant['address'][:30]}...")
        
        return unique_restaurants