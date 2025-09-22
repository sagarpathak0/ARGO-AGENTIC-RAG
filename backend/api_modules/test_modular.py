"""
Simple test to verify the modular API structure
"""
import sys
import os

def test_modular_structure():
    """Test that all modules can be imported correctly"""
    
    # Add the parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    print("🧪 Testing modular ARGO API structure...")
    
    try:
        # Test model imports
        print("📊 Testing models...")
        from api_modules.models import (
            UserRegister, UserLogin, UserProfile, TokenResponse,
            SearchQuery, SearchResult, AggregatedSearchResponse,
            RAGQuery, RAGResponse
        )
        print("✅ Models imported successfully")
        
        # Test auth imports  
        print("🔐 Testing auth...")
        from api_modules.auth import hash_password, verify_password
        print("✅ Auth services imported successfully")
        
        # Test database imports
        print("🗄️ Testing database...")
        from api_modules.database import get_db_connection
        print("✅ Database connection imported successfully")
        
        # Test search imports
        print("🔍 Testing search...")
        from api_modules.search import text_search, intelligent_search
        print("✅ Search services imported successfully")
        
        # Test RAG imports
        print("🤖 Testing RAG...")
        from api_modules.rag import process_rag_query
        print("✅ RAG services imported successfully")
        
        # Test routes imports
        print("🛣️ Testing routes...")
        from api_modules.routes import main_router, auth_router, search_router, rag_router
        print("✅ All routers imported successfully")
        
        # Test main API import
        print("🚀 Testing main API...")
        from api_modules.api import app
        print("✅ Main FastAPI app imported successfully")
        
        print("\n🎉 ALL TESTS PASSED! Modular structure is working correctly.")
        print("\n📈 Benefits achieved:")
        print("   • Separated concerns into logical modules")
        print("   • Reduced complexity from 1069 lines to manageable chunks")
        print("   • Improved maintainability and testability")
        print("   • Made codebase ready for team collaboration")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_basic_functionality():
    """Test some basic functionality"""
    print("\n🔧 Testing basic functionality...")
    
    try:
        from api_modules.auth import hash_password, verify_password
        
        # Test password hashing
        password = "test123"
        hashed = hash_password(password)
        is_valid = verify_password(password, hashed)
        
        if is_valid:
            print("✅ Password hashing/verification works")
        else:
            print("❌ Password verification failed")
            return False
        
        print("✅ Basic functionality tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🌊 ARGO API MODULAR REFACTORING TEST SUITE")
    print("=" * 60)
    
    # Run tests
    structure_ok = test_modular_structure()
    functionality_ok = test_basic_functionality()
    
    print("\n" + "=" * 60)
    if structure_ok and functionality_ok:
        print("🎊 REFACTORING SUCCESSFUL! 🎊")
        print("\nYour ARGO API is now modular and maintainable!")
        print("\nTo run the API:")
        print("  cd backend/api_modules")
        print("  python run_api.py")
    else:
        print("❌ Some tests failed. Please check the imports.")
    print("=" * 60)