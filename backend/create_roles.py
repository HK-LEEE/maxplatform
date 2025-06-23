#!/usr/bin/env python3
"""
기본 역할(Role)과 그룹(Group)을 생성하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import Role, Group

def create_roles(db: Session):
    """기본 역할 생성"""
    roles = [
        {
            "name": "admin",
            "display_name": "관리자",
            "description": "시스템 전체 관리 권한"
        },
        {
            "name": "user",
            "display_name": "일반 사용자",
            "description": "기본 사용자 권한"
        },
        {
            "name": "analyst",
            "display_name": "분석가",
            "description": "데이터 분석 권한"
        },
        {
            "name": "developer",
            "display_name": "개발자",
            "description": "개발 도구 사용 권한"
        }
    ]
    
    for role_data in roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"역할 생성: {role_data['display_name']}")
    
    db.commit()

def create_groups(db: Session):
    """기본 그룹 생성"""
    groups = [
        {
            "name": "administrators",
            "display_name": "관리자 그룹",
            "description": "시스템 관리자들"
        },
        {
            "name": "users",
            "display_name": "일반 사용자 그룹",
            "description": "일반 사용자들"
        },
        {
            "name": "analysts",
            "display_name": "분석가 그룹",
            "description": "데이터 분석가들"
        },
        {
            "name": "developers",
            "display_name": "개발자 그룹",
            "description": "개발자들"
        }
    ]
    
    for group_data in groups:
        existing = db.query(Group).filter(Group.name == group_data["name"]).first()
        if not existing:
            group = Group(**group_data)
            db.add(group)
            print(f"그룹 생성: {group_data['display_name']}")
    
    db.commit()

def main():
    """메인 실행 함수"""
    print("기본 역할 및 그룹 생성을 시작합니다...")
    
    db = next(get_db())
    
    try:
        # 1. 기본 역할 생성
        print("\n1. 기본 역할 생성 중...")
        create_roles(db)
        
        # 2. 기본 그룹 생성
        print("\n2. 기본 그룹 생성 중...")
        create_groups(db)
        
        print("\n✅ 기본 역할 및 그룹 생성이 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main() 