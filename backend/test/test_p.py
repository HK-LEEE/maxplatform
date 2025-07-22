import psycopg2
import os

try:
    # 1단계에서 확인한 Windows 호스트 IP 주소를 사용합니다.
    # 이 값은 WSL 재시작 시 변경될 수 있습니다.
    windows_host_ip = "127.168.30.2" # 예: "172.23.144.1"

    # PostgreSQL 연결 정보
    conn = psycopg2.connect(
        host=windows_host_ip,
        port="5432",  # PostgreSQL 포트 (기본값)
        dbname="your_db_name", # 연결할 데이터베이스 이름
        user="your_username",   # PostgreSQL 사용자 이름
        password="your_password"  # PostgreSQL 비밀번호
    )

    # 커서 생성
    cur = conn.cursor()

    # 간단한 쿼리 실행
    cur.execute("SELECT version();")

    # 결과 가져오기
    db_version = cur.fetchone()
    print("연결 성공!")
    print("PostgreSQL 버전:", db_version)

    # 리소스 정리
    cur.close()
    conn.close()

except psycopg2.OperationalError as e:
    print(f"연결 실패: {e}")
except Exception as e:
    print(f"오류 발생: {e}")
