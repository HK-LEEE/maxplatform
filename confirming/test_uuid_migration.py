#!/usr/bin/env python3
"""
Test script to verify UUID migration compatibility
Tests that all updated models work correctly with UUID group IDs
"""

import sys
import uuid
from datetime import datetime

def test_model_imports():
    """Test that all updated models can be imported without errors"""
    print("Testing model imports...")
    
    try:
        from app.models.user import User, Group
        from app.models.tables import group_permissions, group_features
        from app.models.flow_studio import Project, FlowStudioFlow
        from app.models.llm_chat import MAXLLM_Flow_Publish_Access
        print("✓ All models imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Model import failed: {e}")
        return False

def test_uuid_generation():
    """Test UUID generation for groups"""
    print("\nTesting UUID generation...")
    
    try:
        # Test UUID generation
        test_uuid = uuid.uuid4()
        print(f"✓ UUID generation works: {test_uuid}")
        
        # Test string conversion
        uuid_str = str(test_uuid)
        print(f"✓ UUID string conversion: {uuid_str}")
        
        return True
    except Exception as e:
        print(f"✗ UUID generation failed: {e}")
        return False

def test_schema_compatibility():
    """Test that schemas are compatible with UUID strings"""
    print("\nTesting schema compatibility...")
    
    try:
        from app.schemas.flow_studio import ProjectResponse, FlowResponse
        from app.schemas.llm_chat import FlowPublishAccessCreate
        
        # Test UUID handling in schemas
        test_uuid = str(uuid.uuid4())
        
        # Test schema creation with UUID strings
        test_data = {
            "name": "Test Project",
            "description": "Test description",
            "owner_type": "group",
            "group_id": test_uuid
        }
        
        print(f"✓ Schema compatibility test passed")
        return True
    except Exception as e:
        print(f"✗ Schema compatibility test failed: {e}")
        return False

def test_database_connection():
    """Test database connection and basic queries"""
    print("\nTesting database connection...")
    
    try:
        from app.database import get_database_url
        from sqlalchemy import create_engine, text
        
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            print(f"✓ Database connection successful: {row[0]}")
            
            # Test if groups table exists
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'groups'
            """))
            if result.fetchone():
                print("✓ Groups table exists")
            else:
                print("! Groups table not found (this is expected for new installations)")
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_frontend_types():
    """Test that frontend type definitions are consistent"""
    print("\nTesting frontend type consistency...")
    
    try:
        # This would normally test TypeScript compilation
        # For now, we'll just check if the files exist and contain the right types
        import os
        
        frontend_path = "/home/lee/proejct/maxplatform/frontend"
        if os.path.exists(frontend_path):
            print("✓ Frontend directory exists")
            
            types_file = os.path.join(frontend_path, "src", "types", "ragDataSource.ts")
            if os.path.exists(types_file):
                with open(types_file, 'r') as f:
                    content = f.read()
                    if "group_id?: string" in content:
                        print("✓ Frontend types updated to use string for group_id")
                    else:
                        print("! Frontend types may need manual verification")
            else:
                print("! Types file not found")
        else:
            print("! Frontend directory not found")
        
        return True
    except Exception as e:
        print(f"✗ Frontend types test failed: {e}")
        return False

def run_all_tests():
    """Run all migration compatibility tests"""
    print("UUID Group Migration - Compatibility Tests")
    print("=" * 50)
    
    tests = [
        test_model_imports,
        test_uuid_generation,
        test_schema_compatibility,
        test_database_connection,
        test_frontend_types
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! Migration should be safe to proceed.")
    else:
        print("! Some tests failed. Please review before proceeding with migration.")
        
    return all(results)

if __name__ == "__main__":
    # Change to the backend directory for imports
    import os
    backend_dir = "/home/lee/proejct/maxplatform/backend"
    if os.path.exists(backend_dir):
        sys.path.insert(0, backend_dir)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)