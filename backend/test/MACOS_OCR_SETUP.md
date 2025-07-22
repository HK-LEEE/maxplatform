# macOS OCR 설정 가이드

macOS에서 스캔된 PDF OCR 기능을 사용하기 위한 설정 가이드입니다.

## 1. Homebrew 설치 (필수)

Homebrew가 설치되어 있지 않다면 먼저 설치합니다:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## 2. Poppler 설치

```bash
# Poppler 설치
brew install poppler

# 설치 확인
pdftoppm -h
```

설치 후 Poppler 도구들은 자동으로 PATH에 추가됩니다 (일반적으로 `/usr/local/bin/` 또는 `/opt/homebrew/bin/`).

## 3. Tesseract OCR 설치

```bash
# Tesseract 설치
brew install tesseract

# 한국어 언어 팩 설치
brew install tesseract-lang

# 설치 확인
tesseract --version
tesseract --list-langs
```

## 4. Python 의존성 설치

```bash
cd backend
pip install pytesseract==0.3.10 Pillow==10.0.1 pdf2image==1.16.3
```

## 5. 설정 확인

### 테스트 스크립트

```python
# test_ocr.py
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

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

## 6. 문제 해결

### 일반적인 오류들

1. **"Unable to get page count. Is poppler installed and in PATH?"**
   - Poppler가 설치되지 않았거나 PATH에 없음
   - `brew list poppler` 명령으로 설치 확인
   - `which pdftoppm` 명령으로 경로 확인

2. **"TesseractNotFoundError"**
   - Tesseract가 설치되지 않았거나 PATH에 없음
   - `brew list tesseract` 명령으로 설치 확인
   - `which tesseract` 명령으로 경로 확인

3. **한국어 인식이 안 됨**
   - 한국어 언어 팩이 설치되지 않음
   - `brew reinstall tesseract-lang` 실행
   - `tesseract --list-langs | grep kor` 명령으로 한국어 지원 확인

4. **M1/M2 Mac에서 경로 문제**
   - Apple Silicon Mac에서는 Homebrew가 `/opt/homebrew/`에 설치됨
   - Intel Mac에서는 `/usr/local/`에 설치됨
   - 터미널에서 `echo $PATH`로 경로 확인

### 환경 변수 확인

```bash
# PATH 확인
echo $PATH

# Poppler 위치 확인
which pdftoppm

# Tesseract 위치 확인
which tesseract
```

### Apple Silicon (M1/M2) Mac 추가 설정

```bash
# .zshrc 또는 .bash_profile에 추가
export PATH="/opt/homebrew/bin:$PATH"

# 설정 다시 로드
source ~/.zshrc  # 또는 source ~/.bash_profile
```

## 7. 성능 최적화

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

## 8. 사용 예시

```python
# 스캔된 PDF 업로드 후 자동 OCR 처리
# 1. RAG 데이터소스 페이지에서 파일 업로드
# 2. 일반 텍스트 추출 실패 시 자동으로 OCR 실행
# 3. 추출된 텍스트가 벡터 데이터베이스에 저장
# 4. 검색 및 질의응답 가능
```

## 9. 라이선스

- **Poppler**: GPL v2/v3
- **Tesseract**: Apache 2.0
- 상업적 사용 가능

설치 완료 후 백엔드 서버를 재시작하면 OCR 기능을 사용할 수 있습니다!