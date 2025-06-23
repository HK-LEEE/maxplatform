# 파일 저장 관리 시스템 가이드

이 문서는 사용자별/그룹별 파일 저장 관리 시스템의 구조와 사용법을 설명합니다.

## 시스템 개요

RAG 시스템에 업로드되는 모든 파일은 체계적으로 관리되며, 사용자별 또는 그룹별로 분리된 저장소에 보관됩니다.

## 저장소 구조

```
file_storage/
├── users/                          # 사용자별 저장소
│   └── {user_id}/                   # 사용자 ID별 폴더
│       └── rag_datasources/         # RAG 데이터소스 폴더
│           └── ds_{id}_{name}/      # 데이터소스별 폴더
│               ├── 20241201_120000_a1b2c3d4_document1.pdf
│               ├── 20241201_120030_e5f6g7h8_document2.txt
│               └── ...
└── groups/                          # 그룹별 저장소
    └── {group_id}/                  # 그룹 ID별 폴더
        └── rag_datasources/         # RAG 데이터소스 폴더
            └── ds_{id}_{name}/      # 데이터소스별 폴더
                ├── 20241201_130000_i9j0k1l2_shared_doc.pdf
                └── ...
```

## 파일 명명 규칙

업로드된 파일은 다음 형식으로 저장됩니다:

```
{timestamp}_{unique_id}_{sanitized_filename}
```

- **timestamp**: `YYYYMMDD_HHMMSS` 형식의 업로드 시간
- **unique_id**: 8자리 고유 식별자
- **sanitized_filename**: 안전화된 원본 파일명

### 예시
- 원본: `김교수의 추천도서 100권 (2024).pdf`
- 저장: `20241201_143022_a1b2c3d4_김교수의_추천도서_100권_2024_.pdf`

## 주요 기능

### 1. 자동 파일 저장
- 모든 업로드 파일이 자동으로 적절한 위치에 저장
- 파일명 중복 방지
- 메타데이터 자동 기록

### 2. 권한 기반 접근 제어
- 사용자는 자신의 파일만 접근 가능
- 그룹 멤버는 그룹 파일에 접근 가능
- 관리자는 모든 파일에 접근 가능

### 3. 저장소 통계
- 사용자별/그룹별 저장 용량 추적
- 파일 수 통계
- 실시간 사용량 모니터링

### 4. 파일 생명주기 관리
- 데이터소스 삭제 시 관련 파일 자동 정리
- 고아 파일 방지
- 안전한 파일 삭제

## API 엔드포인트

### 1. 저장된 파일 목록 조회
```http
GET /api/v1/llmops/rag-datasources/{source_id}/stored-files
Authorization: Bearer {token}
```

**응답 예시:**
```json
{
  "datasource_id": 11,
  "datasource_name": "내 문서",
  "stored_files": [
    {
      "filename": "20241201_143022_a1b2c3d4_document.pdf",
      "file_path": "/path/to/file",
      "file_size": 1048576,
      "created_time": "2024-12-01T14:30:22",
      "modified_time": "2024-12-01T14:30:22",
      "relative_path": "users/user123/rag_datasources/ds_11_내문서/..."
    }
  ],
  "storage_stats": {
    "owner_type": "USER",
    "owner_id": "user123",
    "total_size_bytes": 10485760,
    "total_size_mb": 10.0,
    "file_count": 5,
    "storage_path": "/path/to/storage"
  },
  "total_stored_files": 1
}
```

### 2. 저장된 파일 삭제
```http
DELETE /api/v1/llmops/rag-datasources/{source_id}/stored-files?file_path={file_path}
Authorization: Bearer {token}
```

### 3. 저장소 사용량 개요
```http
GET /api/v1/llmops/storage/overview
Authorization: Bearer {token}
```

## 프론트엔드 기능

### 1. 파일 관리 탭
- **문서 청크**: 벡터화된 문서 조각들
- **원본 파일**: 업로드된 원본 파일들

### 2. 저장소 통계 표시
- 실시간 사용량 표시
- 파일 수 카운트
- 저장 경로 정보

