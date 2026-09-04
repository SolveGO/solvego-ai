
# SolveGO AI Server

SolveGO의 바둑 문제 분석을 담당하는 AI 서버입니다.

FastAPI를 통해 요청을 받고, KataGo Analysis Engine을 호출하여 추천 수와 사용자가 선택한 수의 품질을 분석합니다.



## Architecture

```text
React Frontend
      ↓
Spring Boot Backend
      ↓ HTTP
FastAPI AI Server
      ↓ stdin / stdout
KataGo
      ↓
Neural Network Model
````

AI 서버는 브라우저에서 직접 접근하지 않고, Spring Boot Backend를 통해서만 호출됩니다.



## Tech Stack

* Python 3.12
* FastAPI
* Uvicorn
* KataGo 1.18.2
* Docker
* AWS EC2
* Amazon ECR



## Features

### 1. AI Move Recommendation

현재 바둑판 상태를 기반으로 KataGo가 가장 좋은 수를 추천합니다.

```http
POST /recommend
```

### 2. Selected Move Analysis

사용자가 선택한 수와 KataGo의 최선 수를 비교하여 수의 품질을 분석합니다.

```http
POST /analyze
```



# API

## Health Check

```http
GET /
```

### Response

```json
{
  "status": "ok"
}
```



## Recommend Move

```http
POST /recommend
```

현재 바둑판 상태에서 KataGo가 추천하는 최선의 수를 반환합니다.

### Request

```json
{
  "blackStones": [
    {
      "x": 3,
      "y": 3
    }
  ],
  "whiteStones": [
    {
      "x": 15,
      "y": 3
    }
  ],
  "nextPlayer": "BLACK"
}
```

### Response

```json
{
  "bestMove": {
    "x": 16,
    "y": 2
  },
  "bestWinRate": 0.4885
}
```



## Analyze Selected Move

```http
POST /analyze
```

현재 바둑판에서 사용자가 선택한 수와 KataGo의 최선 수를 비교합니다.

### Request

```json
{
  "blackStones": [
    {
      "x": 3,
      "y": 3
    }
  ],
  "whiteStones": [
    {
      "x": 15,
      "y": 3
    }
  ],
  "nextPlayer": "BLACK",
  "selectedPosition": {
    "x": 10,
    "y": 10
  }
}
```

### Response

```json
{
  "bestMove": {
    "x": 16,
    "y": 2
  },
  "selectedMove": {
    "x": 10,
    "y": 10
  },
  "bestWinRate": 0.4865,
  "selectedWinRate": 0.4120,
  "winRateLoss": 0.0745
}
```

### Fields

| Field             | Description       |
| ----------------- | ----------------- |
| `bestMove`        | KataGo가 추천한 최선의 수 |
| `selectedMove`    | 사용자가 선택한 수        |
| `bestWinRate`     | 최선 수의 승률          |
| `selectedWinRate` | 사용자가 선택한 수의 승률    |
| `winRateLoss`     | 최선 수 대비 승률 감소량    |



# Coordinate System

SolveGO에서는 프론트엔드와 백엔드 모두 다음 좌표계를 사용합니다.

```text
(0, 0) ─────────────→ x
  |
  |
  |
  ↓
  y
```

* 좌측 상단: `(0, 0)`
* 우측 하단: `(18, 18)`
* Board Size: `19 x 19`

KataGo는 `D4`, `Q16`과 같은 바둑 좌표를 사용하기 때문에 AI 서버 내부에서 좌표 변환을 수행합니다.

```text
SolveGO
{x: 3, y: 15}

        ↓

KataGo
D4
```

KataGo의 좌표 표현은 AI 서버 내부 구현에만 사용되며 API에서는 `{x, y}` 형식을 사용합니다.



# Project Structure

```text
solvego_ai/
├── main.py
├── requirements.txt
├── Dockerfile
│
├── app/
│   ├── config.py
│   │
│   ├── api/
│   │   └── analysis.py
│   │
│   ├── schemas/
│   │   └── analysis.py
│   │
│   ├── services/
│   │   └── analysis_service.py
│   │
│   └── katago/
│       ├── client.py
│       └── coordinate.py
│
├── katago/
│   └── analysis.cfg
│
└── models/
    └── model.bin.gz
