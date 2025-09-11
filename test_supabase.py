#!/usr/bin/env python3
"""
Test script to verify Supabase connection
Run this before starting the main Flask app
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_supabase_connection():
    """Test basic Supabase connectivity"""
    print("🔍 Testing Supabase Connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        print("   Please check SUPABASE_URL and SUPABASE_KEY")
        return False
    
    try:
        # Create client
        print(f"📡 Connecting to: {supabase_url}")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test connection by querying a table
        print("🔍 Testing database access...")
        result = supabase.table('sessions').select('count', count='exact').execute()
        
        print("✅ Supabase connection successful!")
        print(f"   Database accessible: Yes")
        print(f"   Sessions table: Found")
        
        # Test table structure
        print("\n📊 Testing table structure...")
        
        # Check sessions table
        try:
            sessions_result = supabase.table('sessions').select('*').limit(1).execute()
            print("✅ Sessions table: Accessible")
        except Exception as e:
            print(f"❌ Sessions table error: {e}")
        
        # Check questions table
        try:
            questions_result = supabase.table('questions').select('*').limit(1).execute()
            print("✅ Questions table: Accessible")
        except Exception as e:
            print(f"❌ Questions table error: {e}")
        
        # Check logs table
        try:
            logs_result = supabase.table('logs').select('*').limit(1).execute()
            print("✅ Logs table: Accessible")
        except Exception as e:
            print(f"❌ Logs table error: {e}")
        
        # Check anomalies table
        try:
            anomalies_result = supabase.table('anomalies').select('*').limit(1).execute()
            print("✅ Anomalies table: Accessible")
        except Exception as e:
            print(f"❌ Anomalies table error: {e}")
        
        print("\n🎉 All tests passed! Your Supabase setup is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your SUPABASE_URL and SUPABASE_KEY in .env")
        print("   2. Verify your project is active in Supabase dashboard")
        print("   3. Ensure database schema was run successfully")
        print("   4. Check if your IP is allowed (if using restrictions)")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("\n🚀 Ready to start your Flask backend!")
        print("   Run: python app.py")
    else:
        print("\n⚠️  Please fix the connection issues before proceeding")
        exit(1)
