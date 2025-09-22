"""
Alternative runner for ARGO API - run from backend directory
"""
import uvicorn

if __name__ == "__main__":
    print("🌊 Starting ARGO Oceanographic RAG API (Modular Version)...")
    print("📁 Running from backend directory...")
    uvicorn.run(
        "api_modules.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )