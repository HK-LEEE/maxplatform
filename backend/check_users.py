from app.database import get_db
from app.models import User

try:
    db = next(get_db())
    users = db.query(User).all()
    print(f'Total users: {len(users)}')
    
    for i, user in enumerate(users[:5]):
        print(f'User {i+1}: {user.email}, ID: {user.id}')
    
    # 첫 번째 사용자로 테스트용 토큰 생성
    if users:
        from app.routers.auth import create_access_token
        from datetime import timedelta
        
        test_user = users[0]
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(test_user.id)}, expires_delta=access_token_expires
        )
        print(f'\nTest token for {test_user.email}: {access_token}')
        
    db.close()
except Exception as e:
    print(f'Error: {e}') 