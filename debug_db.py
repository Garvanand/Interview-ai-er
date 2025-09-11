#!/usr/bin/env python3
"""
Debug script to check database structure and data
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def debug_database():
    """Debug database structure and data"""
    print("🔍 Debugging Database...")
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    try:
        # Create client
        print(f"📡 Connecting to: {supabase_url}")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Check sessions table structure
        print("\n📊 Checking sessions table...")
        try:
            # Try to get table info
            result = supabase.table('sessions').select('*').limit(1).execute()
            print(f"✅ Sessions table accessible")
            print(f"   Columns: {list(result.data[0].keys()) if result.data else 'No data'}")
        except Exception as e:
            print(f"❌ Sessions table error: {e}")
        
        # Check if we can insert a simple record
        print("\n🔍 Testing simple insert...")
        try:
            test_data = {
                'user_id': 'debug-test-user',
                'interview_type': 'Test',
                'start_time': '2025-08-30T20:00:00Z',
                'score': 0
            }
            
            print(f"   Trying to insert: {test_data}")
            result = supabase.table('sessions').insert(test_data).execute()
            
            if result.data:
                print(f"✅ Insert successful! ID: {result.data[0].get('id')}")
                
                # Clean up - delete the test record
                test_id = result.data[0].get('id')
                delete_result = supabase.table('sessions').delete().eq('id', test_id).execute()
                print(f"✅ Test record cleaned up")
            else:
                print(f"❌ Insert failed - no data returned")
                
        except Exception as e:
            print(f"❌ Insert error: {e}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error details: {str(e)}")
        
        # Check other tables
        print("\n📊 Checking other tables...")
        tables = ['questions', 'logs', 'anomalies']
        for table in tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                print(f"✅ {table} table: Accessible")
            except Exception as e:
                print(f"❌ {table} table error: {e}")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    debug_database()
