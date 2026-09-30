#!/usr/bin/env python3
"""
Test database schema and connection
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_database_schema():
    """Test database schema and connection"""
    print("🔍 Testing Database Schema...")
    
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
        
        # Test interview_sessions table
        print("\n📊 Testing interview_sessions table...")
        try:
            result = supabase.table('interview_sessions').select('*').limit(1).execute()
            print(f"✅ interview_sessions table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ interview_sessions table error: {e}")
        
        # Test interview_questions table
        print("\n📊 Testing interview_questions table...")
        try:
            result = supabase.table('interview_questions').select('*').limit(1).execute()
            print(f"✅ interview_questions table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
            else:
                print("   No questions found (table is empty)")
        except Exception as e:
            print(f"❌ interview_questions table error: {e}")
        
        # Test session_events table
        print("\n📊 Testing session_events table...")
        try:
            result = supabase.table('session_events').select('*').limit(1).execute()
            print(f"✅ session_events table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ session_events table error: {e}")
        
        # Test integrity_events table
        print("\n📊 Testing integrity_events table...")
        try:
            result = supabase.table('integrity_events').select('*').limit(1).execute()
            print(f"✅ integrity_events table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ integrity_events table error: {e}")
            
        # Test responses table
        print("\n📊 Testing responses table...")
        try:
            result = supabase.table('responses').select('*').limit(1).execute()
            print(f"✅ responses table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ responses table error: {e}")
        
        # Test evaluations table
        print("\n📊 Testing evaluations table...")
        try:
            result = supabase.table('evaluations').select('*').limit(1).execute()
            print(f"✅ evaluations table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ evaluations table error: {e}")
        
        print("\n🎉 Database schema test complete!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    test_database_schema()
