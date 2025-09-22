#!/usr/bin/env python3
"""
NLP Query Understanding System for ARGO Oceanographic Data
Intelligent parsing of natural language queries for oceanographic data retrieval
"""

import re
import spacy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import dateparser

# Load spaCy model (install with: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

class QueryType(Enum):
    """Types of oceanographic queries"""
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    MEASUREMENT = "measurement"
    STATISTICAL = "statistical"
    COMPARATIVE = "comparative"
    TREND = "trend"

class MeasurementType(Enum):
    """Types of oceanographic measurements"""
    TEMPERATURE = "temperature"
    SALINITY = "salinity"
    PRESSURE = "pressure"
    DEPTH = "depth"
    DENSITY = "density"

@dataclass
class GeographicBounds:
    """Geographic boundaries for ocean regions"""
    name: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    
@dataclass
class TemporalFilter:
    """Temporal filter for queries"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    month: Optional[int] = None
    year: Optional[int] = None
    season: Optional[str] = None

@dataclass
class QueryIntent:
    """Parsed query intent and parameters"""
    raw_query: str
    query_types: List[QueryType]
    geographic_bounds: Optional[GeographicBounds] = None
    temporal_filter: Optional[TemporalFilter] = None
    measurement_types: List[MeasurementType] = None
    statistical_operations: List[str] = None
    keywords: List[str] = None
    confidence: float = 0.0

class OceanographicNLP:
    """NLP system for understanding oceanographic queries"""
    
    def __init__(self):
        self.ocean_regions = self._load_ocean_regions()
        self.measurement_keywords = self._load_measurement_keywords()
        self.statistical_keywords = self._load_statistical_keywords()
        self.temporal_patterns = self._load_temporal_patterns()
    
    def _load_ocean_regions(self) -> Dict[str, GeographicBounds]:
        """Load predefined ocean region boundaries"""
        return {
            "indian ocean": GeographicBounds("Indian Ocean", -60, 30, 20, 140),
            "pacific ocean": GeographicBounds("Pacific Ocean", -60, 60, 120, -70),
            "atlantic ocean": GeographicBounds("Atlantic Ocean", -60, 80, -80, 20),
            "southern ocean": GeographicBounds("Southern Ocean", -90, -60, -180, 180),
            "arctic ocean": GeographicBounds("Arctic Ocean", 60, 90, -180, 180),
            "mediterranean sea": GeographicBounds("Mediterranean Sea", 30, 46, -6, 36),
            "red sea": GeographicBounds("Red Sea", 12, 30, 32, 43),
            "persian gulf": GeographicBounds("Persian Gulf", 24, 30, 48, 57),
            "north sea": GeographicBounds("North Sea", 51, 62, -4, 9),
            "baltic sea": GeographicBounds("Baltic Sea", 54, 66, 10, 30),
        }
    
    def _load_measurement_keywords(self) -> Dict[MeasurementType, List[str]]:
        """Load measurement type keywords"""
        return {
            MeasurementType.TEMPERATURE: [
                "temperature", "temp", "thermal", "heat", "warm", "cold", "celsius", "°c", "degrees"
            ],
            MeasurementType.SALINITY: [
                "salinity", "salt", "saline", "psu", "practical salinity", "salt content"
            ],
            MeasurementType.PRESSURE: [
                "pressure", "depth pressure", "hydrostatic", "dbar", "decibar", "bar"
            ],
            MeasurementType.DEPTH: [
                "depth", "deep", "shallow", "meters", "metres", "depth level", "bathymetry"
            ],
            MeasurementType.DENSITY: [
                "density", "water density", "sigma", "potential density"
            ]
        }
    
    def _load_statistical_keywords(self) -> List[str]:
        """Load statistical operation keywords"""
        return [
            "average", "mean", "median", "maximum", "minimum", "max", "min",
            "highest", "lowest", "range", "variance", "standard deviation",
            "distribution", "trend", "change", "increase", "decrease",
            "compare", "comparison", "difference", "correlation"
        ]
    
    def _load_temporal_patterns(self) -> List[str]:
        """Load temporal pattern regex"""
        return [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b',
            r'\b(\d{4})\b',
            r'\b(spring|summer|autumn|fall|winter)\s+(\d{4})\b',
            r'\b(\d{1,2})[\/\-](\d{4})\b',
            r'\b(last|past)\s+(\d+)\s+(years?|months?|days?)\b'
        ]
    
    def parse_query(self, query: str) -> QueryIntent:
        """Parse natural language query into structured intent"""
        query_lower = query.lower().strip()
        
        # Initialize intent
        intent = QueryIntent(
            raw_query=query,
            query_types=[],
            measurement_types=[],
            statistical_operations=[],
            keywords=[]
        )
        
        # Extract geographic information
        geographic_bounds = self._extract_geographic_bounds(query_lower)
        if geographic_bounds:
            intent.geographic_bounds = geographic_bounds
            intent.query_types.append(QueryType.GEOGRAPHIC)
        
        # Extract temporal information
        temporal_filter = self._extract_temporal_filter(query_lower)
        if temporal_filter:
            intent.temporal_filter = temporal_filter
            intent.query_types.append(QueryType.TEMPORAL)
        
        # Extract measurement types
        measurement_types = self._extract_measurement_types(query_lower)
        if measurement_types:
            intent.measurement_types = measurement_types
            intent.query_types.append(QueryType.MEASUREMENT)
        
        # Extract statistical operations
        statistical_ops = self._extract_statistical_operations(query_lower)
        if statistical_ops:
            intent.statistical_operations = statistical_ops
            intent.query_types.append(QueryType.STATISTICAL)
        
        # Extract keywords using spaCy if available
        if nlp:
            intent.keywords = self._extract_keywords_spacy(query)
        else:
            intent.keywords = self._extract_keywords_basic(query_lower)
        
        # Calculate confidence
        intent.confidence = self._calculate_confidence(intent)
        
        return intent
    
    def _extract_geographic_bounds(self, query: str) -> Optional[GeographicBounds]:
        """Extract geographic boundaries from query"""
        for region_name, bounds in self.ocean_regions.items():
            if region_name in query:
                return bounds
        
        # Look for coordinate patterns
        coord_pattern = r'(-?\d+\.?\d*)[\s]*([ns])[,\s]*(-?\d+\.?\d*)[\s]*([ew])'
        matches = re.findall(coord_pattern, query, re.IGNORECASE)
        
        if matches:
            # Create custom bounds from coordinates
            lat, lat_dir, lon, lon_dir = matches[0]
            lat_val = float(lat) * (-1 if lat_dir.lower() == 's' else 1)
            lon_val = float(lon) * (-1 if lon_dir.lower() == 'w' else 1)
            
            # Create a small region around the point
            return GeographicBounds(
                f"Custom Region ({lat_val}, {lon_val})",
                lat_val - 5, lat_val + 5,
                lon_val - 5, lon_val + 5
            )
        
        return None
    
    def _extract_temporal_filter(self, query: str) -> Optional[TemporalFilter]:
        """Extract temporal filter from query"""
        temporal_filter = TemporalFilter()
        
        # Month-Year pattern (July 2004)
        month_year_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b'
        match = re.search(month_year_pattern, query, re.IGNORECASE)
        
        if match:
            month_name, year = match.groups()
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            
            temporal_filter.month = month_map[month_name.lower()]
            temporal_filter.year = int(year)
            
            # Create date range for the entire month
            temporal_filter.start_date = datetime(int(year), temporal_filter.month, 1)
            if temporal_filter.month == 12:
                temporal_filter.end_date = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                temporal_filter.end_date = datetime(int(year), temporal_filter.month + 1, 1) - timedelta(days=1)
            
            return temporal_filter
        
        # Year only pattern
        year_pattern = r'\b(\d{4})\b'
        matches = re.findall(year_pattern, query)
        
        if matches:
            years = [int(year) for year in matches if 1950 <= int(year) <= 2030]
            if years:
                year = years[0]  # Take first valid year
                temporal_filter.year = year
                temporal_filter.start_date = datetime(year, 1, 1)
                temporal_filter.end_date = datetime(year, 12, 31)
                return temporal_filter
        
        # Try dateparser for more complex patterns
        try:
            import dateparser
            parsed_date = dateparser.parse(query)
            if parsed_date and 1950 <= parsed_date.year <= 2030:
                temporal_filter.start_date = parsed_date
                temporal_filter.end_date = parsed_date
                temporal_filter.year = parsed_date.year
                temporal_filter.month = parsed_date.month
                return temporal_filter
        except:
            pass
        
        return None
    
    def _extract_measurement_types(self, query: str) -> List[MeasurementType]:
        """Extract measurement types from query"""
        found_types = []
        
        for measurement_type, keywords in self.measurement_keywords.items():
            for keyword in keywords:
                # Use word boundaries to prevent partial matches (e.g., 'c' in 'ocean')
                import re
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query, re.IGNORECASE):
                    if measurement_type not in found_types:
                        found_types.append(measurement_type)
                    break
        
        return found_types
    
    def _extract_statistical_operations(self, query: str) -> List[str]:
        """Extract statistical operations from query"""
        found_ops = []
        
        for stat_keyword in self.statistical_keywords:
            if stat_keyword in query:
                found_ops.append(stat_keyword)
        
        return found_ops
    
    def _extract_keywords_spacy(self, query: str) -> List[str]:
        """Extract keywords using spaCy NLP"""
        doc = nlp(query)
        keywords = []
        
        for token in doc:
            if (token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and 
                not token.is_stop and 
                not token.is_punct and 
                len(token.text) > 2):
                keywords.append(token.lemma_.lower())
        
        return list(set(keywords))
    
    def _extract_keywords_basic(self, query: str) -> List[str]:
        """Basic keyword extraction without spaCy"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'what', 'was', 'were', 'is', 'are', 'what', 'how'
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return list(set(keywords))
    
    def _calculate_confidence(self, intent: QueryIntent) -> float:
        """Calculate confidence score for parsed intent"""
        confidence = 0.0
        
        # Base confidence for having any intent
        if intent.query_types:
            confidence += 0.3
        
        # Boost for specific components
        if intent.geographic_bounds:
            confidence += 0.25
        
        if intent.temporal_filter:
            confidence += 0.25
        
        if intent.measurement_types:
            confidence += 0.15
        
        if intent.statistical_operations:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def generate_sql_filters(self, intent: QueryIntent) -> Dict[str, Any]:
        """Generate SQL filters from parsed intent"""
        filters = {
            'where_clauses': [],
            'parameters': [],
            'order_by': 'ap.date DESC'
        }
        
        # Geographic filtering
        if intent.geographic_bounds:
            bounds = intent.geographic_bounds
            filters['where_clauses'].append(
                "ap.latitude BETWEEN %s AND %s AND ap.longitude BETWEEN %s AND %s"
            )
            filters['parameters'].extend([bounds.min_lat, bounds.max_lat, bounds.min_lon, bounds.max_lon])
        
        # Temporal filtering
        if intent.temporal_filter and intent.temporal_filter.start_date:
            if intent.temporal_filter.start_date == intent.temporal_filter.end_date:
                # Single date
                filters['where_clauses'].append("DATE(ap.date) = %s")
                filters['parameters'].append(intent.temporal_filter.start_date.date())
            else:
                # Date range
                filters['where_clauses'].append("ap.date BETWEEN %s AND %s")
                filters['parameters'].extend([
                    intent.temporal_filter.start_date,
                    intent.temporal_filter.end_date
                ])
        
        # Measurement type filtering (JSON field queries)
        if intent.measurement_types:
            measurement_conditions = []
            for measurement in intent.measurement_types:
                if measurement == MeasurementType.TEMPERATURE:
                    measurement_conditions.append("ap.ocean_data ? 'temp'")
                elif measurement == MeasurementType.SALINITY:
                    measurement_conditions.append("ap.ocean_data ? 'psal'")
                elif measurement == MeasurementType.PRESSURE:
                    measurement_conditions.append("ap.ocean_data ? 'pres'")
            
            if measurement_conditions:
                filters['where_clauses'].append(f"({' OR '.join(measurement_conditions)})")
        
        return filters

