# voice_assistant/property_kb_handler.py

import json
import logging
import re
from typing import List, Dict, Optional, Set

class PropertyKBHandler:
    def __init__(self, kb_file_path: str = "KB/uae_property_kb.json"):
        self.kb_file_path = kb_file_path
        self.properties = self._load_properties()
        # Dynamic data extraction
        self.locations = self._extract_locations()
        self.features = self._extract_features()
        self.location_keywords = self._build_location_keywords()
        self.property_keywords = self._build_property_keywords()
        
    def _load_properties(self) -> List[Dict]:
        """Load properties from the KB file"""
        try:
            with open(self.kb_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logging.error(f"Error loading property KB: {e}")
            return []
    
    def _extract_locations(self) -> Set[str]:
        """Dynamically extract all unique locations from KB data"""
        locations = set()
        for prop in self.properties:
            location = prop.get('location', '').strip()
            if location:
                locations.add(location.lower())
        return locations
    
    def _extract_features(self) -> Set[str]:
        """Dynamically extract all unique features from KB data"""
        features = set()
        for prop in self.properties:
            prop_features = prop.get('features', '')
            if prop_features:
                # Split features and clean them
                feature_list = [f.strip() for f in prop_features.split(',')]
                features.update(feature_list)
        return features
    
    def _build_location_keywords(self) -> Dict[str, List[str]]:
        """Dynamically build location keywords based on actual data"""
        location_keywords = {}
        
        for prop in self.properties:
            location = prop.get('location', '').lower()
            if not location:
                continue
                
            # Generate keywords from location name
            keywords = [location]
            
            # Split location name into words
            words = location.split()
            keywords.extend(words)
            
            # Add common abbreviations
            if 'dubai' in location:
                keywords.append('dubai')
            if 'palm' in location:
                keywords.append('palm')
            if 'jumeirah' in location:
                keywords.append('jumeirah')
            if 'hills' in location:
                keywords.append('hills')
            if 'ranches' in location:
                keywords.append('ranches')
            if 'estate' in location:
                keywords.append('estate')
            if 'jebel' in location:
                keywords.append('jebel')
            if 'ali' in location:
                keywords.append('ali')
            if 'beach' in location:
                keywords.append('beach')
            if 'marina' in location:
                keywords.append('marina')
            if 'downtown' in location:
                keywords.append('downtown')
            if 'emirates' in location:
                keywords.append('emirates')
            if 'arabian' in location:
                keywords.append('arabian')
            
            location_keywords[location] = list(set(keywords))
        
        return location_keywords
    
    def _build_property_keywords(self) -> List[str]:
        """Dynamically build property keywords from actual data"""
        keywords = set()
        
        # Add common property terms
        base_keywords = [
            'property', 'properties', 'apartment', 'apartments', 'villa', 'villas',
            'house', 'houses', 'home', 'homes', 'real estate', 'buy', 'purchase',
            'rent', 'rental', 'price', 'cost', 'location', 'area', 'bedroom',
            'bedrooms', 'furnished', 'unfurnished', 'sea view', 'beach', 'pool',
            'gym', 'garden', 'amenities'
        ]
        keywords.update(base_keywords)
        
        # Add locations
        keywords.update(self.locations)
        
        # Add features
        for feature in self.features:
            feature_lower = feature.lower()
            keywords.add(feature_lower)
            # Add individual words from features
            words = feature_lower.split()
            keywords.update(words)
        
        return list(keywords)
    
    def _extract_bhk_from_features(self, features: str) -> str:
        """Dynamically extract BHK information from features"""
        features_lower = features.lower()
        
        # Look for BR patterns
        br_pattern = r'(\d+)BR'
        br_match = re.search(br_pattern, features_lower)
        if br_match:
            number = br_match.group(1)
            return f"{number} bhk"
        
        # Look for bedroom patterns
        bedroom_pattern = r'(\d+)\s*bedroom'
        bedroom_match = re.search(bedroom_pattern, features_lower)
        if bedroom_match:
            number = bedroom_match.group(1)
            return f"{number} bhk"
        
        # Default fallback
        return "apartment"
    
    def search_properties(self, query: str) -> List[Dict]:
        """Search properties based on user query using dynamic keywords"""
        query_lower = query.lower()
        matching_properties = []
        
        # Handle "all properties" queries
        if query_lower in ['all properties', 'all property', 'all', 'everything', 'show all']:
            return self.properties
        
        # Search by location using dynamic keywords
        for property_data in self.properties:
            location = property_data.get('location', '').lower()
            
            # Check if query matches location keywords
            if location in self.location_keywords:
                keywords = self.location_keywords[location]
                if any(keyword in query_lower for keyword in keywords):
                    matching_properties.append(property_data)
            
            # Also check direct location match
            if location in query_lower:
                matching_properties.append(property_data)
        
        # Remove duplicates
        seen = set()
        unique_properties = []
        for prop in matching_properties:
            prop_key = f"{prop['location']}_{prop['price']}_{prop['features']}"
            if prop_key not in seen:
                seen.add(prop_key)
                unique_properties.append(prop)
        
        # Search by features if no location matches
        if not unique_properties:
            for property_data in self.properties:
                features = property_data.get('features', '').lower()
                if any(keyword in features for keyword in query_lower.split()):
                    unique_properties.append(property_data)
        
        # Search by price range if no other matches
        if not unique_properties:
            price_pattern = r'(\d+(?:\.\d+)?)\s*(?:million|m|k|thousand)?\s*(?:aed|dollars?|dirhams?)'
            price_matches = re.findall(price_pattern, query_lower)
            if price_matches:
                for property_data in self.properties:
                    property_price = property_data.get('price', '')
                    if any(price in property_price.lower() for price in price_matches):
                        unique_properties.append(property_data)
        
        # Search by budget range
        if not unique_properties:
            budget_pattern = r'(\d+)\s*(?:million|m|k|thousand)?\s*(?:budget|around|upto|max)'
            budget_matches = re.findall(budget_pattern, query_lower)
            if budget_matches:
                budget_limit = float(budget_matches[0])
                for property_data in self.properties:
                    property_price = property_data.get('price', '')
                    # Extract price value
                    price_match = re.search(r'(\d+\.?\d*)M', property_price)
                    if price_match:
                        property_price_value = float(price_match.group(1))
                        if property_price_value <= budget_limit:
                            unique_properties.append(property_data)
        
        return unique_properties
    
    def format_property_response(self, properties: List[Dict]) -> str:
        """Format property information into a professional, concise response"""
        if not properties:
            # Dynamic suggestion based on available locations
            location_list = ", ".join([loc.title() for loc in sorted(self.locations)])
            return f"No properties found. Try: {location_list}."
        
        if len(properties) == 1:
            prop = properties[0]
            bhk = self._extract_bhk_from_features(prop['features'])
            return f"{prop['location']} {bhk} {prop['price']}"
        else:
            # Professional format for multiple properties
            response = f"Available properties: "
            for i, prop in enumerate(properties, 1):
                bhk = self._extract_bhk_from_features(prop['features'])
                response += f"{i}. {prop['location']} {bhk} {prop['price']}. "
            return response.strip()
    
    def is_property_related_query(self, query: str) -> bool:
        """Check if the query is property-related using dynamic keywords"""
        query_lower = query.lower()
        
        # Check if query contains property-related keywords
        if any(keyword in query_lower for keyword in self.property_keywords):
            return True
        
        # Check for follow-up requests for details
        detail_keywords = ['yes', 'want', 'details', 'more', 'information', 'tell me', 'show me', 'provide']
        if any(keyword in query_lower for keyword in detail_keywords):
            return True
        
        # Check for follow-up questions about properties
        follow_up_keywords = [
            'are you the only one', 'only one', 'just that', 'only that',
            'is that all', 'that\'s it', 'nothing else', 'any others',
            'more options', 'other properties', 'different ones',
            'what else', 'anything else', 'other locations', 'other areas',
            'them', 'those', 'that', 'this', 'it'
        ]
        if any(keyword in query_lower for keyword in follow_up_keywords):
            return True
        
        return False
    
    def is_greeting_or_general_query(self, query: str) -> bool:
        """Check if the query is a greeting or general question"""
        query_lower = query.lower()
        
        # Greeting and general keywords
        general_keywords = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'what is your name', 'who are you', 'tell me about yourself',
            'what can you do', 'help', 'pricing', 'accounting', 'services',
            'thank you', 'thanks', 'bye', 'goodbye', 'see you'
        ]
        
        # Emotional and acknowledgment responses
        emotional_keywords = [
            'nice', 'good', 'great', 'excellent', 'perfect', 'awesome', 'amazing',
            'wow', 'cool', 'fantastic', 'wonderful', 'lovely', 'beautiful',
            'that\'s nice', 'that\'s good', 'that\'s great', 'sounds good',
            'okay', 'ok', 'alright', 'fine', 'sure', 'yes', 'yeah', 'yep',
            'interesting', 'impressive', 'not bad', 'pretty good'
        ]
        
        return any(keyword in query_lower for keyword in general_keywords + emotional_keywords)
    
    def get_default_response(self) -> str:
        """Get default response for non-property queries using dynamic locations"""
        location_list = ", ".join([loc.title() for loc in sorted(self.locations)])
        return f"I'm a UAE property assistant. Ask about {location_list}."
    
    def format_detailed_property_response(self, properties: List[Dict]) -> str:
        """Format detailed property information in 3-4 lines"""
        if not properties:
            # Dynamic suggestion based on available locations
            location_list = ", ".join([loc.title() for loc in sorted(self.locations)])
            return f"No properties found. Try: {location_list}."
        
        if len(properties) == 1:
            prop = properties[0]
            bhk = self._extract_bhk_from_features(prop['features'])
            
            # Format detailed response - point to point, professional
            response = f"{prop['location']} {bhk} {prop['price']}. "
            response += f"Features: {prop['features']}. "
            response += f"Status: {prop['status']}."
            
            return response
        else:
            # For multiple properties, provide a clean, professional format
            response = f"Property details: "
            
            for i, prop in enumerate(properties, 1):
                bhk = self._extract_bhk_from_features(prop['features'])
                
                # Clean, professional format - point to point
                response += f"{i}. {prop['location']} {bhk} {prop['price']} - {prop['features']}. "
            
            return response.strip() 