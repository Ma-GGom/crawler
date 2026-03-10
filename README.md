# Ma-GGom Crawler

국내 마라톤 일정 수집 크롤러입니다.
운영 수집은 원문 소스를 실시간 조회해 파싱합니다.

## 폴더 구조

```text
main.py
src/
  domain/        # 순수 규칙/모델
  application/   # 유스케이스 + 포트
  adapter/       # HTTP/파서/스케줄 등 외부 기술
  bootstrap/     # 의존성 조립
tests/
```
