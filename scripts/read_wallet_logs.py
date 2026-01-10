import sys
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import from app
# We are in scripts/, parent is universal-bot-os/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from app.core.database import engine

def read_logs():
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query for the debug logs we added
        # specific for wallet_validation_failed
        # We look for records in business_data where data_type='log'
        # The data column is JSONB, so we can query keys inside if needed, 
        # but for now let's just grab the latest logs.
        
        sql = text("""
            SELECT id, data, created_at 
            FROM business_data 
            WHERE data_type = 'log' 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        result = session.execute(sql)
        logs = result.fetchall()
        
        print(f"Found {len(logs)} logs:")
        print("-" * 50)
        
        for log in logs:
            log_id, data, created_at = log
            if data.get('event') not in ['wallet_validation_failed', 'wallet_validation_failed_api']:
                continue
                
            print(f"Log ID: {log_id}")
            print(f"Time: {created_at}")
            print(f"Wallet: {data.get('received_wallet_string')}")
            print(f"Type: {data.get('received_type')}")
            print(f"Length: {data.get('length')}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    read_logs()
