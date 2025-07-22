from passlib.context import CryptContext

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 샘플 비밀번호들 해싱
passwords = {
    'admin123!': '',
    'test123!': '',
    'manager123!': '',
    'user123!': '', 
    'dev123!': ''
}

print("🔐 비밀번호 해시 생성 중...")
print("=" * 50)

for password in passwords.keys():
    hashed = hash_password(password)
    passwords[password] = hashed
    print(f"Password: {password}")
    print(f"Hash: {hashed}")
    print("-" * 50)

# 마이그레이션 스크립트용 포맷으로 출력
print("\n📋 마이그레이션 스크립트용 해시:")
print("=" * 50)
for password, hashed in passwords.items():
    print(f"'{password}': '{hashed}',") 