#!/usr/bin/env python3
import os
import traceback
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv

load_dotenv()

def main():
    # Get password from environment or use a default
    password = os.getenv("POSTGRES_PASSWORD", "password")
    db_uri = f"postgresql://postgres:{password}@localhost:5432/langgraph"
    
    print(f"Connecting to: {db_uri}")
    
    try:
        # Need to use autocommit=True to avoid transaction block issues with CREATE INDEX CONCURRENTLY
        # Configure the connection pool to use autocommit
        def configure_connection(conn):
            conn.autocommit = True
        
        with ConnectionPool(db_uri, configure=configure_connection) as pool:
            checkpointer = PostgresSaver(pool)
            print("Created checkpointer, running setup()...")
            
            # Run setup - this should now work with autocommit
            checkpointer.setup()
            print("✅ Setup worked!")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()