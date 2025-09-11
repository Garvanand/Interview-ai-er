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
        
        # Test sessions table
        print("\n📊 Testing sessions table...")
        try:
            result = supabase.table('sessions').select('*').limit(1).execute()
            print(f"✅ Sessions table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ Sessions table error: {e}")
        
        # Test questions table
        print("\n📊 Testing questions table...")
        try:
            result = supabase.table('questions').select('*').limit(1).execute()
            print(f"✅ Questions table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
            else:
                print("   No questions found (table is empty)")
        except Exception as e:
            print(f"❌ Questions table error: {e}")
        
        # Test logs table
        print("\n📊 Testing logs table...")
        try:
            result = supabase.table('logs').select('*').limit(1).execute()
            print(f"✅ Logs table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ Logs table error: {e}")
        
        # Test anomalies table
        print("\n📊 Testing anomalies table...")
        try:
            result = supabase.table('anomalies').select('*').limit(1).execute()
            print(f"✅ Anomalies table accessible")
            if result.data:
                print(f"   Columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ Anomalies table error: {e}")
        
        print("\n🎉 Database schema test complete!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    test_database_schema()
