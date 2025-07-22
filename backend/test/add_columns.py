"""
데이터베이스 컬럼 추가 스크립트
"""
from app.database import engine
from sqlalchemy import text

def add_missing_columns():
    try:
        with engine.connect() as conn:
            # 기존 컬럼 확인
            result = conn.execute(text("SHOW COLUMNS FROM features LIKE 'is_external'"))
            if not result.fetchone():
                print("is_external 컬럼 추가 중...")
                conn.execute(text("ALTER TABLE features ADD COLUMN is_external BOOLEAN DEFAULT FALSE"))
                print("✅ is_external 컬럼 추가 완료")
            else:
                print("is_external 컬럼이 이미 존재합니다.")
            
            result = conn.execute(text("SHOW COLUMNS FROM features LIKE 'open_in_new_tab'"))
            if not result.fetchone():
                print("open_in_new_tab 컬럼 추가 중...")
                conn.execute(text("ALTER TABLE features ADD COLUMN open_in_new_tab BOOLEAN DEFAULT FALSE"))
                print("✅ open_in_new_tab 컬럼 추가 완료")
            else:
                print("open_in_new_tab 컬럼이 이미 존재합니다.")
            
            conn.commit()
            print("✅ 데이터베이스 스키마 업데이트 완료")
            
    except Exception as e:
        print(f"❌ 컬럼 추가 실패: {e}")

if __name__ == "__main__":
    add_missing_columns() 