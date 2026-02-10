# LangGraph HITL 승인 시스템 & 제조 QA 적용

> 🎯 **LangGraph의 Human-in-the-Loop 패턴을 학습하고 제조/에너지 현장 품질 관리에 적용한 프로젝트**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-green)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 목차

- [개요](#-개요)
- [주요 기능](#-주요-기능)
- [설치 및 실행](#-설치-및-실행)
- [사용 예시](#-사용-예시)
- [핵심 개념](#-핵심-개념)
- [실전 적용 시나리오](#-실전-적용-시나리오)
- [기술 스택](#-기술-스택)
- [학습 내용](#-학습-내용)
- [다음 단계](#-다음-단계)
- [참고 자료](#-참고-자료)

---

## 🎯 개요

이 프로젝트는 **LangGraph의 HITL(Human-in-the-Loop) 패턴**을 학습하고, 이를 **제조/에너지 현장의 품질 관리(QA) 시스템**에 적용한 실습 코드입니다.

### 왜 HITL인가?

현대 제조 현장에서는 AI가 빠르게 데이터를 분석하지만, **중요한 결정은 여전히 인간 전문가의 판단이 필요**합니다. 특히:

- 🏭 **가동 중지 결정**: AI가 과열을 감지했어도, 전문가가 최종 승인
- ⚠️ **안전 프로토콜**: 위험한 조치는 반드시 인간 검토 필요
- 🔧 **유지보수 스케줄링**: AI 권장 조치를 전문가가 현장 상황에 맞게 조정

### 프로젝트 목표

    1. ✅ LangGraph의 `interrupt()` 및 `Command` 패턴 이해
    2. ✅ 기본 승인 워크플로우 구현 (`lg_approval.py`)
    3. ✅ 실제 제조 현장 시나리오에 적용 (`lg_app_qa.py`)
    4. ✅ 동기/비동기 실행 모드 비교 학습

---

## 🚀 주요 기능

### 1️⃣ 기본 승인 시스템 (`lg_approval.py`)

```python
# 승인/거부에 따른 조건부 라우팅
approved = interrupt({"question": "이 작업을 승인하시겠습니까?"})

if approved:
    return Command(goto="do", update={"status": "approved"})
else:
    return Command(goto="cancel", update={"status": "rejected"})
```

**특징:**
- 💡 `interrupt()`를 통한 사용자 입력 대기
- 🔀 `Command`로 동적 라우팅 (승인 → do, 거부 → cancel)
- ⚡ 동기/비동기 실행 모드 지원
- 🐛 비동기 스트리밍 디버깅 포함

### 2️⃣ 제조 QA 시스템 (`lg_app_qa.py`)

```python
# 위험도에 따른 조건부 승인
if risk_level == "LOW":
    return Command(goto="execute_action", update={"human_approval": True})
else:
    # HIGH/CRITICAL은 전문가 검토 필수
    approval_data = interrupt({
        "type": "expert_approval_required",
        "risk_level": risk_level,
        "sensor_data": sensor_data
    })
```

**특징:**
- 🤖 **AI 센서 분석**: 온도/압력/진동/유량/전력 모니터링
- 📊 **위험도 자동 분류**: LOW/HIGH/CRITICAL
- 👤 **조건부 전문가 검토**: 
  - LOW → 자동 승인 (전문가 개입 불필요)
  - HIGH/CRITICAL → 전문가 검토 필수
- ✏️ **전문가 Override**: AI가 "긴급 중지"를 권장해도 전문가가 "부하 감소"로 변경 가능
- 🎬 **4가지 시나리오**: 정상/과열/압력급증/진동이상
- 📝 **완전한 감사 추적**: 타임스탬프, 전문가 의견, 실행 조치 기록

---

## 🛠 설치 및 실행

### 1. 환경 설정

```bash
# Python 3.10 이상 필요
python --version

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install langgraph langchain-core typing-extensions
```

### 2. 기본 승인 시스템 실행

```bash
python lg_approval.py
```

**대화형 프롬프트:**
```
실행 모드를 선택하세요:
1. 비동기 스트리밍 방식 (권장)
2. 동기 방식 (간단)

선택 (1 or 2): 2

=== 첫 번째 실행 ===
새로운 세션 ID: abc123...

질문: 이 작업을 승인하시겠습니까?
작업: 서버 재부팅

승인하시겠습니까? (yes/no): yes

=== 'True'로 재개 ===
--- 작업 실행: 서버 재부팅 ---
최종 상태: completed
```

### 3. 제조 QA 시스템 실행

    ```bash
    python lg_app_qa.py
    ```

**대화형 프롬프트:**
```
🏭 제조/에너지 현장 HITL 모니터링 시스템

    시나리오를 선택하세요:
    1. normal - 정상 작동
    2. overheating - 과열 감지
    3. pressure_spike - 압력 급증
    4. vibration_anomaly - 진동 이상

  선택 (1-4): 2
  
  실행 모드:
    1. 동기 방식 (권장)
    2. 비동기 방식

  선택 (1-2): 1

    ############################################################
    🏭 설비 모니터링 시작
    ############################################################
    설비 ID: PLANT-A1B2C3D4
    시나리오: overheating
    ############################################################
    
    🤖 AI 분석 완료 - 2025-02-10 14:30:25
    ============================================================
    위험도: CRITICAL
    분석 결과:
    🚨 긴급 상황 감지!
    온도 위험: 95.8°C (임계값: 90.0°C)
    권장 조치: IMMEDIATE_SHUTDOWN
    ============================================================

    ⏸️  전문가 검토 대기 중...

    승인하시겠습니까? (yes/no): yes
    의견을 입력하세요: 현장 확인 완료, 즉시 가동 중지 승인
    
    ⚙️ 조치 실행: IMMEDIATE_SHUTDOWN
    🛑 긴급 가동 중지 실행
    전문가 의견: 현장 확인 완료, 즉시 가동 중지 승인
    
    ############################################################
    📋 최종 리포트
    ############################################################
    설비 ID: PLANT-A1B2C3D4
    위험도: CRITICAL
    전문가 승인: ✅ 예
    전문가 의견: 현장 확인 완료, 즉시 가동 중지 승인
    실행된 조치: IMMEDIATE_SHUTDOWN
    타임스탬프: 2025-02-10T14:30:25.123456
    ############################################################
    ```

---

## 💡 사용 예시

### 예시 1: 정상 작동 (자동 승인)

    ```bash
    # 시나리오 1 선택
    선택 (1-4): 1

    🤖 AI 분석: 온도 72.5°C → 위험도 LOW
    ✅ 위험도 낮음 - 자동 승인
    👁️ 모니터링 계속
    전문가 의견: 자동 승인 (정상 범위)
    
    ✅ 정상 작동 - 전문가 개입 불필요
    ```

### 예시 2: 과열 감지 (전문가 승인)

    ```bash
    # 시나리오 2 선택
    선택 (1-4): 2
    
    🤖 AI 분석: 온도 95.8°C → 위험도 CRITICAL
    ⏸️  전문가 검토 대기 중...
    
    승인하시겠습니까? (yes/no): yes
    의견: 긴급 가동 중지 승인
    
    ⚙️ 조치 실행: IMMEDIATE_SHUTDOWN
    🛑 긴급 가동 중지 실행
    ```

### 예시 3: 전문가 Override

    ```bash
    # 시나리오 2 선택
    선택 (1-4): 2

    🤖 AI 분석: 온도 95.8°C → 위험도 CRITICAL
    AI 권장 조치: IMMEDIATE_SHUTDOWN
    
    승인하시겠습니까? (yes/no): yes
    의견: 부하만 감소하여 점검
    조치를 수정하시겠습니까? (yes/no): yes
    
    가능한 조치:
    1. IMMEDIATE_SHUTDOWN
    2. CONTROLLED_SHUTDOWN
    3. REDUCE_LOAD
    4. MAINTENANCE_ALERT
    5. CONTINUE_MONITORING

    선택: 3

    ⚠️ 전문가가 AI 권장 조치를 수정했습니다
    원래 권장 조치: IMMEDIATE_SHUTDOWN
    수정된 조치: REDUCE_LOAD
    
    ⚙️ 조치 실행: REDUCE_LOAD
    📉 부하 감소 실행
    ```

---

## 🧠 핵심 개념

### 1. `interrupt()` vs `interrupt_before`

    | 특징 | `interrupt()` | `interrupt_before` |
    |------|---------------|-------------------|
    | 위치 | 노드 내부 | 컴파일 시 설정 |
    | 조건부 실행 | ✅ 가능 | ❌ 불가능 |
    | 데이터 전달 | ✅ 가능 | ❌ 제한적 |
    | 사용 난이도 | ⚠️ 중급 | ✅ 쉬움 |

**`interrupt()` 예시 (본 프로젝트):**
```python
def expert_approval_node(state):
    if state["risk_level"] == "LOW":
        return Command(goto="execute", update={...})  # 자동 승인
    
    # HIGH/CRITICAL만 interrupt
    approval = interrupt({"question": "승인?"})
    return Command(goto="execute", update={...})
```

**`interrupt_before` 예시:**
```python
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["approval_node"]  # 항상 이 노드 전에 멈춤
)
```

### 2. `Command`를 통한 동적 라우팅

```python
def approval_node(state):
    decision = interrupt({"question": "승인?"})
    
    # 조건에 따라 다른 노드로 이동
    if decision["approved"]:
        return Command(goto="execute", update={"status": "approved"})
    elif decision.get("override"):
        return Command(goto="override", update={"action": decision["override"]})
    else:
        return Command(goto="cancel", update={"status": "rejected"})
```

### 3. 조건부 HITL 패턴

```python
# 위험도가 낮으면 자동 승인, 높으면 전문가 검토
if risk_level == "LOW":
    return auto_approve()
else:
    return request_expert_approval()
```

---

## 🏭 실전 적용 시나리오

### 시나리오 1: 제조 라인 가동 중지

    **상황:**
    - AI가 설비 과열 감지 (95.8°C)
    - 정상 범위: 70-80°C
    - 임계값: 90°C
    
    **워크플로우:**
    1. 🤖 AI 센서 분석 → CRITICAL 위험도 감지
    2. ⏸️ 그래프 중단, 전문가 알림 전송
    3. 👤 전문가 현장 확인
    4. ✅ 전문가 승인 → 긴급 가동 중지 실행
    5. 📝 감사 기록: "전문가 A, 2025-02-10 14:30, 승인, 긴급 가동 중지"

### 시나리오 2: 에너지 부하 관리

    **상황:**
    - AI가 압력 급증 감지 (125.5 kPa)
    - AI 권장: IMMEDIATE_SHUTDOWN
    
    **워크플로우:**
    1. 🤖 AI 분석 → HIGH 위험도
    2. ⏸️ 전문가 검토 요청
    3. 👤 전문가 판단: "즉시 중지보다 부하 감소가 적절"
    4. ✏️ 전문가 Override → REDUCE_LOAD 선택
    5. 📉 부하 감소 실행
    6. 📝 감사 기록: "AI 권장 수정, 전문가 B, 부하 감소"

### 시나리오 3: 정상 모니터링 (자동화)

    **상황:**
    - 모든 센서 정상 범위
    - 위험도: LOW
    
    **워크플로우:**
    1. 🤖 AI 분석 → LOW 위험도
    2. ✅ 자동 승인 (전문가 개입 없이 바로 실행)
    3. 👁️ 모니터링 계속
    4. 📝 자동 기록: "자동 승인, 정상 범위"

---

## 🔧 기술 스택

    | 카테고리 | 기술 |
    |----------|------|
    | **언어** | Python 3.10+ |
    | **프레임워크** | LangGraph |
    | **상태 관리** | LangGraph Checkpointer (MemorySaver) |
    | **비동기** | asyncio |
    | **타입** | typing, typing_extensions |

### 의존성

    ```txt
    langgraph>=0.2.0
    langchain-core>=0.3.0
    typing-extensions>=4.5.0
    ```

---

## 📚 학습 내용

### 학습한 핵심 패턴

1. ✅ **HITL 기본 패턴**
   - `interrupt()`로 사용자 입력 대기
   - `Command(resume=value)`로 재개

2. ✅ **조건부 라우팅**
   - `Command(goto="node_name")`로 동적 이동
   - 상태에 따른 분기 처리

3. ✅ **비동기 스트리밍**
   - `astream()`의 이벤트 언패킹
   - `__interrupt__` 감지 및 처리

4. ✅ **상태 관리**
   - Checkpointer를 통한 세션 유지
   - `thread_id`로 세션 식별

### 주요 디버깅 경험

**문제:** 비동기 스트리밍에서 interrupt 감지 안 됨
```python
# ❌ 잘못된 언패킹
async for mode, *rest in graph.astream(...):
    chunk = rest[0]  # 구조 불일치

# ✅ 올바른 언패킹
async for event in graph.astream(...):
    if isinstance(event, tuple):
        _, content = event
        chunk = content[1] if isinstance(content, tuple) else content
    else:
        chunk = event
```

---

## 🎯 다음 단계

### 단기 개선 (1-2주)

- [ ] **SQLite Checkpointer 전환**
  ```python
  from langgraph.checkpoint.sqlite import SqliteSaver
  checkpointer = SqliteSaver.from_conn_string("qa_checkpoints.db")
  ```
  - 세션 영구 저장
  - 프로세스 재시작 후 복구

- [ ] **에러 처리 강화**
  - 센서 연결 실패 처리
  - 타임아웃 설정
  - 재시도 로직

- [ ] **알림 시스템 통합**
  ```python
  # 전문가에게 이메일/Slack 알림
  send_notification(
      expert="safety_officer@company.com",
      subject=f"긴급: {facility_id} 승인 필요",
      priority="HIGH"
  )
  ```

### 중기 개선 (1-2개월)

- [ ] **웹 UI 개발**
  - FastAPI 백엔드
  - React 프론트엔드
  - 실시간 센서 대시보드

- [ ] **실제 센서 연동**
  ```python
  # SCADA/IoT 시스템 연결
  sensor_data = scada_client.read_tags([
      "TEMP_SENSOR_01",
      "PRESSURE_GAUGE_02"
  ])
  ```

- [ ] **다중 전문가 승인**
  ```python
  # CRITICAL은 2명 승인 필요
  approval_1 = interrupt({"expert": "shift_manager"})
  approval_2 = interrupt({"expert": "safety_officer"})
  ```

### 장기 목표 (3-6개월)

- [ ] **ML 모델 통합**
  - 이상 징후 예측
  - 임계값 자동 조정

- [ ] **PostgreSQL/MySQL 전환**
  - 엔터프라이즈급 DB
  - 고가용성

- [ ] **감사 리포팅**
  - 승인 준수율 대시보드
  - 의사결정 분석

---

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📖 참고 자료

### 공식 문서
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [HITL Guide](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [Interrupt API](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.types.interrupt)

### 관련 프로젝트
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [Manufacturing HITL Case Studies](https://example.com)

### 학습 자료
- [LangGraph Tutorial](https://python.langchain.com/docs/langgraph)
- [Async Programming in Python](https://docs.python.org/3/library/asyncio.html)

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 📞 문의

질문이나 제안사항이 있으시면 Issue를 열어주세요!

**Happy Learning! 🚀**
