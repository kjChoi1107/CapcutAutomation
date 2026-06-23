# Shorts Auto Editor — 프로젝트 인수인계 문서

> 이 문서는 macOS에서 개발된 프로젝트를 Windows 환경에서 이어받는 Claude Code 세션을 위해 작성됐습니다.

---

## 프로젝트 목적

영상을 업로드하면 AI가 자동으로:
1. 영상 메타데이터 분석
2. Whisper로 음성 전사 (한국어 포함)
3. Claude API로 가장 임팩트 있는 20초 구간 감지
4. 해당 구간을 세로(9:16) 형식으로 클리핑
5. AI 생성 제목 + 자막을 삽입한 최종 숏츠 출력

웹 인터페이스(FastAPI + HTML)를 통해 영상을 업로드하고 단계별로 진행합니다.

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| 백엔드 | Python 3.9 + FastAPI + uvicorn |
| 영상 처리 | FFmpeg (imageio-ffmpeg 내장 바이너리) |
| 음성 전사 | OpenAI Whisper (tiny/base/small/medium/large-v3 선택 가능) |
| AI 분석 | Anthropic Claude API (claude-haiku-4-5-20251001) |
| 프론트엔드 | 순수 HTML/CSS/JS (프레임워크 없음) |

---

## 파일 구조

```
CapcutAutomation/
├── main.py                  # FastAPI 서버 (5개 API 엔드포인트)
├── pipeline/
│   ├── stage1_analyze.py    # FFmpeg으로 영상 메타데이터 추출
│   ├── stage2_transcribe.py # Whisper 음성 전사
│   ├── stage3_highlight.py  # Claude API로 최적 구간 감지
│   ├── stage4_clip.py       # FFmpeg으로 클리핑 + 9:16 변환
│   └── stage5_render.py     # 제목/자막 삽입 후 최종 렌더
├── static/
│   └── index.html           # 웹 UI (단계별 진행 인터페이스)
├── uploads/                 # 업로드된 원본 영상 저장
├── output/                  # 처리된 클립/최종 영상 저장
├── requirements.txt
├── start.sh                 # macOS/Linux 서버 시작 스크립트
└── sync_to_tmp.sh           # macOS 전용 (Windows에서는 불필요)
```

---

## API 엔드포인트

| 메서드 | 경로 | 기능 |
|--------|------|------|
| GET | `/` | 웹 UI 서빙 |
| POST | `/api/upload` | Stage 1: 영상 업로드 + 메타데이터 분석 |
| POST | `/api/transcribe/{video_id}` | Stage 2: Whisper 전사 (body: `{"model": "small"}`) |
| POST | `/api/highlight/{video_id}` | Stage 3: Claude 하이라이트 감지 (body: `{"transcript": ..., "segments": ..., "api_key": ...}`) |
| POST | `/api/clip/{video_id}` | Stage 4: 영상 클리핑 (body: `{"start": 초, "end": 초}`) |
| POST | `/api/render/{video_id}` | Stage 5: 최종 렌더 (body: `{"transcript": ..., "segments": ..., "start": 초, "api_key": ...}`) |
| GET | `/output/{filename}` | 결과 영상 파일 서빙 |
| GET | `/api/status` | 서버 상태 확인 |

---

## 현재 완성 상태

- [x] Stage 1: 영상 업로드 + 메타데이터 추출 (동작 확인)
- [x] Stage 2: Whisper 음성 전사 (동작 확인, 모델 선택 UI 포함)
- [x] Stage 3: Claude API 하이라이트 감지 (API 키 필요)
- [x] Stage 4: FFmpeg 클리핑 + 9:16 세로 변환
- [x] Stage 5: 제목 생성 + 자막 삽입 + 최종 렌더
- [x] 웹 UI: 단계별 진행 상황 표시, API 키 입력, Whisper 모델 선택

---

## macOS 전용 코드 → Windows 수정 필요 항목

### 1. `pipeline/stage2_transcribe.py` — ffmpeg 심볼릭 링크

macOS에서는 Whisper가 `ffmpeg` 명령을 찾지 못해 `/tmp/ffmpeg`에 심볼릭 링크를 만들었습니다.

```python
# 현재 macOS 코드 (stage2_transcribe.py 상단)
_ffmpeg_link = "/tmp/ffmpeg"
if not os.path.exists(_ffmpeg_link):
    os.symlink(_ffmpeg_exe, _ffmpeg_link)
if "/tmp" not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = "/tmp" + os.pathsep + os.environ.get("PATH", "")
```

**Windows(WSL) 수정안:**
```python
# WSL에서도 /tmp는 존재하므로 동일하게 작동
# 순수 Windows라면:
import tempfile
_tmp_dir = tempfile.gettempdir()  # C:\Users\...\AppData\Local\Temp
_ffmpeg_link = os.path.join(_tmp_dir, "ffmpeg")
# Windows에서 symlink는 관리자 권한 필요 → 대신 .bat 래퍼 사용
```

**가장 간단한 해결책 (WSL/Linux/Mac 공통):**
```python
# imageio_ffmpeg 바이너리를 PATH에 직접 등록하는 대신
# whisper.audio에 ffmpeg 경로를 monkey-patch
import whisper.audio as _wa
_wa.FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
# whisper 소스를 수정하지 않고 ffmpeg 명령 자체를 교체
```

### 2. `start.sh` — bash 스크립트

macOS/WSL에서는 `bash start.sh`로 실행.
순수 Windows CMD라면 아래 `start.bat`이 필요합니다:

```bat
@echo off
set PYTHONPATH=%USERPROFILE%\AppData\Roaming\Python\Python39\site-packages
cd /d %~dp0
python main.py
```

### 3. `sync_to_tmp.sh`

macOS 전용 (preview 서버 샌드박스 우회용). Windows에서는 불필요합니다.

### 4. `main.py` — 파일 경로

현재 `Path(__file__).parent`를 사용하므로 Windows에서도 자동으로 올바른 경로를 사용합니다. 수정 불필요.

---

## 서버 실행 방법

### macOS / WSL (Linux)
```bash
pip3 install -r requirements.txt
bash start.sh
# → http://localhost:8000 접속
```

### 순수 Windows (CMD)
```cmd
pip install -r requirements.txt
python main.py
```

---

## 알려진 이슈 및 해결책

### Whisper가 ffmpeg를 못 찾음
- 원인: Whisper가 시스템 PATH의 `ffmpeg` 명령을 직접 호출
- 해결: imageio_ffmpeg 바이너리로 심볼릭 링크 생성 후 PATH 등록
- 파일: `pipeline/stage2_transcribe.py` 상단

### 영상 메타데이터 파싱 실패
- 원인: ffmpeg stderr 출력 포맷이 다양함
- 해결: 정규식으로 Video: 라인에서 코덱명/해상도 각각 추출
- 파일: `pipeline/stage1_analyze.py`

### macOS Claude Code preview 서버 샌드박스
- 원인: preview_start가 `/Users/*/Documents/` 경로 접근 차단
- 해결: 소스를 `/tmp/shorts_app/`에 복사 후 실행 (sync_to_tmp.sh)
- Windows에서는 이 문제 없음 → `launch.json`을 직접 프로젝트 경로로 수정 필요

### `fetch` URL 파싱 오류
- 원인: 앱 내장 뷰어가 프록시 URL 사용 시 상대 경로 `/api/...` 불가
- 해결: `API_BASE`를 `localhost:8000` 여부로 자동 감지
- 파일: `static/index.html` 스크립트 상단

---

## Claude API 설정

- 사용 모델: `claude-haiku-4-5-20251001` (가장 저렴, 빠름)
- 사용 위치: Stage 3 (하이라이트 구간 감지), Stage 5 (제목 생성)
- API 키: 웹 UI 상단 입력란에 입력 (코드에 하드코딩 금지)
- 키 발급: https://console.anthropic.com

---

## Windows에서 이어서 작업할 때 우선순위

1. **WSL2 + Ubuntu 설치** → `wsl --install` (PowerShell 관리자)
2. **레포 클론** → `git clone https://github.com/kjChoi1107/CapcutAutomation.git`
3. **패키지 설치** → `pip3 install -r requirements.txt`
4. **ffmpeg 심볼릭 링크 문제 수정** → `stage2_transcribe.py` Windows 호환 처리
5. **launch.json 수정** → Windows 경로로 업데이트
6. **전체 파이프라인 테스트** → 샘플 영상으로 Stage 1~5 순서대로 확인

---

## 개발 히스토리 요약

1. FastAPI 웹 서버 + 5단계 파이프라인 구조 설계
2. Stage 1: FFmpeg 메타데이터 추출 구현 (ffprobe 없이 stderr 파싱)
3. Stage 2: Whisper 전사 구현 + ffmpeg PATH 문제 해결
4. Stage 3: Claude API 하이라이트 감지 (API 키 없을 때 휴리스틱 폴백)
5. Stage 4: FFmpeg 클리핑 + 9:16 세로 변환
6. Stage 5: 자막(SRT) + drawtext 제목 오버레이 렌더링
7. 웹 UI: 단계별 진행 카드, Whisper 모델 선택 (tiny~large-v3), API 키 입력
8. macOS Claude Code preview 샌드박스 우회 (sync_to_tmp.sh)
9. fetch URL API_BASE 자동 감지 (file://, 프록시, localhost 모두 대응)
10. GitHub 업로드 완료: https://github.com/kjChoi1107/CapcutAutomation
