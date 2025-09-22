"""
ARGO-AGENTIC-RAG: Simple API Entry Point

This is a minimal FastAPI entry point for basic health checks and testing.
The main ARGO oceanographic data processing with agentic RAG capabilities 
is implemented in argo_api.py, which includes:

- 🧠 Intelligent NLP query processing for oceanographic data
- 🔍 Semantic search across ARGO float profiles 
- 📊 Geographic and temporal filtering (as seen in your search interface)
- 🌊 Ocean temperature, depth, and measurement analysis
- 🔐 Authentication and user management
- 📈 Real-time oceanographic statistics and data visualization

This main.py serves as a lightweight development server for basic API testing,
while argo_api.py contains the full production-ready ARGO RAG system.

Usage:
- Development testing: python main.py
- Production deployment: Use argo_api.py with proper configuration
"""

from fastapi import FastAPI
import uvicorn

# Simple FastAPI instance for basic health checks and development testing
# Note: Full ARGO RAG functionality is in argo_api.py
app = FastAPI(
    title="ARGO-RAG Simple Entry Point",
    description="Basic health check endpoint - see argo_api.py for full functionality"
)

@app.get('/')
def root():
    """
    Basic health check endpoint
    
    Returns API status for simple connectivity testing.
    For full ARGO oceanographic data search capabilities with NLP query processing,
    geographic filtering, and measurement analysis, use the endpoints in argo_api.py
    
    Returns:
        dict: Simple status message confirming API is running
    """
    return {'status': 'ARGO API Ready'}

@app.get('/info')
def api_info():
    """
    API information endpoint
    
    Provides guidance on accessing the full ARGO RAG functionality
    
    Returns:
        dict: Information about available ARGO services
    """
    return {
        'message': 'This is a simple entry point for ARGO-AGENTIC-RAG',
        'full_api': 'Use argo_api.py for complete oceanographic data processing',
        'features': [
            'Intelligent NLP query processing',
            'Semantic search across ARGO profiles', 
            'Geographic and temporal filtering',
            'Ocean measurement statistics',
            'Authentication system'
        ]
    }

# Development server configuration
if __name__ == '__main__':
    """
    Run simple development server
    
    For production deployment with full ARGO RAG capabilities,
    use argo_api.py instead of this basic server.
    
    Configuration:
    - host='0.0.0.0': Accept connections from any IP
    - port=8000: Standard development port
    """
    print("🌊 Starting simple ARGO API development server...")
    print("💡 For full oceanographic RAG functionality, use argo_api.py")
    uvicorn.run(app, host='0.0.0.0', port=8000)