### 3. 파일 작업
- 개별 파일 삭제
- 일괄 파일 삭제
- 파일 검색 및 필터링

## 설정 및 관리

### 1. 기본 저장 경로 설정
```python
# backend/app/llmops/file_storage_service.py
class FileStorageService:
    def __init__(self, base_storage_path: str = "./file_storage"):
        self.base_storage_path = Path(base_storage_path)
```

### 2. 환경 변수 설정
```bash
# .env 파일에 추가
FILE_STORAGE_BASE_PATH=./file_storage
FILE_STORAGE_MAX_SIZE_MB=1000  # 사용자당 최대 저장 용량 (향후 구현)
```

### 3. 디스크 공간 모니터링
```python
# 저장소 사용량 확인
from app.llmops.file_storage_service import FileStorageService

storage_service = FileStorageService()
stats = storage_service.get_storage_stats("USER", "user123")
print(f"사용량: {stats['total_size_mb']} MB")
```

## 보안 고려사항

### 1. 파일명 안전화
- 특수문자 제거 및 치환
- 경로 탐색 공격 방지
- 파일명 길이 제한

### 2. 접근 권한 검증
- 모든 파일 작업에 권한 확인
- 사용자별 격리된 저장소
- 그룹 권한 기반 접근 제어

### 3. 파일 타입 검증
- 허용된 파일 타입만 업로드
- 악성 파일 업로드 방지
- 파일 크기 제한

## 백업 및 복구

### 1. 백업 전략
```bash
# 전체 저장소 백업
tar -czf file_storage_backup_$(date +%Y%m%d).tar.gz file_storage/

# 사용자별 백업
tar -czf user_backup_$(date +%Y%m%d).tar.gz file_storage/users/{user_id}/
```

### 2. 복구 절차
```bash
# 전체 복구
tar -xzf file_storage_backup_20241201.tar.gz

# 사용자별 복구
tar -xzf user_backup_20241201.tar.gz -C file_storage/users/{user_id}/
```

## 성능 최적화

### 1. 대용량 파일 처리
- 스트리밍 업로드 지원
- 청크 단위 처리
- 메모리 사용량 최적화

### 2. 저장소 정리
```python
# 고아 파일 정리 (향후 구현)
def cleanup_orphaned_files():
    # 데이터베이스에 없는 파일들 정리
    pass

# 임시 파일 정리
def cleanup_temp_files():
    # 업로드 실패한 임시 파일들 정리
    pass
```

### 3. 캐싱 전략
- 파일 메타데이터 캐싱
- 자주 접근하는 파일 정보 캐시
- 저장소 통계 캐싱

## 모니터링 및 로깅

### 1. 로그 예시
```
INFO:app.llmops.file_storage_service:File saved: document.pdf -> /path/to/storage/...
INFO:app.llmops.file_storage_service:File deleted: /path/to/file
INFO:app.llmops.file_storage_service:Cleaned up files for datasource 123
```

### 2. 메트릭 수집
- 업로드 파일 수
- 저장소 사용량
- 파일 삭제 횟수
- 오류 발생률

## 문제 해결

### 1. 디스크 공간 부족
```bash
# 저장소 사용량 확인
du -sh file_storage/

# 큰 파일 찾기
find file_storage/ -type f -size +100M -ls
```

### 2. 권한 문제
```bash
# 저장소 권한 확인
ls -la file_storage/

# 권한 수정
chmod -R 755 file_storage/
chown -R app:app file_storage/
```

### 3. 파일 손상
- 정기적인 파일 무결성 검사
- 백업에서 복구
- 사용자에게 재업로드 요청

## 향후 개선 계획

1. **저장소 할당량 관리**: 사용자별 저장 용량 제한
2. **파일 압축**: 자동 파일 압축으로 공간 절약
3. **클라우드 저장소 연동**: AWS S3, Google Cloud Storage 지원
4. **파일 버전 관리**: 동일 파일의 여러 버전 관리
5. **자동 정리**: 오래된 파일 자동 아카이브/삭제 