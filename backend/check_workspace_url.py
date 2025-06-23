import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host='localhost',
        database='jupyter_platform',
        user='root',
        password='your_password'
    )
    
    if connection.is_connected():
        cursor = connection.cursor()
        
        # 워크스페이스 관련 기능들 조회
        cursor.execute("""
            SELECT service_name, service_display_name, url 
            FROM features 
            WHERE service_name LIKE '%workspace%' OR url LIKE '%workspace%'
        """)
        records = cursor.fetchall()
        
        print('현재 워크스페이스 관련 기능들:')
        for record in records:
            print(f'서비스명: {record[0]}, 표시명: {record[1]}, URL: {record[2]}')
        
        # 모든 기능들의 URL 확인
        print('\n모든 기능들:')
        cursor.execute("SELECT service_name, service_display_name, url FROM features ORDER BY service_name")
        records = cursor.fetchall()
        
        for record in records:
            print(f'서비스명: {record[0]}, 표시명: {record[1]}, URL: {record[2]}')
            
except Error as e:
    print(f'Error: {e}')
finally:
    if connection.is_connected():
        cursor.close()
        connection.close() 