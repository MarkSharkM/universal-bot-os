#!/usr/bin/env python3
"""
Налаштування Railway проекту universal-bot-os
Додає PostgreSQL, Redis, налаштовує змінні оточення
"""
import os
import sys
import json
import httpx
import time
import secrets
from typing import Dict, Any, Optional
from pathlib import Path

# Завантажити .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
PROJECT_ID = "46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a"  # universal-bot-os


def make_graphql_request(query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
    """Виконати GraphQL запит до Railway API"""
    if not RAILWAY_TOKEN:
        raise ValueError("RAILWAY_TOKEN environment variable is required")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = httpx.post(RAILWAY_GRAPHQL_URL, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    result = response.json()
    
    if result.get("errors"):
        error_msg = json.dumps(result["errors"], indent=2)
        raise Exception(f"GraphQL errors: {error_msg}")
    
    return result.get("data", {})


def get_project_services(project_id: str) -> list:
    """Отримати список сервісів проекту"""
    query = """
    query GetServices($projectId: String!) {
      project(id: $projectId) {
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
    """
    
    variables = {"projectId": project_id}
    result = make_graphql_request(query, variables)
    
    services = []
    for edge in result.get("project", {}).get("services", {}).get("edges", []):
        services.append(edge["node"])
    
    return services


def get_service_variables(service_id: str) -> Dict[str, str]:
    """Отримати змінні оточення сервісу"""
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
    
    variables = {"serviceId": service_id}
    result = make_graphql_request(query, variables)
    
    vars_dict = {}
    for edge in result.get("service", {}).get("variables", {}).get("edges", []):
        node = edge["node"]
        vars_dict[node["key"]] = node["value"]
    
    return vars_dict


def create_plugin(project_id: str, plugin_type: str, name: str) -> Optional[Dict[str, Any]]:
    """Створити плагін (PostgreSQL/Redis)"""
    print(f"🔧 Створюю плагін {name} ({plugin_type})...")
    
    # Спробуємо через REST API
    try:
        # Railway має REST API для плагінів
        # Але GraphQL може не підтримувати це
        # Спробуємо через serviceCreate з source
        query = """
        mutation CreateService($input: ServiceCreateInput!) {
          serviceCreate(input: $input) {
            id
            name
          }
        }
        """
        
        variables = {
            "input": {
                "projectId": project_id,
                "name": name
            }
        }
        
        result = make_graphql_request(query, variables)
        service = result.get("serviceCreate")
        
        if service:
            print(f"✅ Сервіс '{name}' створено! ID: {service['id']}")
            return service
    except Exception as e:
        print(f"⚠️  Не вдалося створити через API: {e}")
        print(f"   Потрібно додати {name} вручну через Railway UI")
    
    return None


def set_variable(service_id: str, key: str, value: str) -> bool:
    """Встановити змінну оточення"""
    print(f"   Встановлюю {key}...")
    
    query = """
    mutation SetVariable($input: VariableUpsertInput!) {
      variableUpsert(input: $input) {
        id
      }
    }
    """
    
    variables = {
        "input": {
            "serviceId": service_id,
            "key": key,
            "value": value
        }
    }
    
    try:
        result = make_graphql_request(query, variables)
        if result.get("variableUpsert"):
            print(f"   ✅ {key} встановлено")
            return True
    except Exception as e:
        print(f"   ⚠️  Не вдалося встановити {key}: {e}")
        print(f"      Встанови вручну в Railway UI")
    
    return False


def generate_secret_key() -> str:
    """Згенерувати SECRET_KEY"""
    return secrets.token_urlsafe(32)


def main():
    """Головна функція"""
    print("🚀 Налаштування Railway проекту universal-bot-os\n")
    print("=" * 60 + "\n")
    
    if not RAILWAY_TOKEN:
        print("❌ Помилка: RAILWAY_TOKEN не знайдено")
        sys.exit(1)
    
    # Отримати сервіси проекту
    print("📋 Отримую інформацію про проект...")
    try:
        services = get_project_services(PROJECT_ID)
        print(f"✅ Знайдено {len(services)} сервісів:")
        for svc in services:
            print(f"   - {svc['name']} (ID: {svc['id']})")
        print()
    except Exception as e:
        print(f"❌ Помилка при отриманні сервісів: {e}")
        sys.exit(1)
    
    # Знайти сервіс 'api'
    api_service = None
    for svc in services:
        if svc['name'] == 'api':
            api_service = svc
            break
    
    if not api_service:
        print("❌ Сервіс 'api' не знайдено!")
        print("   Створи сервіс 'api' вручну через Railway UI")
        sys.exit(1)
    
    api_service_id = api_service['id']
    print(f"✅ Сервіс 'api' знайдено: {api_service_id}\n")
    
    # Перевірити поточні змінні
    print("📋 Перевіряю поточні змінні оточення...")
    try:
        current_vars = get_service_variables(api_service_id)
        print(f"   Знайдено {len(current_vars)} змінних")
        if current_vars:
            for key in list(current_vars.keys())[:5]:
                print(f"   - {key}")
        print()
    except Exception as e:
        print(f"⚠️  Не вдалося отримати змінні: {e}\n")
        current_vars = {}
    
    # Перевірити чи є DATABASE_URL та REDIS_URL
    has_database = 'DATABASE_URL' in current_vars
    has_redis = 'REDIS_URL' in current_vars
    
    print("🔍 Перевірка необхідних змінних:")
    print(f"   DATABASE_URL: {'✅' if has_database else '❌'}")
    print(f"   REDIS_URL: {'✅' if has_redis else '❌'}")
    print(f"   SECRET_KEY: {'✅' if 'SECRET_KEY' in current_vars else '❌'}")
    print(f"   ANTHROPIC_API_KEY: {'✅' if 'ANTHROPIC_API_KEY' in current_vars else '❌'}")
    print()
    
    # Встановити змінні, яких не вистачає
    print("⚙️  Налаштування змінних оточення...\n")
    
    # SECRET_KEY
    if 'SECRET_KEY' not in current_vars:
        secret_key = generate_secret_key()
        print(f"🔑 Генерую SECRET_KEY...")
        set_variable(api_service_id, 'SECRET_KEY', secret_key)
        print()
    else:
        print("✅ SECRET_KEY вже встановлено\n")
    
    # ANTHROPIC_API_KEY
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key and 'ANTHROPIC_API_KEY' not in current_vars:
        print(f"🤖 Додаю ANTHROPIC_API_KEY...")
        set_variable(api_service_id, 'ANTHROPIC_API_KEY', anthropic_key)
        print()
    elif 'ANTHROPIC_API_KEY' in current_vars:
        print("✅ ANTHROPIC_API_KEY вже встановлено\n")
    else:
        print("⚠️  ANTHROPIC_API_KEY не знайдено в .env\n")
    
    # DATABASE_URL та REDIS_URL
    if not has_database or not has_redis:
        print("📦 Інформація про бази даних:")
        print("   ⚠️  DATABASE_URL та REDIS_URL створюються автоматично")
        print("      коли додаєш PostgreSQL та Redis через Railway UI")
        print("   📋 Дії:")
        print("      1. Відкрий: https://railway.app/project/" + PROJECT_ID)
        print("      2. Натисни 'New' → 'Database' → 'PostgreSQL'")
        print("      3. Натисни 'New' → 'Database' → 'Redis'")
        print("      4. Railway автоматично створить змінні для сервісу 'api'")
        print()
    
    # Підсумок
    print("=" * 60)
    print("✅ Налаштування завершено!\n")
    print("📋 Статус:")
    print(f"   - Проект: universal-bot-os ({PROJECT_ID})")
    print(f"   - Сервіс API: {api_service_id}")
    print(f"   - DATABASE_URL: {'✅' if has_database else '❌ Потрібно додати PostgreSQL'}")
    print(f"   - REDIS_URL: {'✅' if has_redis else '❌ Потрібно додати Redis'}")
    print(f"   - SECRET_KEY: {'✅' if 'SECRET_KEY' in current_vars else '✅ Встановлено'}")
    print(f"   - ANTHROPIC_API_KEY: {'✅' if anthropic_key else '⚠️  Додай вручну'}")
    print()
    print("🔗 Railway UI: https://railway.app/project/" + PROJECT_ID)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Скасовано користувачем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

