# 유튜브 라이브 채팅 다운로더 사용법

---

## ⚠ 실행 전 필수 설치

### 1. Python
**Python이 반드시 설치돼 있어야 합니다.**

1. https://www.python.org/downloads/ 접속
2. **Download Python 3.x.x** 버튼 클릭
3. 설치 시 **반드시 "Add Python to PATH" 체크** 후 설치

### 2. Chrome 브라우저
로그인이 필요한 영상(멤버십 등)을 수집할 경우 **Chrome 브라우저**가 설치되어 있어야 합니다.
ChromeDriver는 실행 시 자동으로 설치됩니다.

### 3. 필수 패키지 설치 (최초 1회)
```
pip install selenium webdriver-manager requests openpyxl
```

---

## 📁 파일 구성

| 파일 | 설명 |
|------|------|
| `download_chat.py` | 유튜브 라이브 채팅 다운로드 프로그램 |
| `dedup.py` | CSV 중복 제거 유틸리티 |

---

## 🚀 사용법

### 1. `download_chat.py` 실행
```
python download_chat.py
```

### 2. URL 입력
- 유튜브 영상 URL을 붙여넣고 엔터

### 3. 로그인 필요 여부 선택
```
구글 로그인이 있어야 접근 가능한 영상인가요? (멤버십 등) [y/n]:
```

**n (공개 영상):**
- 바로 채팅 수집 시작

**y (멤버십 등 로그인 필요 영상):**
- 터미널에 안내 메시지가 뜨면 `ok` 입력
- Chrome 창이 자동으로 열립니다
- Chrome 창에서 YouTube에 로그인합니다
- 로그인 완료 후 터미널 창으로 돌아와 엔터를 누릅니다
- 채팅 수집 시작

### 4. 결과 확인
- `영상ID_채팅전체.csv` — 전체 채팅 (CSV)
- `영상ID_채팅.xlsx` — 전체 채팅 (Excel, 유형별 색상 구분)

---

## 🔁 중단 후 재개

수집 도중 중단해도 체크포인트가 자동 저장됩니다. 다시 실행하면 중단된 지점부터 재개됩니다.

---

## 🧹 dedup.py — CSV 중복 제거

`download_chat.py`로 수집한 CSV에서 닉네임+메시지+금액 기준으로 중복 행을 제거합니다.

```
python dedup.py
```

> **주의:** `dedup.py` 내부의 파일명(`nL6QHnSIyuc_채팅전체.csv`)을 실제 파일명으로 수정 후 실행하세요.
