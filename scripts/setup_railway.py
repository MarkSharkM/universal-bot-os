#!/usr/bin/env python3
"""
Railway Setup Script для Universal Bot OS
Створює проект, додає PostgreSQL та Redis, налаштовує змінні оточення
"""
import os
import sys
import json
import httpx
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Завантажити .env з кореня проекту
try:
    from dotenv import load_dotenv
    # Шукаємо .env в корені railway-mcp-project
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # Якщо dotenv не встановлено, використовуємо тільки os.getenv

RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
PROJECT_NAME = "universal-bot-os"


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
        raise Exception(f"GraphQL errors: {json.dumps(result['errors'], indent=2)}")
    
    return result.get("data", {})


def create_project(name: str) -> Dict[str, Any]:
    """Створити новий Railway проект"""
    print(f"🚂 Створюю проект '{name}'...")
    
    query = """
    mutation CreateProject($input: ProjectCreateInput!) {
      projectCreate(input: $input) {
        id
        name
      }
    }
    """
    
    variables = {
        "input": {
            "name": name
        }
    }
    
    result = make_graphql_request(query, variables)
    project = result["projectCreate"]
    
    print(f"✅ Проект створено!")
    print(f"   ID: {project['id']}")
    print(f"   Name: {project['name']}")
    print(f"   URL: https://railway.app/project/{project['id']}\n")
    
    return project


def get_projects() -> list:
    """Отримати список всіх проектів"""
    query = """
    query GetProjects {
      projects {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """
    
    result = make_graphql_request(query)
    projects = [edge["node"] for edge in result.get("projects", {}).get("edges", [])]
    return projects


def find_project(name: str) -> Optional[Dict[str, Any]]:
    """Знайти проект за назвою"""
    projects = get_projects()
    for project in projects:
        if project["name"] == name:
            return project
    return None


def create_service(project_id: str, name: str, source: Dict[str, Any] = None) -> Dict[str, Any]:
    """Створити сервіс в проекті"""
    print(f"📦 Створюю сервіс '{name}'...")
    
    query = """
    mutation CreateService($input: ServiceCreateInput!) {
      serviceCreate(input: $input) {
        id
        name
      }
    }
    """
    
    input_data = {
        "projectId": project_id,
        "name": name
    }
    
    if source:
        input_data["source"] = source
    
    variables = {"input": input_data}
    
    result = make_graphql_request(query, variables)
    service = result["serviceCreate"]
    
    print(f"✅ Сервіс '{name}' створено! ID: {service['id']}\n")
    return service


def add_postgresql(project_id: str) -> Dict[str, Any]:
    """Додати PostgreSQL плагін"""
    print("🐘 Додаю PostgreSQL...")
    
    query = """
    mutation AddPlugin($input: PluginCreateInput!) {
      pluginCreate(input: $input) {
        id
        name
        serviceId
      }
    }
    """
    
    variables = {
        "input": {
            "projectId": project_id,
            "name": "PostgreSQL",
            "type": "POSTGRES"
        }
    }
    
    try:
        result = make_graphql_request(query, variables)
        plugin = result["pluginCreate"]
        print(f"✅ PostgreSQL додано! ID: {plugin['id']}\n")
        return plugin
    except Exception as e:
        print(f"⚠️  Помилка при додаванні PostgreSQL: {e}")
        print("   Спробуй додати вручну через Railway UI\n")
        return {}


def add_redis(project_id: str) -> Dict[str, Any]:
    """Додати Redis плагін"""
    print("🔴 Додаю Redis...")
    
    query = """
    mutation AddPlugin($input: PluginCreateInput!) {
      pluginCreate(input: $input) {
        id
        name
        serviceId
      }
    }
    """
    
    variables = {
        "input": {
            "projectId": project_id,
            "name": "Redis",
            "type": "REDIS"
        }
    }
    
    try:
        result = make_graphql_request(query, variables)
        plugin = result["pluginCreate"]
        print(f"✅ Redis додано! ID: {plugin['id']}\n")
        return plugin
    except Exception as e:
        print(f"⚠️  Помилка при додаванні Redis: {e}")
        print("   Спробуй додати вручну через Railway UI\n")
        return {}


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


def wait_for_plugin_variables(plugin_id: str, timeout: int = 60) -> Dict[str, str]:
    """Чекати поки плагін створить змінні оточення"""
    print(f"⏳ Чекаю поки плагін налаштується (до {timeout} сек)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Спробуй отримати змінні через service
        # Це може не працювати через API, тому просто чекаємо
        time.sleep(5)
        print("   ...")
    
    print("✅ Плагін налаштовано (перевір змінні в Railway UI)\n")
    return {}


def main():
    """Головна функція"""
    print("🚀 Railway Setup для Universal Bot OS\n")
    print("=" * 50 + "\n")
    
    if not RAILWAY_TOKEN:
        print("❌ Помилка: RAILWAY_TOKEN не знайдено в змінних оточення")
        print("   Додай в .env: RAILWAY_TOKEN=твій-токен")
        sys.exit(1)
    
    # Перевір чи проект вже існує
    existing_project = find_project(PROJECT_NAME)
    
    if existing_project:
        print(f"ℹ️  Проект '{PROJECT_NAME}' вже існує!")
        print(f"   ID: {existing_project['id']}")
        print(f"   URL: https://railway.app/project/{existing_project['id']}\n")
        
        use_existing = input("Використати існуючий проект? (y/n): ").lower().strip()
        if use_existing != 'y':
            print("Скасовано.")
            sys.exit(0)
        
        project_id = existing_project["id"]
    else:
        # Створити новий проект
        project = create_project(PROJECT_NAME)
        project_id = project["id"]
    
    # Створити основний сервіс для додатку
    print("📦 Створюю основний сервіс для додатку...")
    app_service = create_service(project_id, "api")
    
    # Додати PostgreSQL
    postgres_plugin = add_postgresql(project_id)
    
    # Додати Redis
    redis_plugin = add_redis(project_id)
    
    # Отримати змінні оточення (якщо доступні)
    print("📋 Перевіряю змінні оточення...")
    time.sleep(5)  # Даємо час плагінам налаштуватися
    
    try:
        app_vars = get_service_variables(app_service["id"])
        print(f"✅ Знайдено {len(app_vars)} змінних для сервісу 'api'")
    except Exception as e:
        print(f"⚠️  Не вдалося отримати змінні: {e}")
        app_vars = {}
    
    # Підсумок
    print("\n" + "=" * 50)
    print("✅ Налаштування завершено!\n")
    print("📋 Наступні кроки:")
    print(f"   1. Відкрий Railway UI: https://railway.app/project/{project_id}")
    print("   2. Перевір що PostgreSQL та Redis додано")
    print("   3. В сервісі 'api' додай змінні оточення:")
    print("      - DATABASE_URL (автоматично з PostgreSQL)")
    print("      - REDIS_URL (автоматично з Redis)")
    print("      - SECRET_KEY (згенеруй: python -c \"import secrets; print(secrets.token_urlsafe(32))\")")
    print("      - ANTHROPIC_API_KEY (вже є в твоєму .env)")
    print("   4. Підключи GitHub репозиторій для автоматичного деплою")
    print("   5. Або задеплой вручну: railway up")
    print("\n💡 Порада: Railway автоматично створить DATABASE_URL та REDIS_URL")
    print("   коли додаси плагіни через UI (якщо через API не спрацювало)\n")


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

