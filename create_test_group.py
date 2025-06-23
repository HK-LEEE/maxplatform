#!/usr/bin/env python3
"""
테스트 그룹 생성 및 사용자 할당 스크립트
"""

import sys
import os
sys.path.append('backend')

from backend.app.database import engine, SessionLocal
from backend.app.models.user import User, Group
from backend.app.models.permission import Feature
from sqlalchemy.orm import sessionmaker

def create_test_groups():
    """테스트 그룹 생성 및 기능 할당"""
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("🚀 테스트 그룹 생성 중...")
        
        # 관리자 사용자 찾기
        admin_user = db.query(User).filter(User.email == "admin@test.com").first()
        if not admin_user:
            print("❌ 관리자 사용자를 찾을 수 없습니다.")
            return False
        
        # 기존 그룹 삭제
        db.query(Group).delete()
        db.commit()
        
        # 1. 분석팀 그룹 생성
        analysis_group = Group(
            name="분석팀",
            description="데이터 분석 및 AI 관련 업무를 담당하는 팀",
            created_by=admin_user.id
        )
        db.add(analysis_group)
        db.flush()  # ID 생성을 위해
        
        # 분석팀에 기능 할당 (jupyter_workspace, apex, llm_chat)
        analysis_features = db.query(Feature).filter(
            Feature.name.in_(['dashboard', 'jupyter_workspace', 'apex', 'llm_chat'])
        ).all()
        analysis_group.features = analysis_features
        
        # 2. 관리팀 그룹 생성
        admin_group = Group(
            name="관리팀",
            description="시스템 관리 및 운영을 담당하는 팀",
            created_by=admin_user.id
        )
        db.add(admin_group)
        db.flush()
        
        # 관리팀에 모든 기능 할당
        all_features = db.query(Feature).all()
        admin_group.features = all_features
        
        # 3. 일반사용자 그룹 생성
        user_group = Group(
            name="일반사용자",
            description="기본 기능만 사용 가능한 일반 사용자 그룹",
            created_by=admin_user.id
        )
        db.add(user_group)
        db.flush()
        
        # 일반사용자에 기본 기능만 할당 (dashboard)
        basic_features = db.query(Feature).filter(
            Feature.name.in_(['dashboard'])
        ).all()
        user_group.features = basic_features
        
        db.commit()
        
        print("✅ 테스트 그룹 생성 완료:")
        print(f"  - 분석팀: {len(analysis_features)}개 기능 할당")
        print(f"  - 관리팀: {len(all_features)}개 기능 할당")
        print(f"  - 일반사용자: {len(basic_features)}개 기능 할당")
        
        # 관리자를 관리팀에 할당
        admin_user.group_id = admin_group.id
        db.commit()
        
        print(f"\n👤 관리자({admin_user.email})를 관리팀에 할당")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def show_group_info():
    """그룹 정보 표시"""
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("\n📊 현재 그룹 정보:")
        groups = db.query(Group).all()
        
        for group in groups:
            print(f"\n🏢 {group.name}")
            print(f"   설명: {group.description}")
            print(f"   기능: {len(group.features)}개")
            for feature in group.features:
                print(f"     - {feature.display_name} ({feature.name})")
            
            # 그룹에 속한 사용자 조회
            users = db.query(User).filter(User.group_id == group.id).all()
            print(f"   사용자: {len(users)}명")
            for user in users:
                print(f"     - {user.real_name} ({user.email})")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("테스트 그룹 생성 및 기능 할당")
    print("=" * 60)
    
    success = create_test_groups()
    
    if success:
        show_group_info()
        print("\n🎉 테스트 그룹 설정이 완료되었습니다!")
        print("\n다음 단계:")
        print("1. 웹 브라우저에서 http://localhost:3000 접속")
        print("2. admin@test.com / admin123! 로 로그인")
        print("3. Mother Page에서 할당된 기능들 확인")
    else:
        print("\n💥 그룹 설정 중 오류가 발생했습니다.")
        sys.exit(1) 