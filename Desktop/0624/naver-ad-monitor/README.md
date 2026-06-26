# Naver Ad Rank Monitor

네이버 파워링크 광고 순위 자동 모니터링.

## 수집 키워드
- 여행자보험 / 단기여행자보험 / 해외여행자보험 / 해외여행보험
- PC + 모바일 양 환경 수집

## 모니터링 대상
삼성화재 파워링크 광고가 **4~5위** 범위를 벗어나면 Slack 알림 발송

## 스케줄
평일(월~금) 09:00~18:00 KST, 30분 간격 자동 실행 (GitHub Actions)

## 결과 시트
https://docs.google.com/spreadsheets/d/1FGdF8KiMh8dMYgu0gmcgScpQvqv68hshbfs25QdWFtc/

- **RAW 탭**: 모든 수집 기록 누적
- **SUMMARY 탭**: 최신 스냅샷 (삼성화재 행 노란색 강조)

## 로컬 실행

```bash
cd naver-ad-monitor
pip install -r requirements.txt
playwright install chromium

export GOOGLE_SERVICE_ACCOUNT_JSON='{ ... }'
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'
python main.py
```

## GitHub Secrets 설정

저장소 Settings → Secrets → Actions:
- `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON 전체
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

## 파일 구조

```
naver-ad-monitor/
├── config.py           # 키워드·상수·UA 설정
├── scraper.py          # Playwright 광고 수집 (PC/모바일)
├── drive_uploader.py   # 광고 스크린샷 → Google Drive
├── sheets_writer.py    # Google Sheets RAW/SUMMARY 기록
├── notifier.py         # Slack 알림
├── main.py             # 오케스트레이터
└── tests/              # 단위 테스트
```
