# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 프로젝트에 대해

퍼포먼스 마케팅 데이터 분석 워크스페이스.
매일 채널 리포트 + 앱스플라이어 데이터를 업로드 → 조인 → 전처리 → 인사이트 추출.
주 결과물: Streamlit 대시보드(`dashboard.py`), 분석 리포트, 소재 성과 인사이트.

---

## 1. 데이터 구조 & 파일 관리 규칙

### 폴더 구조
```
data/
├── channel/      ← YYYY-MM-DD_channel.parquet    (채널 리포트 원본)
└── appsflyer/    ← YYYY-MM-DD_appsflyer.parquet  (MMP 어트리뷰션 원본)
```

### 파일 네이밍 규칙
- 반드시 `YYYY-MM-DD_channel.parquet` / `YYYY-MM-DD_appsflyer.parquet` 형식
- 날짜는 데이터 기준일 (업로드일 아님)
- CSV → Parquet 변환 후 저장 (성능·용량 이유)

### CSV → Parquet 변환
```python
import pandas as pd, pathlib
df = pd.read_csv("YYYY-MM-DD_channel.csv")
df.to_parquet("data/channel/YYYY-MM-DD_channel.parquet", index=False)
```

---

## 2. 채널 ↔ 앱스플라이어 매핑 테이블

조인 시 채널명이 다르므로 아래 매핑을 항상 참조할 것.

| 채널 리포트 (`채널`) | AF (`미디어소스`) | 채널분류 |
|---------------------|-------------------|---------|
| 구글 | googleadwords_int | 외부 |
| 메타 | Facebook Ads | 외부 |
| 네이버 | naver_search | 자체 |

### 조인 키
```
날짜(일) + 캠페인 + 그룹 + 소재
```
- 채널 리포트에는 `채널분류`(외부/자체) 컬럼이 있고 AF에는 없음
- 조인 후 충돌 컬럼 suffix: `_ch` (채널), `_af` (앱스플라이어)

---

## 3. 소재 네이밍 컨벤션

### 파싱 규칙
```
{소재유형}_{메시지카테고리}_{시즌}_{AB버전}_{버전넘버}

예시: VID_플러스멤버십_겨울_A_v1
     IMG_적립혜택_겨울_v2        ← AB 없는 경우
     TXT_할인쿠폰_겨울_A_v1
```

### 소재 유형 (포맷)
| 코드 | 설명 | 채널 |
|------|------|------|
| VID | 영상 소재 | 구글, 메타 |
| IMG | 이미지 소재 | 구글, 메타, 네이버 |
| CRS | 캐러셀 소재 | 구글, 메타 |
| TXT | 텍스트 소재 | 네이버 검색 |

### AB 테스트 표기
- `A`, `B` : AB 테스트 버전 (같은 메시지, 다른 크리에이티브)
- `v1`, `v2` : 버전업 (메시지 또는 소재 자체 개선)
- AB 없이 `v2`만 있으면 단일 소재 버전업

---

## 4. 캠페인 목적 분류

### 캠페인명 파싱 규칙
```
{채널코드}_CMP_{번호}_{목적}

예시: GGL_CMP_01_플러스가입
     META_CMP_03_재구매
     NVR_CMP_02_일반KW
```

### 목적별 분류
| 캠페인목적 | 설명 | 주요 타겟 그룹 |
|-----------|------|--------------|
| 플러스가입 | 멤버십 신규 가입 유도 | 논타겟, 유사타겟 |
| 첫구매 | 신규 유저 첫 구매 | 논타겟, 유사타겟 |
| 리타겟팅 | 방문 이력 재유도 | 리마케팅 |
| 신규유저 | 메타 신규 획득 | 논타겟 |
| 룩얼라이크 | 유사 오디언스 확장 | 유사타겟 |
| 재구매 | 기존 고객 재구매 | VIP, 윈백 |
| 브랜드KW | 브랜드 검색어 | 논타겟 |
| 일반KW | 일반 검색어 | 논타겟 |

