-- Jupyter Data Platform 데이터베이스 설정

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS jupyter_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 및 권한 부여 (선택사항)
-- CREATE USER 'jupyter_user'@'localhost' IDENTIFIED BY 'your_password';
-- GRANT ALL PRIVILEGES ON jupyter_platform.* TO 'jupyter_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 데이터베이스 사용
USE jupyter_platform;

-- 테이블은 FastAPI 애플리케이션에서 자동으로 생성됩니다.
-- SQLAlchemy가 Base.metadata.create_all()을 통해 테이블을 생성합니다.

SELECT 'Database setup completed!' as message; 