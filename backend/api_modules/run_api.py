"""
ARGO API Runner - Modular Version
Simple script to run the refactored ARGO API
"""
import uvicorn

if __name__ == "__main__":
    print("🌊 Starting ARGO Oceanographic RAG API (Modular Version)...")
    uvicorn.run(
        "api:app",  # Use import string instead of importing app directly
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )