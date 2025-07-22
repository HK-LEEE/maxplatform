# OCR 기능 설정 가이드

이 문서는 스캔된 이미지 PDF 처리를 위한 OCR 기능 설정 방법을 안내합니다.

## 필수 요구사항

### 1. Tesseract OCR 엔진 설치

#### Windows
1. **Tesseract 설치**
   ```bash
   # Chocolatey 사용 (권장)
   choco install tesseract
   
   # 또는 직접 다운로드
   # https://github.com/UB-Mannheim/tesseract/wiki 에서 Windows 설치 파일 다운로드
   ```

2. **환경 변수 설정**
   - 시스템 환경 변수에 Tesseract 경로 추가
   - 일반적으로 `C:\Program Files\Tesseract-OCR` 또는 `C:\Users\{사용자명}\AppData\Local\Programs\Tesseract-OCR`

#### macOS
```bash
# Homebrew 사용
brew install tesseract

# 한국어 언어 팩 설치
brew install tesseract-lang
```

#### Ubuntu/Debian
```bash
# Tesseract 설치
sudo apt update
sudo apt install tesseract-ocr

# 한국어 언어 팩 설치
sudo apt install tesseract-ocr-kor

# 개발 라이브러리 설치
sudo apt install libtesseract-dev
```

#### CentOS/RHEL/Fedora
```bash
# Tesseract 설치
sudo dnf install tesseract tesseract-langpack-kor

# 또는 yum 사용
sudo yum install tesseract tesseract-langpack-kor
```

### 2. Python 의존성 설치

```bash
# 백엔드 디렉토리에서 실행
cd backend
pip install -r requirements.txt

# 또는 개별 설치
pip install pytesseract==0.3.10
pip install Pillow==10.0.1
pip install pdf2image==1.16.3
```

### 3. 추가 시스템 의존성

#### Windows
- **poppler-utils**: PDF를 이미지로 변환하기 위해 필요
  ```bash
  # Chocolatey 사용
  choco install poppler
  
  # 또는 직접 다운로드
  # http://blog.alivate.com.au/poppler-windows/ 에서 다운로드
  ```

#### macOS
```bash
# poppler 설치
brew install poppler
```

#### Ubuntu/Debian
```bash
# poppler-utils 설치
sudo apt install poppler-utils
```

## 설정 확인

### 1. Tesseract 설치 확인
```bash
tesseract --version
```

### 2. 언어 팩 확인
```bash
tesseract --list-langs
```
출력에 `kor` (한국어)와 `eng` (영어)가 포함되어야 합니다.

### 3. Python에서 테스트
```python
import pytesseract
from PIL import Image
import pdf2image

# Tesseract 경로 확인 (Windows에서 필요할 수 있음)
print(pytesseract.get_tesseract_version())

# 언어 확인
print(pytesseract.get_languages())
```

## 환경 변수 설정 (선택사항)

### Windows
```bash
# 시스템 환경 변수 또는 .env 파일에 추가
TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
```

### Linux/macOS
```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# 또는 .env 파일에 추가
TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
```

## 성능 최적화

### 1. OCR 설정 조정
`backend/app/llmops/rag_service.py`에서 OCR 설정을 조정할 수 있습니다:

```python
# OCR 수행 시 사용되는 설정
page_text = pytesseract.image_to_string(
    processed_image, 
    lang='kor+eng',  # 언어 설정
    config='--psm 3 --oem 3'  # 페이지 분할 모드와 OCR 엔진 모드
)
```

### 2. 이미지 전처리 개선
더 나은 OCR 결과를 위해 이미지 전처리를 조정할 수 있습니다:

```python
def _preprocess_image_for_ocr(self, image):
    # 대비 조정
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)  # 값 조정 가능
    
    # 선명도 조정
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)  # 값 조정 가능
    
    return image
```

## 문제 해결

### 1. "TesseractNotFoundError" 오류
- Tesseract가 설치되지 않았거나 PATH에 없음
- Windows에서는 pytesseract 설정 필요:
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

### 2. "FileNotFoundError: [Errno 2] No such file or directory: 'pdftoppm'"
- poppler-utils가 설치되지 않음
- 위의 설치 가이드 참조

### 3. 한국어 인식이 안 됨
- 한국어 언어 팩이 설치되지 않음
- `tesseract --list-langs`로 확인 후 언어 팩 설치

### 4. OCR 성능이 낮음
- 이미지 품질이 낮거나 해상도가 부족
- DPI 설정 조정: `convert_from_bytes(content, dpi=300)`에서 DPI 값 증가
- 이미지 전처리 파라미터 조정

## 지원되는 파일 형식

- **PDF**: 텍스트 PDF 및 스캔된 이미지 PDF
- **이미지**: PNG, JPEG, TIFF, BMP 등 (PIL에서 지원하는 모든 형식)

## 사용 예시

1. **일반 텍스트 PDF**: 기존 방식으로 텍스트 추출
2. **스캔된 PDF**: 자동으로 OCR 처리
3. **이미지 파일**: 직접 OCR 처리 (향후 지원 예정)

## 로그 확인

OCR 처리 과정은 로그로 확인할 수 있습니다:

```
INFO:app.llmops.rag_service:Starting OCR extraction from PDF
INFO:app.llmops.rag_service:Converted PDF to 3 images
INFO:app.llmops.rag_service:OCR extracted 1250 characters from page 1
INFO:app.llmops.rag_service:OCR extraction completed: 3750 total characters
```

## 라이선스 및 주의사항

- Tesseract는 Apache 2.0 라이선스
- 상업적 사용 가능
- OCR 정확도는 원본 이미지 품질에 따라 달라짐
- 대용량 PDF 처리 시 메모리 사용량 주의 