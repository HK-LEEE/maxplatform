#!/usr/bin/env python3
"""
마이그레이션 실행 스크립트
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.database import get_database_url
from app.config import settings

def run_migration():
    """마이그레이션 실행"""
    print("🚀 데이터베이스 마이그레이션을 시작합니다...")
    
    # 데이터베이스 연결
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        # 데이터베이스 타입 확인
        db_type = settings.database_type.lower() if hasattr(settings, 'database_type') else 'mysql'
        
        # MySQL URL에서 확인
        if 'mysql' in database_url.lower():
            db_type = 'mysql'
        elif 'mssql' in database_url.lower() or 'sqlserver' in database_url.lower():
            db_type = 'mssql'
        
        print(f"📊 데이터베이스 타입: {db_type.upper()}")
        
        # 마이그레이션 파일 선택
        if db_type == 'mysql':
            migration_file = 'migrations/mysql_migration_001_add_service_system.sql'
        else:
            migration_file = 'migrations/mssql_migration_001_add_service_system.sql'
        
        # 마이그레이션 파일 읽기
        if not os.path.exists(migration_file):
            print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # SQL 문장들을 분리하여 실행
        with engine.connect() as connection:
            # 트랜잭션 시작
            trans = connection.begin()
            
            try:
                # MySQL의 경우 세미콜론으로 분리
                if db_type == 'mysql':
                    # MySQL 특정 명령어들을 처리
                    statements = []
                    current_statement = ""
                    
                    for line in migration_sql.split('\n'):
                        line = line.strip()
                        
                        # 주석 및 빈 줄 스킵
                        if not line or line.startswith('--'):
                            continue
                        
                        # SET 문장 특별 처리
                        if line.upper().startswith('SET '):
                            if current_statement:
                                statements.append(current_statement)
                                current_statement = ""
                            statements.append(line)
                            continue
                        
                        # INSERT IGNORE 특별 처리
                        if 'INSERT IGNORE' in line.upper():
                            current_statement += line + " "
                            if line.endswith(';'):
                                # INSERT IGNORE를 INSERT ... ON DUPLICATE KEY UPDATE로 변경
                                stmt = current_statement.replace('INSERT IGNORE', 'INSERT')
                                if 'user_services' in stmt:
                                    stmt = stmt.rstrip('; ') + ' ON DUPLICATE KEY UPDATE granted_at = granted_at;'
                                statements.append(stmt)
                                current_statement = ""
                            continue
                        
                        current_statement += line + " "
                        
                        if line.endswith(';'):
                            statements.append(current_statement)
                            current_statement = ""
                    
                    if current_statement.strip():
                        statements.append(current_statement)
                
                else:
                    # MSSQL의 경우
                    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                
                print(f"📋 실행할 SQL 문장 수: {len(statements)}")
                
                executed_count = 0
                for i, statement in enumerate(statements, 1):
                    statement = statement.strip()
                    if not statement or statement.upper() in ['GO', 'COMMIT', 'BEGIN TRANSACTION']:
                        continue
                    
                    try:
                        # 테이블 생성 및 기본 데이터 삽입
                        print(f"  ⏳ 실행 중 ({i}/{len(statements)}): {statement[:50]}...")
                        connection.execute(text(statement))
                        executed_count += 1
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        
                        # 이미 존재하는 테이블/인덱스는 무시
                        if any(ignore_msg in error_msg for ignore_msg in [
                            'already exists', 'table already exists', 'duplicate key name',
                            'duplicate entry', 'cannot create', 'exist'
                        ]):
                            print(f"  ⏭️  이미 존재함: {statement[:50]}...")
                            continue
                        else:
                            print(f"  ❌ 오류: {e}")
                            raise
                
                # 트랜잭션 커밋
                trans.commit()
                print(f"✅ 마이그레이션 완료! {executed_count}개 문장 실행됨")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 마이그레이션 실패: {e}")
                return False
    
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if not success:
        sys.exit(1) 