# 픽팟 관상 분석 (face-analysis)

얼굴 사진 1장 → 공통 분석 1개 + 페르소나별 해석 3개.
미로 보드 "관상중독 — 결과 산출 구조"(v2 스펙) + v1 재현 파이프라인(MediaPipe → 버킷 → LLM 스키마 강제)을 합친 구현.

## 구조

```
사진 → MediaPipe 478 랜드마크 (롤 보정)          landmarks.py
     → 수치 특징 17 + 버킷 라벨 18               features.py / bucketize.py / config/buckets.yaml
     → 오행 점수·삼정 점수·DOMINANT(range>8)     scoring.py
     → 20유형 상수 조회 (생성 없음)              type_table.py
     → 인생그래프 수치 + 시드 SVG                scoring.py / life_graph.py
     → 페르소나 3종 LLM 해석 (스키마 강제)       persona.py / llm.py
```

## 실행

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

CLI 테스트:

```powershell
.\.venv\Scripts\python.exe tools\analyze_cli.py tests\faces\yoo_jaesuk.jpg --persona KIND,T,ROAST
```

## LLM

Ollama + EXAONE 3.5 필요. 환경변수:
- `GWANSANG_MODEL` (기본 `exaone3.5:2.4b`, 품질 우선 시 `exaone3.5:7.8b`)
- `OLLAMA_URL` (기본 `http://127.0.0.1:11434`)

## 튜닝 대상 (시작값 상태)

- `config/buckets.yaml` 임계값 — 테스트 촬영 분포 기반 조정
- `scoring.py` ZONE_BASELINE / DOMINANT_RANGE_THRESHOLD(8) — 균형형 배출 15~20% 목표
- `scoring.py` 오행 가중치 — 유형 분포 확인 후 조정
- `type_table.py` 태그라인 19개 — [초안], 미로 별첨 네이밍 표 확보 후 교체

## 면책

오락 목적 서비스. 결과에 면책 문구는 서버가 강제 첨부 (LLM에 맡기지 않음).
