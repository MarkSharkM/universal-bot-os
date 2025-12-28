#!/usr/bin/env python3
"""
Run import via Railway API by getting DATABASE_URL and running locally
"""
import os
import sys
import httpx
import json
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
PROJECT_ID = "46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a"
SERVICE_ID = "a9598ef7-0499-439f-bf3c-c6de5f3cd022"  # api service


def get_service_variables(service_id: str) -> dict:
    """Get service environment variables"""
    query = """
    query GetVariables($serviceId: String!) {
      service(id: $serviceId) {
        variables {
          edges {
            node {
              key
              value
            }
          }
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = httpx.post(
        RAILWAY_GRAPHQL_URL,
        json={"query": query, "variables": {"serviceId": service_id}},
        headers=headers,
        timeout=30.0
    )
    
    if response.status_code != 200:
        print(f"Response: {response.text}")
        raise Exception(f"API error: {response.status_code}")
    
    result = response.json()
    if result.get("errors"):
        raise Exception(f"GraphQL errors: {result['errors']}")
    
    variables = {}
    for edge in result.get("data", {}).get("service", {}).get("variables", {}).get("edges", []):
        node = edge["node"]
        variables[node["key"]] = node["value"]
    
    return variables


def main():
    """Main function"""
    if not RAILWAY_TOKEN:
        print("❌ RAILWAY_TOKEN not found in .env")
        return
    
    print("📥 Getting DATABASE_URL from Railway...")
    try:
        vars = get_service_variables(SERVICE_ID)
        database_url = vars.get("DATABASE_URL")
        
        if not database_url:
            print("❌ DATABASE_URL not found in Railway")
            return
        
        print("✅ Got DATABASE_URL")
        print(f"   Setting DATABASE_URL environment variable...")
        os.environ["DATABASE_URL"] = database_url
        
        # Now run import
        print("\n🚀 Running import...")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from scripts.import_now import main as import_main
        import_main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

