#!/usr/bin/env python3
"""
View Railway logs via API
"""
import sys
import os
import requests
import json
from datetime import datetime, timedelta

# Railway API endpoint
RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = "3eafda3e-4ce7-4834-b359-99a17e884"  # Account token
ENVIRONMENT_ID = "2cb4835c-5e82-47dd-96fd-e13027177188"

def get_railway_logs(limit=50, severity=None):
    """Get Railway logs via GraphQL API"""
    query = """
    query GetEnvironmentLogs($environmentId: String!, $limit: Int) {
      environmentLogs(environmentId: $environmentId, limit: $limit) {
        message
        timestamp
        severity
      }
    }
    """
    
    variables = {
        "environmentId": ENVIRONMENT_ID,
        "limit": limit
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RAILWAY_TOKEN}"
    }
    
    try:
        response = requests.post(
            RAILWAY_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return []
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL errors: {data['errors']}")
            return []
        
        logs = data.get("data", {}).get("environmentLogs", [])
        
        # Filter by severity if specified
        if severity:
            logs = [log for log in logs if log.get("severity", "").upper() == severity.upper()]
        
        return logs
        
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return []

def print_logs(logs, show_all=False):
    """Print logs in readable format"""
    if not logs:
        print("No logs found")
        return
    
    print(f"\n📊 Found {len(logs)} log entries:\n")
    print("=" * 100)
    
    for log in logs:
        severity = log.get("severity", "INFO")
        timestamp = log.get("timestamp", "")
        message = log.get("message", "")
        
        # Color coding
        if severity == "ERROR":
            prefix = "❌ [ERROR]"
        elif severity == "WARNING":
            prefix = "⚠️  [WARN]"
        else:
            prefix = "ℹ️  [INFO]"
        
        # Format timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "N/A"
        except:
            time_str = timestamp
        
        print(f"{prefix} {time_str}")
        print(f"   {message[:200]}")
        if len(message) > 200:
            print(f"   ... (truncated)")
        print()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="View Railway logs")
    parser.add_argument("--limit", type=int, default=50, help="Number of logs to fetch")
    parser.add_argument("--severity", choices=["ERROR", "WARNING", "INFO"], help="Filter by severity")
    parser.add_argument("--errors-only", action="store_true", help="Show only errors")
    parser.add_argument("--search", help="Search for text in logs")
    
    args = parser.parse_args()
    
    severity = "ERROR" if args.errors_only else args.severity
    
    logs = get_railway_logs(limit=args.limit, severity=severity)
    
    # Search filter
    if args.search:
        logs = [log for log in logs if args.search.lower() in log.get("message", "").lower()]
    
    print_logs(logs)

if __name__ == "__main__":
    main()
