from sqlalchemy.orm import Session
from ..models.user import User
from ..schemas.user import UserCreate
from ..utils.auth import get_password_hash, verify_password

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate):
        """새 사용자 생성"""
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_user_by_username(self, username: str):
        """사용자명으로 사용자 조회"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str):
        """이메일로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, username: str, password: str):
        """사용자 인증"""
        user = self.get_user_by_username(username)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user
    
    def is_username_taken(self, username: str) -> bool:
        """사용자명 중복 확인"""
        return self.get_user_by_username(username) is not None
    
    def is_email_taken(self, email: str) -> bool:
        """이메일 중복 확인"""
        return self.get_user_by_email(email) is not None 