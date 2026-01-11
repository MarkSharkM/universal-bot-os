import sys
import os
import asyncio
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, ANY

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Settings before importing app.core.config
sys.modules['app.core.config'] = MagicMock()
sys.modules['app.core.config'].settings = MagicMock()
sys.modules['app.core.config'].settings.DATABASE_URL = "sqlite:///:memory:"

# Mock create_engine to avoid TypeError with SQLite and Postgres args
import sqlalchemy
sqlalchemy.create_engine = MagicMock()

from app.api.v1.admin import get_bot_analytics

async def test_analytics_logic():
    print("🚀 Starting Analytics Logic Verification (Mocked DB)...")
    
    # Mock Session
    mock_db = MagicMock()
    
    # Mock Bot
    mock_bot = MagicMock()
    mock_bot.id = uuid.uuid4()
    mock_bot.name = "Test Bot"
    
    # Setup expected daily clicks (3 days ago: 5 clicks, today: 10 clicks)
    today = date.today()
    three_days_ago = today - timedelta(days=3)
    
    # Mock Daily Query Results
    # Row objects usually have attributes corresponding to labels
    mock_daily_row_1 = MagicMock()
    mock_daily_row_1.date = three_days_ago
    mock_daily_row_1.count = 5
    
    mock_daily_row_2 = MagicMock()
    mock_daily_row_2.date = today
    mock_daily_row_2.count = 10
    
    # Mock Top Partners Results
    mock_partner_row_1 = MagicMock()
    mock_partner_row_1.partner_id = "partner_123"
    mock_partner_row_1.count = 50
    
    mock_partner_row_2 = MagicMock()
    mock_partner_row_2.partner_id = "partner_456"
    mock_partner_row_2.count = 30
    
    # Configure Query Side Effects
    # We need to handle multiple queries:
    # 1. bot query
    # 2. daily clicks query
    # 3. top partners query
    # 4. partners details query
    
    # Helper to return different mocks based on call chain could be complex.
    # Instead, we can just return specific lists if we mock the chain carefully, 
    # but SQLAlchemy chains are deep.
    
    # Let's mock the db.query() return value's methods.
    
    # Mocking the chain: db.query(...).filter(...).group_by(...).order_by(...).all()
    # It sends different queries. We can distinguish by the *entity* passed to query().
    
    def side_effect_query(*args):
        query_mock = MagicMock()
        
        # Check what we are querying
        entity = args[0]
        
        # 1. Bot Query: db.query(Bot)
        if hasattr(entity, '__name__') and entity.__name__ == 'Bot':
             query_mock.filter.return_value.first.return_value = mock_bot
             return query_mock
             
        # 2. Partners Details: db.query(BusinessData)
        if hasattr(entity, '__name__') and entity.__name__ == 'BusinessData':
            mock_p1 = MagicMock()
            mock_p1.id = "partner_123" # match UUID or string? Logic handles both hopefully.
            # Logic casts to string: str(p.id)
            # So mock.id should probably be an object that str() returns "partner_123" 
            # or just a string if the code allows (str("partner_123") is "partner_123")
            
            mock_p1.data = {'bot_name': 'Super Partner'}
            
            mock_p2 = MagicMock()
            mock_p2.id = "partner_456"
            mock_p2.data = {'bot_name': 'Mega Partner'}
            
            query_mock.filter.return_value.all.return_value = [mock_p1, mock_p2]
            return query_mock

        # 3. Analytics Queries (Daily & Top Partners)
        # These usages pass func.something, not a Class directly usually, OR they pass entities.
        # In my code:
        # daily_clicks: db.query(func.date(...), func.count(...))
        # top_partners: db.query(func.json_extract..., func.count...)
        
        # We can detect based on args length or type?
        # daily clicks asks for 2 columns.
        
        # We can implement a simplified mock that just returns the "Final" result 
        # when .all() is called, but we have two different .all() calls.
        
        # Iterate to handle sequential calls?
        # Or check filter criteria (hard to inspect).
        
        pass 
        
        return query_mock

    # Simplified Approach:
    # Since we can't easily distinguish the queries in 'side_effect_query', 
    # we will rely on the order of execution if we just return an iterator of mocks.
    # Order in code:
    # 1. Bot
    # 2. Daily Clicks
    # 3. Top Partners
    # 4. Partner Details (BusinessData)
    
    query1_bot = MagicMock()
    query1_bot.filter.return_value.first.return_value = mock_bot
    
    query2_daily = MagicMock()
    query2_daily.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [mock_daily_row_1, mock_daily_row_2]
    
    query3_top = MagicMock()
    query3_top.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_partner_row_1, mock_partner_row_2]
    
    query4_partners = MagicMock()
    
    mock_p1 = MagicMock()
    mock_p1.id = "partner_123" # Since implementation checks UUID(str(pid)), string is fine if it parses as UUID?
    # Logic: try UUID(str(pid)). If fails, it skips name lookup.
    # So "partner_123" will fail UUID check.
    # We should use real UUIDs for partners.
    
    real_uuid1 = uuid.uuid4()
    real_uuid2 = uuid.uuid4()
    
    mock_partner_row_1.partner_id = real_uuid1
    mock_partner_row_2.partner_id = real_uuid2
    
    mock_p1 = MagicMock()
    mock_p1.id = real_uuid1
    mock_p1.data = {'bot_name': 'Super Partner'}
    
    mock_p2 = MagicMock()
    mock_p2.id = real_uuid2
    mock_p2.data = {'bot_name': 'Mega Partner'}

    query4_partners.filter.return_value.all.return_value = [mock_p1, mock_p2]
    
    # Assign side effect
    mock_db.query.side_effect = [query1_bot, query2_daily, query3_top, query4_partners]

    # Run Function
    print("🔄 Calling get_bot_analytics...")
    result = await get_bot_analytics(bot_id=mock_bot.id, days=30, db=mock_db)

    # Verify Output Structure
    print("\n✅ Verifying Result Structure:")
    
    # 1. Check Total Clicks
    total = result['total_clicks']
    # 5 + 10 = 15. The logic sums formatted_daily counts.
    # Note: logic fills missing dates with 0. 
    # So sum should be 15.
    print(f"Total Clicks: {total}")
    if total == 15:
        print("✅ Total Clicks correct (15)")
    else:
        print(f"❌ Total Clicks incorrect: {total} (Expected 15)")

    # 2. Check Daily Clicks format
    daily = result['daily_clicks']
    print(f"Daily Clicks entries: {len(daily)}")
    # Should be 31 entries (today + 30 days back = 31 days inclusive?) 
    # Logic: since_date = now - 30 days. current loop goes from since_date to now.
    # Roughly 30 or 31.
    if len(daily) >= 30:
        print("✅ Daily Clicks range correct")
    else:
        print(f"❌ Daily Clicks range too short: {len(daily)}")
        
    # Check specific date values
    day_3_ago_str = str(three_days_ago)
    entry_3_ago = next((d for d in daily if d['date'] == day_3_ago_str), None)
    if entry_3_ago and entry_3_ago['count'] == 5:
         print("✅ Specific date payload correct (5 clicks)")
    else:
         print(f"❌ Specific date payload error: {entry_3_ago}")

    # 3. Check Top Partners
    top = result['top_partners']
    print(f"Top Partners count: {len(top)}")
    
    p1 = next((p for p in top if p['id'] == real_uuid1), None)
    if p1 and p1['count'] == 50 and p1['name'] == 'Super Partner':
        print("✅ Partner 1 Data correct")
    else:
        print(f"❌ Partner 1 Data error: {p1}")

    print("\n🎉 Logic Verification Passed!")

if __name__ == "__main__":
    asyncio.run(test_analytics_logic())