### 채널 코드
| 코드 | 채널 |
|------|------|
| GGL | 구글 |
| META | 메타 |
| NVR | 네이버 |

---

## 5. 지표 정의 & 우선순위

### 지표별 기준 소스
| 지표 | 기준 소스 | 이유 |
|------|----------|------|
| 비용 | 채널 리포트 (`_ch`) | 실제 과금 기준 |
| 노출 | 채널 리포트 (`_ch`) | 채널이 정확 |
| 클릭 | 채널 리포트 (`_ch`) | 채널이 정확 |
| 회원가입 | 앱스플라이어 (`_af`) | MMP 어트리뷰션 기준 |
| 구매 | 앱스플라이어 (`_af`) | MMP 어트리뷰션 기준 |
| 구매매출 | 앱스플라이어 (`_af`) | MMP 어트리뷰션 기준 |

### 파생 지표 계산식
```python
ROAS  = 구매매출_af / 비용_ch
CPA   = 비용_ch / 구매_af
CTR   = 클릭_ch / 노출_ch * 100      # %
CVR   = 구매_af / 클릭_ch * 100      # %
CPM   = 비용_ch / 노출_ch * 1000
CPC   = 비용_ch / 클릭_ch
```

### KPI 기준값 (목표치) — 직접 수정 필요
```
# TODO: 아래 값은 예시입니다. 실제 목표값으로 교체하세요.
목표 ROAS:  구글 8x  / 메타 6x  / 네이버 20x
목표 CPA:   구글 6,000원 / 메타 8,000원 / 네이버 3,000원
CTR 경고선: 0.5% 미만 시 소재 피로 의심
소재 운영 기간: 14일 이상 시 피로도 체크
```

---

## 6. 분석 워크플로우

### 매일 루틴
```
1. 채널 CSV + AF CSV 업로드
2. CSV → Parquet 변환 후 data/ 폴더 배치
3. 대시보드 새로고침 버튼 → 데이터 반영 확인
4. 이상치 체크 (전일 대비 비용/성과 급변 여부)
5. 인사이트 도출
```

### 분석 요청 시 기본 포함 항목
- 기간 및 비교 기간 명시
- 채널별 / 캠페인별 / 소재유형별 분류 기본 적용
- 수치는 반드시 기준 소스(채널/AF) 명시
- ROAS·CPA는 목표 대비 달성률로 표현

### 자주 쓰는 분석 패턴
```
소재 피로도:   동일 소재 n일 운영 시 CTR/CVR 추이
AB 성과 비교:  동일 캠페인 내 A vs B 소재 통계적 유의성
채널 기여:     AF 기준 채널별 구매 기여 비율
예산 효율:     ROAS 하위 20% 소재/그룹 플래그
```

---

## 7. Python 환경

```
Python 3.11.9  →  C:\Users\MADUP\AppData\Local\Programs\Python\Python311\python.exe
pip            →  위 경로의 python.exe -m pip
streamlit      →  C:\Users\MADUP\AppData\Local\Programs\Python\Python311\Scripts\streamlit.exe
```

Bash 도구에서 실행 시:
```bash
powershell -NoProfile -Command "& 'C:\Users\MADUP\AppData\Local\Programs\Python\Python311\python.exe' ..."
```

주요 설치 패키지: `pandas`, `pyarrow`, `streamlit`, `altair`

---

## 8. 대시보드

```
dashboard.py   — Streamlit 앱 (localhost:8501)
```

실행:
```bash
powershell -NoProfile -Command "Start-Process 'C:\Users\MADUP\AppData\Local\Programs\Python\Python311\Scripts\streamlit.exe' -ArgumentList 'run','C:\Users\MADUP\Desktop\0624\dashboard.py'"
```

---

## 9. 기타 도구 & 명령어