# Example usage and testing
if __name__ == "__main__":
    nlp_system = OceanographicNLP()
    
    # Test queries
    test_queries = [
        "hey what was the temperature of indian ocean in july 2004",
        "Show me salinity levels in the Atlantic Ocean during summer 2003",
        "What is the average temperature in Mediterranean Sea in 2005?",
        "Find pressure measurements near 45.5N, 30.2E in 2010",
        "Compare temperature trends in Pacific Ocean between 2000 and 2010"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        intent = nlp_system.parse_query(query)
        
        print(f"Query Types: {[qt.value for qt in intent.query_types]}")
        print(f"Confidence: {intent.confidence:.2f}")
        
        if intent.geographic_bounds:
            bounds = intent.geographic_bounds
            print(f"Geographic: {bounds.name} ({bounds.min_lat}-{bounds.max_lat}N, {bounds.min_lon}-{bounds.max_lon}E)")
        
        if intent.temporal_filter:
            tf = intent.temporal_filter
            if tf.start_date:
                print(f"Temporal: {tf.start_date.strftime('%Y-%m-%d')} to {tf.end_date.strftime('%Y-%m-%d')}")
            if tf.month and tf.year:
                print(f"Month/Year: {tf.month}/{tf.year}")
        
        if intent.measurement_types:
            print(f"Measurements: {[mt.value for mt in intent.measurement_types]}")
        
        if intent.statistical_operations:
            print(f"Statistics: {intent.statistical_operations}")
        
        # Generate SQL filters
        sql_filters = nlp_system.generate_sql_filters(intent)
        if sql_filters['where_clauses']:
            print(f"SQL WHERE: {' AND '.join(sql_filters['where_clauses'])}")
            print(f"Parameters: {sql_filters['parameters']}")
        
        print(f"Keywords: {intent.keywords}")
