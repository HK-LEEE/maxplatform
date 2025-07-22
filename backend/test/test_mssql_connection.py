#!/usr/bin/env python3
"""
MSSQL ODBC 18 연결 테스트 스크립트
"""

import pyodbc
import sqlalchemy
from sqlalchemy import create_engine, text
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pyodbc_connection():
    """pyodbc를 사용한 직접 연결 테스트"""
    print("=" * 50)
    print("1. pyodbc 직접 연결 테스트")
    print("=" * 50)
    
    # 연결 문자열 옵션들
    connection_strings = [
        # ODBC Driver 18
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=172.28.32.1\\SQLEXPRESS;DATABASE=AIDB;UID=mss;PWD=2300;TrustServerCertificate=yes;Encrypt=optional;",
        
        # ODBC Driver 17 (fallback)
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=172.28.32.1\\SQLEXPRESS;DATABASE=AIDB;UID=mss;PWD=2300;TrustServerCertificate=yes;Encrypt=optional;",
        
        # 암호화 없이
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=172.28.32.1\\SQLEXPRESS;DATABASE=AIDB;UID=mss;PWD=2300;Encrypt=no;",
        
        # 포트 명시
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=172.28.32.1,1433\\SQLEXPRESS;DATABASE=AIDB;UID=mss;PWD=2300;TrustServerCertificate=yes;Encrypt=optional;",
    ]
    
    for i, conn_str in enumerate(connection_strings, 1):
        print(f"\n연결 시도 {i}:")
        print(f"연결 문자열: {conn_str}")
        
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            
            # 간단한 쿼리 실행
            cursor.execute("SELECT @@VERSION as version, DB_NAME() as database_name, SYSTEM_USER as user_name")
            row = cursor.fetchone()
            
            print("✅ 연결 성공!")
            print(f"   SQL Server 버전: {row.version[:80]}...")
            print(f"   데이터베이스: {row.database_name}")
            print(f"   사용자: {row.user_name}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 연결 실패: {str(e)}")
            continue
    
    return False

def test_sqlalchemy_connection():
    """SQLAlchemy를 사용한 연결 테스트"""
    print("\n" + "=" * 50)
    print("2. SQLAlchemy 연결 테스트")
    print("=" * 50)
    
    # SQLAlchemy 연결 URL들
    connection_urls = [
        # ODBC Driver 18
        "mssql+pyodbc://mss:2300@172.28.32.1\\SQLEXPRESS/AIDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=optional",
        
        # ODBC Driver 17
        "mssql+pyodbc://mss:2300@172.28.32.1\\SQLEXPRESS/AIDB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=optional",
        
        # 암호화 없이
        "mssql+pyodbc://mss:2300@172.28.32.1\\SQLEXPRESS/AIDB?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=no",
        
        # 포트 명시
        "mssql+pyodbc://mss:2300@172.28.32.1:1433\\SQLEXPRESS/AIDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=optional",
    ]
    
    for i, url in enumerate(connection_urls, 1):
        print(f"\n연결 시도 {i}:")
        print(f"연결 URL: {url}")
        
        try:
            engine = create_engine(url, echo=False, pool_timeout=10, pool_recycle=3600)
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT @@VERSION as version, DB_NAME() as database_name, SYSTEM_USER as user_name"))
                row = result.fetchone()
                
                print("✅ SQLAlchemy 연결 성공!")
                print(f"   SQL Server 버전: {row.version[:80]}...")
                print(f"   데이터베이스: {row.database_name}")
                print(f"   사용자: {row.user_name}")
                
                # 테이블 목록 조회
                tables_result = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"))
                tables = [row[0] for row in tables_result.fetchall()]
                print(f"   테이블 수: {len(tables)}")
                if tables:
                    print(f"   첫 5개 테이블: {tables[:5]}")
                
                return True
                
        except Exception as e:
            print(f"❌ SQLAlchemy 연결 실패: {str(e)}")
            continue
    
    return False

def check_odbc_drivers():
    """설치된 ODBC 드라이버 확인"""
    print("\n" + "=" * 50)
    print("3. 설치된 ODBC 드라이버 확인")
    print("=" * 50)
    
    try:
        drivers = pyodbc.drivers()
        print("설치된 ODBC 드라이버:")
        for driver in drivers:
            print(f"  - {driver}")
            
        # SQL Server 드라이버 확인
        sql_server_drivers = [d for d in drivers if 'SQL Server' in d]
        if sql_server_drivers:
            print(f"\nSQL Server 드라이버: {sql_server_drivers}")
        else:
            print("\n❌ SQL Server ODBC 드라이버를 찾을 수 없습니다!")
            
    except Exception as e:
        print(f"❌ 드라이버 조회 실패: {str(e)}")

def test_network_connectivity():
    """네트워크 연결 테스트"""
    print("\n" + "=" * 50)
    print("4. 네트워크 연결 테스트")
    print("=" * 50)
    
    import socket
    
    # SQL Server 기본 포트 테스트
    ports_to_test = [1433, 1434]  # 1433: 기본 포트, 1434: SQL Browser
    
    for port in ports_to_test:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('172.28.32.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ 포트 {port}: 연결 가능")
            else:
                print(f"❌ 포트 {port}: 연결 불가")
                
        except Exception as e:
            print(f"❌ 포트 {port} 테스트 실패: {str(e)}")

def main():
    """메인 테스트 함수"""
    print("MSSQL ODBC 18 연결 테스트를 시작합니다...")
    print(f"대상 서버: 172.28.32.1\\SQLEXPRESS")
    print(f"데이터베이스: AIDB")
    print(f"사용자: mss")
    
    # 1. 설치된 드라이버 확인
    check_odbc_drivers()
    
    # 2. 네트워크 연결 테스트
    test_network_connectivity()
    
    # 3. pyodbc 직접 연결 테스트
    pyodbc_success = test_pyodbc_connection()
    
    # 4. SQLAlchemy 연결 테스트
    sqlalchemy_success = test_sqlalchemy_connection()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    print(f"pyodbc 연결: {'✅ 성공' if pyodbc_success else '❌ 실패'}")
    print(f"SQLAlchemy 연결: {'✅ 성공' if sqlalchemy_success else '❌ 실패'}")
    
    if not pyodbc_success and not sqlalchemy_success:
        print("\n권장 해결 방법:")
        print("1. SQL Server가 실행 중인지 확인")
        print("2. SQL Server Browser 서비스 시작")
        print("3. TCP/IP 프로토콜 활성화")
        print("4. 방화벽 설정 확인 (포트 1433, 1434)")
        print("5. SQLEXPRESS 인스턴스명 확인")
        print("6. 사용자 권한 확인")

if __name__ == "__main__":
    main()