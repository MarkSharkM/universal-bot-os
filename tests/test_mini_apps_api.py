"""
Basic tests for Mini Apps API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.main import app
from app.core.database import Base, get_db
from app.models.bot import Bot
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent


# Test database (in-memory SQLite for tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_bot(db_session):
    """Create test bot"""
    bot = Bot(
        id=uuid4(),
        platform_type="telegram",
        token="test_token",
        name="TestBot",
        config={},
        default_lang="uk",
        is_active=True
    )
    db_session.add(bot)
    db_session.commit()
    return bot


@pytest.fixture
def test_user(db_session, test_bot):
    """Create test user"""
    user = User(
        id=uuid4(),
        external_id="test_user_123",
        platform="telegram",
        bot_id=test_bot.id,
        language_code="uk",
        balance=0.0,
        custom_data={},
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_tonconnect_manifest(client):
    """Test TON Connect manifest endpoint"""
    response = client.get("/api/v1/mini-apps/tonconnect-manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "name" in data
    assert "iconUrl" in data


def test_analytics_event_storage(client, db_session, test_bot):
    """Test analytics event storage"""
    bot_id = str(test_bot.id)
    
    # Send analytics event
    response = client.post(
        f"/api/v1/mini-apps/mini-app/{bot_id}",
        json={
            "type": "analytics",
            "event": "test_event",
            "data": {"test": "value"}
        },
        params={"user_id": "test_user_123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["event"] == "test_event"
    assert data["stored"] is True
    
    # Check event was stored in database
    events = db_session.query(AnalyticsEvent).filter(
        AnalyticsEvent.bot_id == test_bot.id,
        AnalyticsEvent.event_name == "test_event"
    ).all()
    
    assert len(events) == 1
    assert events[0].event_name == "test_event"
    assert events[0].event_data == {"test": "value"}
    assert events[0].user_external_id == "test_user_123"


def test_analytics_event_with_user(client, db_session, test_bot, test_user):
    """Test analytics event with existing user"""
    bot_id = str(test_bot.id)
    
    # Send analytics event with user_id
    response = client.post(
        f"/api/v1/mini-apps/mini-app/{bot_id}",
        json={
            "type": "analytics",
            "event": "partner_click",
            "data": {"partner_id": "123"}
        },
        params={"user_id": test_user.external_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["stored"] is True
    
    # Check event was stored with user_id
    events = db_session.query(AnalyticsEvent).filter(
        AnalyticsEvent.bot_id == test_bot.id,
        AnalyticsEvent.user_id == test_user.id
    ).all()
    
    assert len(events) == 1
    assert events[0].user_id == test_user.id
    assert events[0].user_external_id == test_user.external_id


def test_partner_click_logging(client, db_session, test_bot):
    """Test partner click logging"""
    bot_id = str(test_bot.id)
    
    response = client.post(
        f"/api/v1/mini-apps/mini-app/{bot_id}",
        json={
            "action": "partner_click",
            "partner_id": "123"
        },
        params={"user_id": "test_user_123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["action"] == "partner_click"
    assert data["logged"] is True
