#!/usr/bin/env python3
import os, httpx, json
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / '.env')
except:
    pass

token = os.getenv('RAILWAY_TOKEN')
if not token:
    print("❌ RAILWAY_TOKEN not found")
    exit(1)

query = '''
query {
  project(id: "46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a") {
    services {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
'''

resp = httpx.post('https://backboard.railway.app/graphql/v2', 
  json={'query': query},
  headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
  timeout=30)

data = resp.json()
if data.get('errors'):
    print(f"❌ Error: {data['errors']}")
    exit(1)

for edge in data.get('data', {}).get('project', {}).get('services', {}).get('edges', []):
    node = edge['node']
    print(f"{node['name']}: {node['id']}")

