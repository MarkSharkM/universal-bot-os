import os
import sqlite3
from sqlalchemy import create_url
from app.core.database import SessionLocal
from app.models.message import Message
from sqlalchemy import desc

def check_messages():
    db = SessionLocal()
    try:
        messages = db.query(Message).order_by(desc(Message.timestamp)).limit(10).all()
        print(f"Total messages in DB: {db.query(Message).count()}")
        for m in messages:
            print(f"ID: {m.id}, User: {m.user_id}, Role: {m.role}, Content: {m.content[:50]}, Time: {m.timestamp}")
    finally:
        db.close()

if __name__ == "__main__":
    check_messages()
