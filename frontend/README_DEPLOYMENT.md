# Max Platform Frontend 배포 가이드

## 문제 해결: /admin 페이지 새로고침 404 오류

### 문제 원인
1. **개발 환경**: Vite proxy가 `/admin`을 백엔드 API로 잘못 전달
2. **프로덕션 환경**: Nginx가 `/admin`을 백엔드로 프록시하여 React Router가 처리 못함

### 해결 방법

#### 1. 개발 환경 (Vite)
`vite.config.ts`에서 `/admin` 프록시 제거 완료:
```javascript
proxy: {
  '/api': {
    target: apiBaseUrl,
    changeOrigin: true
  }
  // '/admin' 프록시 제거됨
}
```

#### 2. 프로덕션 환경 (Nginx)
`nginx.conf.fixed` 파일 사용:

주요 변경사항:
- `/admin/` location 블록 제거
- 모든 프론트엔드 라우트는 `location /`에서 처리
- 백엔드 admin API는 `/api/admin/*` 경로로만 접근

### 배포 절차

#### Nginx 설정 적용
```bash
# 1. 백업
sudo cp /etc/nginx/sites-available/max.dwchem.co.kr /etc/nginx/sites-available/max.dwchem.co.kr.backup

# 2. 새 설정 적용
sudo cp nginx.conf.fixed /etc/nginx/sites-available/max.dwchem.co.kr

# 3. 설정 테스트
sudo nginx -t

# 4. Nginx 재시작
sudo systemctl reload nginx
```

#### Vercel 배포
`vercel.json` 파일이 이미 설정되어 있음 - 추가 작업 불필요

#### Apache 배포
`public/.htaccess` 파일이 이미 설정되어 있음 - 추가 작업 불필요

### 테스트 체크리스트
- [ ] `/` 페이지 접근 및 새로고침
- [ ] `/login` 페이지 접근 및 새로고침
- [ ] `/admin` 페이지 접근 및 새로고침
- [ ] `/dashboard` 페이지 접근 및 새로고침
- [ ] API 호출 정상 작동 (`/api/*`)
- [ ] OAuth 콜백 정상 작동 (`/oauth/*`)
- [ ] WebSocket 연결 정상 작동

### 주의사항
- 백엔드 admin API는 `/api/admin/*` 경로를 통해서만 접근
- 프론트엔드 admin 페이지는 `/admin` 경로 (React Router가 처리)
- 캐시 문제 발생 시 브라우저 캐시 삭제 필요