from app.core.database import SessionLocal
from app.models.message import Message
from app.models.user import User

def cleanup_user_tests(external_id="380927579"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.external_id == external_id).first()
        if not user:
            print(f"User {external_id} not found")
            return
        
        # Delete only messages marked as test
        deleted = db.query(Message).filter(
            Message.user_id == user.id,
            Message.custom_data.contains({'is_test': True})
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"Deleted {deleted} test messages for user {external_id}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_user_tests()
