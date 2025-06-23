# Windows OCR 설정 가이드

Windows에서 스캔된 PDF OCR 기능을 사용하기 위한 설정 가이드입니다.

## 1. Poppler 설치 (필수)

### 방법 1: 직접 다운로드 (권장)

1. **Poppler 다운로드**
   - https://github.com/oschwartz10612/poppler-windows/releases/ 에서 최신 버전 다운로드
   - `poppler-xx.xx.x_x64.7z` 파일 다운로드

2. **압축 해제**
   ```
   C:\poppler\
   ├── bin\
   ├── include\
   ├── lib\
   └── share\
   ```

3. **환경 변수 설정**
   - 시스템 환경 변수 편집
   - Path에 `C:\poppler\bin` 추가

4. **설치 확인**
   ```cmd
   pdftoppm -h
   ```

### 방법 2: Chocolatey 사용

```cmd
# Chocolatey 설치 (관리자 권한 필요)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Poppler 설치
choco install poppler
```

### 방법 3: Conda 사용

```cmd
conda install -c conda-forge poppler
```

## 2. Tesseract OCR 설치

### 직접 설치

1. **Tesseract 다운로드**
   - https://github.com/UB-Mannheim/tesseract/wiki 에서 Windows 설치 파일 다운로드
   - `tesseract-ocr-w64-setup-v5.x.x.exe` 실행

2. **설치 시 주의사항**
   - "Additional language data" 선택 시 Korean 체크
   - 설치 경로 기억 (보통 `C:\Program Files\Tesseract-OCR`)

3. **환경 변수 설정**
   - Path에 `C:\Program Files\Tesseract-OCR` 추가

4. **설치 확인**
   ```cmd
   tesseract --version
   tesseract --list-langs
   ```

## 3. Python 의존성 설치

```cmd
cd backend
pip install pytesseract==0.3.10 Pillow==10.0.1 pdf2image==1.16.3
```

## 4. 설정 확인

### 테스트 스크립트

```python
# test_ocr.py
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Tesseract 경로 설정 (필요한 경우)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Tesseract version:", pytesseract.get_tesseract_version())
print("Available languages:", pytesseract.get_languages())

# 간단한 텍스트 인식 테스트
try:
    # 테스트 이미지 생성
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (300, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Hello World 안녕하세요", fill='black')
    
    # OCR 테스트
    text = pytesseract.image_to_string(img, lang='kor+eng')
    print("OCR Result:", text)
    print("✅ OCR 설정 완료!")
    
except Exception as e:
    print("❌ OCR 설정 오류:", str(e))
```

## 5. 문제 해결

### 일반적인 오류들

1. **"Unable to get page count. Is poppler installed and in PATH?"**
   - Poppler가 설치되지 않았거나 PATH에 없음
   - 위의 Poppler 설치 과정 다시 확인

2. **"TesseractNotFoundError"**
   - Tesseract가 설치되지 않았거나 PATH에 없음
   - 수동으로 경로 설정:
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

3. **한국어 인식이 안 됨**
   - 한국어 언어 팩이 설치되지 않음
   - Tesseract 재설치 시 Korean 언어 팩 선택

4. **"FileNotFoundError: [WinError 2]"**
   - 환경 변수 PATH 설정 확인
   - 시스템 재시작 후 다시 시도

### 환경 변수 확인

```cmd
echo %PATH%
where pdftoppm
where tesseract
```

## 6. 성능 최적화

### 이미지 품질 설정

```python
# DPI 조정 (높을수록 정확하지만 느림)
images = convert_from_bytes(content, dpi=300)  # 기본값
images = convert_from_bytes(content, dpi=150)  # 빠른 처리
images = convert_from_bytes(content, dpi=600)  # 고품질
```

### OCR 설정 최적화

```python
# 페이지 분할 모드 (PSM) 조정
config = '--psm 3 --oem 3'  # 기본값 (자동 페이지 분할)
config = '--psm 6 --oem 3'  # 단일 텍스트 블록
config = '--psm 1 --oem 3'  # 자동 방향 및 스크립트 감지
```

## 7. 사용 예시

```python
# 스캔된 PDF 업로드 후 자동 OCR 처리
# 1. RAG 데이터소스 페이지에서 파일 업로드
# 2. 일반 텍스트 추출 실패 시 자동으로 OCR 실행
# 3. 추출된 텍스트가 벡터 데이터베이스에 저장
# 4. 검색 및 질의응답 가능
```

## 8. 라이선스

- **Poppler**: GPL v2/v3
- **Tesseract**: Apache 2.0
- 상업적 사용 가능

설치 완료 후 백엔드 서버를 재시작하면 OCR 기능을 사용할 수 있습니다! 