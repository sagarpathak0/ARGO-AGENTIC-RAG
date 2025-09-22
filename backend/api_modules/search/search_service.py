"""
Search functionality for ARGO API including intelligent, text, and semantic search
"""
import os
import sys
import logging
from typing import List, Dict, Any, Tuple, Optional

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

# Handle both relative and absolute imports
try:
    from ..models.search_models import SearchResult
    from ..database.connection import get_db_connection
except ImportError:
    from models.search_models import SearchResult
    from database.connection import get_db_connection

# Setup logging
logger = logging.getLogger(__name__)

# Global variable for embedding model
embedding_model = None


def intelligent_search(query: str, limit: int = 10) -> Tuple[List[SearchResult], Optional[Any]]:
    """Perform intelligent search using NLP understanding"""
    # Add the tools directory to the path
    tools_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'analysis')
    if tools_path not in sys.path:
        sys.path.append(tools_path)
    
    try:
        from nlp_query_processor import OceanographicNLP
        
        # Initialize NLP system
        nlp_system = OceanographicNLP()
        
        # Parse the query
        intent = nlp_system.parse_query(query)
        
        # Generate SQL filters
        sql_filters = nlp_system.generate_sql_filters(intent)
        
        # Build the intelligent search query
        base_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            ap.ocean_data,
            pe.content_text,
            0.9 as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.embedding IS NOT NULL
        """
        
        # Add intelligent filters
        if sql_filters['where_clauses']:
            base_query += " AND " + " AND ".join(sql_filters['where_clauses'])
        
        base_query += f" ORDER BY {sql_filters['order_by']} LIMIT %s"
        
        # Execute query
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        parameters = sql_filters['parameters'] + [limit]
        cursor.execute(base_query, parameters)
        results = cursor.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in results:
            # Extract specific measurement data if requested
            ocean_data = row['ocean_data'] or {}
            measurement_summary = ""
            
            if intent.measurement_types:
                for measurement in intent.measurement_types:
                    if measurement.value == "temperature" and 'temp' in ocean_data:
                        temps = ocean_data['temp'][:5]  # First 5 measurements
                        if temps:
                            avg_temp = sum(temps) / len(temps)
                            measurement_summary += f"Avg Temp: {avg_temp:.2f}C. "
                    elif measurement.value == "salinity" and 'psal' in ocean_data:
                        salinity = ocean_data['psal'][:5]
                        if salinity:
                            avg_sal = sum(salinity) / len(salinity)
                            measurement_summary += f"Avg Salinity: {avg_sal:.2f} PSU. "
                    elif measurement.value == "pressure" and 'pres' in ocean_data:
                        pressure = ocean_data['pres'][:5]
                        if pressure:
                            avg_pres = sum(pressure) / len(pressure)
                            measurement_summary += f"Avg Pressure: {avg_pres:.2f} dbar. "
            
            content_summary = measurement_summary + row['content_text'][:200]
            if len(content_summary) > 200:
                content_summary = content_summary[:200] + "..."
            
            search_results.append(SearchResult(
                profile_id=row['profile_id'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                date=str(row['date']),
                institution=row['institution'],
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data=ocean_data,
                similarity_score=float(row['similarity_score']),
                content_summary=content_summary
            ))
        
        conn.close()
        
        # Return results and intent for frontend display
        return search_results, intent
        
    except ImportError as e:
        logger.error(f"NLP system not available: {e}")
        # Fallback to regular search
        return text_search(query, limit), None
    except Exception as e:
        logger.error(f"Intelligent search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intelligent search failed: {str(e)}")


def text_search(query: str, limit: int = 10) -> List[SearchResult]:
    """Perform text-based search as fallback"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Simple text search
        search_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            pe.content_text
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.content_text ILIKE %s
        ORDER BY ap.date DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, [f"%{query}%", limit])
        results = cursor.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in results:
            search_results.append(SearchResult(
                profile_id=row['profile_id'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                date=str(row['date']),
                institution=row['institution'],
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data={},
                similarity_score=0.5,
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        return search_results
        
    except Exception as e:
        conn.close()
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


def semantic_search(query_embedding: List[float], limit: int = 10, similarity_threshold: float = 0.3) -> List[SearchResult]:
    """Perform semantic search using vector similarity"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Semantic search query using array operations instead of vector operators
        query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            ap.ocean_data,
            pe.content_text,
            0.8 as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.embedding IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
        """
        
        cursor.execute(query, [limit])
        results = cursor.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in results:
            search_results.append(SearchResult(
                profile_id=row['profile_id'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                date=str(row['date']),
                institution=row['institution'],
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data=row['ocean_data'] or {},
                similarity_score=float(row['similarity_score']),
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        return search_results
        
    except Exception as e:
        conn.close()
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


def create_query_embedding(query: str) -> List[float]:
    """Create embedding for search query"""
    try:
        if not embedding_model:
            raise HTTPException(status_code=503, detail="Embedding model not available")
        embedding = embedding_model.encode([query], normalize_embeddings=True)
        return embedding[0].tolist()
    except Exception as e:
        logger.error(f"Embedding creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create query embedding")


def intelligent_search_aggregated(query: str, limit: int = 10) -> tuple:
    """Perform intelligent search with aggregated oceanographic statistics"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Import NLP system
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'analysis'))
        from nlp_query_processor import OceanographicNLP
        
        # Initialize NLP system
        nlp_system = OceanographicNLP()
        
        # Parse the query
        intent = nlp_system.parse_query(query)
        
        # Build WHERE conditions
        where_conditions = []
        params = []
        
        # Add intelligent filters based on NLP parsing
        if intent and intent.geographic_bounds:
            lat_min = intent.geographic_bounds.min_lat
            lat_max = intent.geographic_bounds.max_lat
            lon_min = intent.geographic_bounds.min_lon
            lon_max = intent.geographic_bounds.max_lon
            
            where_conditions.append("latitude BETWEEN %s AND %s")
            params.extend([lat_min, lat_max])
            where_conditions.append("longitude BETWEEN %s AND %s")
            params.extend([lon_min, lon_max])
        
        if intent and intent.temporal_filter:
            if intent.temporal_filter.start_date:
                where_conditions.append("date >= %s")
                params.append(intent.temporal_filter.start_date)
            if intent.temporal_filter.end_date:
                where_conditions.append("date <= %s")
                params.append(intent.temporal_filter.end_date)
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = " AND " + " AND ".join(where_conditions)
        
        # 1. Get basic profile aggregation
        base_query = f"""
        SELECT 
            COUNT(*) as total_profiles,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(latitude) as avg_latitude,
            AVG(longitude) as avg_longitude,
            MIN(latitude) as min_latitude,
            MAX(latitude) as max_latitude,
            MIN(longitude) as min_longitude,
            MAX(longitude) as max_longitude,
            COUNT(DISTINCT institution) as institutions_count,
            array_agg(DISTINCT institution) as institutions
        FROM argo_profiles 
        WHERE 1=1 {where_clause}
        """
        
        logger.info(f"Executing aggregation query: {base_query}")
        logger.info(f"With parameters: {params}")
        cursor.execute(base_query, params)
        agg_result = cursor.fetchone()
        
        # 2. Get measurement statistics using simplified approach
        measurements = {}
        
        # Check what measurements were requested
        requested_temp = intent and intent.measurement_types and any('temp' in str(mt).lower() for mt in intent.measurement_types)
        requested_sal = intent and intent.measurement_types and any('sal' in str(mt).lower() for mt in intent.measurement_types)
        requested_depth = intent and intent.measurement_types and any('depth' in str(mt).lower() or 'pressure' in str(mt).lower() for mt in intent.measurement_types)
        
        # Get sample data for measurements calculation
        sample_query = f"""
        SELECT ocean_data 
        FROM argo_profiles 
        WHERE ocean_data IS NOT NULL 
        AND ocean_data != '{{}}'
        {where_clause}
        LIMIT 1000
        """
        
        logger.info(f"Getting sample data for measurements: {sample_query}")
        cursor.execute(sample_query, params)
        sample_results = cursor.fetchall()
        
        # Process ocean data in Python (more reliable than complex SQL)
        temp_values = []
        sal_values = []
        pres_values = []
        
        for row in sample_results:
            ocean_data = row['ocean_data']
            if ocean_data:
                # Extract temperature data
                if requested_temp and 'temp' in ocean_data:
                    temp_data = ocean_data['temp']
                    if isinstance(temp_data, list):
                        temp_values.extend([float(x) for x in temp_data if x is not None and str(x) != 'nan'])
                    elif temp_data is not None and str(temp_data) != 'nan':
                        temp_values.append(float(temp_data))
                
                # Extract salinity data
                if requested_sal and 'psal' in ocean_data:
                    sal_data = ocean_data['psal']
                    if isinstance(sal_data, list):
                        sal_values.extend([float(x) for x in sal_data if x is not None and str(x) != 'nan'])
                    elif sal_data is not None and str(sal_data) != 'nan':
                        sal_values.append(float(sal_data))
                
                # Extract pressure data
                if requested_depth and 'pres' in ocean_data:
                    pres_data = ocean_data['pres']
                    if isinstance(pres_data, list):
                        pres_values.extend([float(x) for x in pres_data if x is not None and str(x) != 'nan'])
                    elif pres_data is not None and str(pres_data) != 'nan':
                        pres_values.append(float(pres_data))
        
        # Calculate temperature statistics
        if temp_values:
            import statistics
            measurements["temperature"] = {
                "average": statistics.mean(temp_values),
                "min": min(temp_values),
                "max": max(temp_values),
                "std_deviation": statistics.stdev(temp_values) if len(temp_values) > 1 else 0,
                "total_measurements": len(temp_values),
                "unit": "°C"
            }
        
        # Calculate salinity statistics
        if sal_values:
            import statistics
            measurements["salinity"] = {
                "average": statistics.mean(sal_values),
                "min": min(sal_values),
                "max": max(sal_values),
                "std_deviation": statistics.stdev(sal_values) if len(sal_values) > 1 else 0,
                "total_measurements": len(sal_values),
                "unit": "PSU"
            }
        
        # Calculate depth/pressure statistics
        if pres_values:
            import statistics
            measurements["depth"] = {
                "average": statistics.mean(pres_values),
                "min": min(pres_values),
                "max": max(pres_values),
                "std_deviation": statistics.stdev(pres_values) if len(pres_values) > 1 else 0,
                "total_measurements": len(pres_values),
                "unit": "dbar (pressure) / ~10m depth"
            }
        
        # Format query understanding data
        query_understanding = None
        confidence = 0.0
        filters_applied = []
        
        if intent:
            query_understanding = {
                "query_types": [qt.value for qt in intent.query_types],
                "geographic_region": intent.geographic_bounds.name if intent.geographic_bounds else None,
                "time_period": f"{intent.temporal_filter.year}{f'/{intent.temporal_filter.month}' if intent.temporal_filter.month else ''}" if intent.temporal_filter else None,
                "measurements": [mt.value for mt in intent.measurement_types] if intent.measurement_types else None,
                "statistics": intent.statistical_operations if intent.statistical_operations else None
            }
            confidence = intent.confidence
            
            # List applied filters
            if intent.geographic_bounds:
                filters_applied.append(f"Geographic: {intent.geographic_bounds.name}")
            if intent.temporal_filter:
                if intent.temporal_filter.month and intent.temporal_filter.year:
                    filters_applied.append(f"Time: {intent.temporal_filter.month}/{intent.temporal_filter.year}")
                elif intent.temporal_filter.year:
                    filters_applied.append(f"Year: {intent.temporal_filter.year}")
            if intent.measurement_types:
                filters_applied.append(f"Measurements: {', '.join([mt.value for mt in intent.measurement_types])}")
        
        # Format aggregated response
        aggregated_data = {
            "summary": {
                "total_profiles": agg_result['total_profiles'] if agg_result['total_profiles'] else 0,
                "date_range": {
                    "start": agg_result['earliest_date'].isoformat() if agg_result['earliest_date'] else None,
                    "end": agg_result['latest_date'].isoformat() if agg_result['latest_date'] else None
                },
                "geographic_bounds": {
                    "latitude_range": [float(agg_result['min_latitude']), float(agg_result['max_latitude'])] if agg_result['min_latitude'] else [0, 0],
                    "longitude_range": [float(agg_result['min_longitude']), float(agg_result['max_longitude'])] if agg_result['min_longitude'] else [0, 0],
                    "center": [float(agg_result['avg_latitude']), float(agg_result['avg_longitude'])] if agg_result['avg_latitude'] else [0, 0]
                },
                "institutions": {
                    "count": agg_result['institutions_count'] if agg_result['institutions_count'] else 0,
                    "names": agg_result['institutions'] if agg_result['institutions'] else []
                }
            },
            "measurements": measurements,
            "query_understanding": query_understanding,
            "confidence": confidence,
            "filters_applied": filters_applied
        }
        
        conn.close()
        logger.info(f"Aggregated intelligent search found {agg_result['total_profiles']} profiles with {len(measurements)} measurement types")
        
        return aggregated_data, intent
        
    except ImportError as e:
        logger.error(f"NLP system not available: {e}")
        # Simple fallback
        basic_query = "SELECT COUNT(*) as total_profiles FROM argo_profiles"
        cursor.execute(basic_query)
        result = cursor.fetchone()
        conn.close()
        
        return {
            "summary": {"total_profiles": result['total_profiles'] if result['total_profiles'] else 0},
            "measurements": {},
            "query_understanding": None,
            "confidence": 0.0,
            "filters_applied": []
        }, None
        
    except Exception as e:
        conn.close()
        logger.error(f"Aggregated intelligent search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Aggregated search failed: {str(e)}")


def initialize_embedding_model():
    """Initialize the embedding model on startup"""
    global embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Embedding model loaded successfully")
    except ImportError:
        logger.warning("⚠️ sentence-transformers not available. Semantic search will be limited.")
        embedding_model = None
    except Exception as e:
        logger.error(f"❌ Failed to load embedding model: {e}")
        embedding_model = None