```



# KataGo Communication

FastAPI 서버는 KataGo Analysis Engine을 subprocess로 실행합니다.

KataGo와의 통신은 stdin/stdout을 사용합니다.

```text
FastAPI
   ↓ JSON Query
stdin
   ↓
KataGo
   ↓ JSON Result
stdout
   ↓
FastAPI
```

KataGo 프로세스를 요청마다 새로 실행하지 않고 하나의 프로세스를 유지하여 재사용합니다.



# Concurrent Request Handling

여러 HTTP 요청이 동시에 들어올 수 있기 때문에 KataGo 요청마다 고유한 ID를 부여합니다.

```text
Request A
   ↓
UUID A
   ↓
KataGo

Request B
   ↓
UUID B
   ↓
KataGo
```

각 요청은 전용 Queue를 가지고 있으며, KataGo stdout을 읽는 별도의 reader thread가 결과의 ID를 확인하여 해당 요청 Queue에 전달합니다.

```text
                     ┌─ Queue A → Request A
KataGo stdout
      ↓
 Reader Thread ──────┼─ Queue B → Request B
                     │
                     └─ Queue C → Request C
```

이를 통해 여러 요청이 동시에 발생해도 각 요청이 자신의 분석 결과를 받을 수 있도록 구성했습니다.



# Configuration

AI 서버는 다음 환경변수를 사용합니다.

```bash
KATAGO_MODEL_PATH=/models/model.bin.gz
```

KataGo 실행 파일과 설정 파일의 경로는 애플리케이션 설정을 통해 관리됩니다.



# Docker

## Build

AWS EC2의 x86_64 환경에 맞춰 `linux/amd64` 이미지로 빌드합니다.

```bash
docker build \
  --platform linux/amd64 \
  -t solvego-ai .
```



## Run

KataGo 모델 파일은 Docker 이미지에 포함하지 않고 EC2에 저장한 뒤 volume mount하여 사용합니다.

```bash
docker run -d \
  --name solvego-ai \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /home/ubuntu/solvego-ai/models/model.bin.gz:/models/model.bin.gz:ro \
  -e KATAGO_MODEL_PATH=/models/model.bin.gz \
  solvego-ai
```



# AWS Deployment

AI 서버는 별도의 EC2 인스턴스에 배포되어 있습니다.

```text
Spring Backend EC2
        ↓
   Private Network
        ↓
AI Server EC2
        ↓
     KataGo
```

Spring Backend와 AI Server는 AWS VPC 내부의 Private IP를 통해 통신합니다.

AI Server의 `8000` 포트는 Backend Server의 Security Group에서만 접근할 수 있도록 제한합니다.

Docker 이미지는 Amazon ECR을 통해 배포합니다.

```text
Local
  ↓ docker push
Amazon ECR
  ↓ docker pull
AI EC2
```



# AI Policy

SolveGO에서 AI는 문제의 정답을 결정하지 않습니다.

문제의 공식 정답은 문제 작성자가 지정한 `answerPosition`을 기준으로 판단합니다.

```text
Author Answer
     ↓
Canonical Correct / Incorrect
```

KataGo는 추가적인 분석 정보를 제공하는 역할만 수행합니다.

```text
User Selected Move
        ↓
     KataGo
        ↓
Move Quality Analysis
```

따라서 다음과 같은 상황이 가능합니다.

```text
작성자 정답: D4
사용자 선택: Q16

SolveGO 판정
→ Incorrect

AI 평가
→ Good Move
```

즉, AI 분석 결과와 문제 정답 판정은 서로 독립적으로 처리합니다.



# Future Improvements

* AI 분석 결과 기반 수의 품질 등급화
* 실제 문제 데이터를 기반으로 `winRateLoss` 임계값 조정
* AI 요청 timeout 및 fallback 처리
* 분석 결과 모니터링
* AI 서버 CI/CD 자동화