### PPTX 리스타일링
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\MADUP\Desktop\0624\restyle_pptx.ps1"
```

### claude.exe 경로
```
C:\Users\MADUP\AppData\Roaming\Claude\claude-code\2.1.181\claude.exe
```

### 설치된 플러그인
| 플러그인 | 용도 |
|---------|------|
| `insane-search@gptaku-plugins` v0.8.2 | 네이버·X·Reddit WAF 우회 수집 |
| `browser-harness@browser-harness` v0.1.0 | CDP 기반 브라우저 제어 |
| `playwright@claude-plugins-official` | Playwright MCP |
| `superpowers@claude-plugins-official` v5.1.0 | 스킬·에이전트 시스템 |

### PowerShell 호출 규칙
- Bash 도구에서는 항상 `powershell -NoProfile -Command "..."` 형태
- 한글 경로 포함 시 따옴표 주의

### 글로벌 설정 우선순위
글로벌 CLAUDE.md(`~/.claude/CLAUDE.md`) 충돌 시 전역 설정 우선

## 핵심 도구 및 명령어

### PPTX 리스타일링
```powershell
# PowerShell에서 실행 (Bash 도구 아님)
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\MADUP\Desktop\0624\restyle_pptx.ps1"
```
- 입력: `C:\Users\MADUP\Downloads\` 안의 원본 PPTX
- 출력: `storyboard_v2_clean.pptx`
- 내부적으로 `pptxgenjs`(Node.js)와 PowerShell ZIP 압축 해제 조합

### Node.js 의존성
```bash
npm install   # pptxgenjs 설치
```

## Claude Code 글로벌 설정 (이 PC 기준)

### claude.exe 경로
```
C:\Users\MADUP\AppData\Roaming\Claude\claude-code\2.1.181\claude.exe
```
Bash/PowerShell에서 `claude` 명령이 PATH에 없을 때 위 전체 경로로 직접 호출.

### 설치된 플러그인 (user scope)
| 플러그인 | 용도 |
|---------|------|
| `insane-search@gptaku-plugins` v0.8.2 | 네이버·X·Reddit 등 WAF 우회 웹 수집 |
| `browser-harness@browser-harness` v0.1.0 | CDP 기반 브라우저 직접 제어 |
| `playwright@claude-plugins-official` | Playwright MCP (브라우저 자동화) |
| `superpowers@claude-plugins-official` v5.1.0 | 스킬·에이전트 시스템 |
| `vercel@claude-plugins-official` v0.43.0 | Vercel 배포 관련 |

### MCP 서버
- `playwright`: `npx @playwright/mcp@latest` — 로컬 프로젝트 설정 (`~/.claude.json`)

## 네이버 쇼핑 데이터 수집 패턴

`search.shopping.naver.com`은 418 차단, `msearch.shopping.naver.com`도 불안정.  
**동작하는 경로**: `search.naver.com/search.naver?where=shop&query=<키워드>`

```javascript
// Playwright MCP로 상품 추출하는 패턴
const products = [];
document.querySelectorAll('li, article').forEach(el => {
  const text = el.innerText.trim();
  const priceMatch = text.match(/([\d,]+)원/);
  if (!priceMatch || text.length < 30) return;
  // ... 이미지 alt, 브랜드명, 별점 추출
});
```

## Python 환경

**Python 미설치** — `python3`, `pip` 명령 사용 불가.  
insane-search engine (`python3 -m engine`) 직접 실행 불가 → Playwright MCP로 대체.

## 파일 구조

```
0624/
├── restyle_pptx.ps1        # PPTX 리스타일 스크립트 (PowerShell, 107줄)
├── storyboard_v2_clean.pptx # 출력된 리스타일 PPTX
├── 선글라스_검색결과.csv    # 네이버 쇼핑 수집 결과 예시
├── package.json            # pptxgenjs 의존성
└── node_modules/
```

## 작업 시 주의사항

- PowerShell 명령은 반드시 `powershell -NoProfile -Command "..."` 형태로 호출 (Bash 도구에서)
- `claude` CLI 호출 시 전체 경로 사용: `C:\Users\MADUP\AppData\Roaming\Claude\claude-code\2.1.181\claude.exe`
- 글로벌 CLAUDE.md(`~/.claude/CLAUDE.md`)에 마케터 워크플로우 전체 가이드 있음 — 이 파일과 충돌 시 전역 설정 우선
