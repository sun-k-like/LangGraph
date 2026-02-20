"""
FastAPI 서버 — 센서 QA 모니터링

엔드포인트:
  POST /monitor/start              → 센서 데이터 수신, 그래프 실행, thread_id 반환
  GET  /monitor/{thread_id}/status → 인터럽트 대기 여부 확인
  POST /monitor/{thread_id}/approve→ 전문가 결정 전송 후 그래프 재개

환경 변수(.env):
  N8N_WEBHOOK_URL  n8n webhook URL (기본값: http://localhost:5678/webhook/sensor-alert)
  BASE_URL         이 서버 외부 URL (approve/status URL 생성에 사용)
"""

import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langgraph.types import Command
from lg_app_qa import qa_graph

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────────────

N8N_WEBHOOK_URL: str = os.getenv(
    "N8N_WEBHOOK_URL", "http://localhost:5678/webhook/sensor-alert"
)
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI(
    title="Sensor QA Monitor API",
    description="LangGraph 기반 센서 이상 감지 + 전문가 Human-in-the-Loop 서버",
    version="1.0.0",
)

# 그래프의 동기 invoke를 비동기 환경에서 실행하기 위한 스레드 풀
_executor = ThreadPoolExecutor(max_workers=4)

# ── Request / Response 모델 ───────────────────────────────────────────────────

class SensorData(BaseModel):
    device_id: str = Field(..., description="장치 ID")
    temperature: Optional[float] = Field(None, description="온도 (°C)")
    pressure: Optional[float] = Field(None, description="압력 (kPa)")
    vibration: Optional[float] = Field(None, description="진동 (mm/s)")
    humidity: Optional[float] = Field(None, description="습도 (%)")
    extra: Optional[Dict[str, Any]] = Field(None, description="기타 센서 값")


class ExpertDecision(BaseModel):
    action: str = Field(..., description="결정: 'approve' 또는 'reject'")
    note: Optional[str] = Field("", description="전문가 메모")


# ── n8n Webhook ───────────────────────────────────────────────────────────────

async def _call_n8n_webhook(thread_id: str, state_values: dict) -> None:
    """인터럽트 발생 시 n8n webhook으로 알림을 전송한다."""
    payload = {
        "thread_id": thread_id,
        "event": "interrupt",
        "status": "waiting_for_approval",
        "approve_url": f"{BASE_URL}/monitor/{thread_id}/approve",
        "status_url": f"{BASE_URL}/monitor/{thread_id}/status",
        "sensor_data": state_values.get("sensor_data", {}),
        "analysis": state_values.get("analysis", ""),
        "anomaly_details": state_values.get("anomaly_details", ""),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(N8N_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
        print(f"[n8n] webhook 전송 성공 | thread_id={thread_id}")
    except httpx.HTTPStatusError as e:
        print(f"[n8n] webhook HTTP 오류: {e.response.status_code} | thread_id={thread_id}")
    except Exception as e:
        print(f"[n8n] webhook 전송 실패: {e} | thread_id={thread_id}")


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _get_state_or_404(thread_id: str):
    """thread_id에 해당하는 그래프 상태를 반환. 없으면 HTTPException 발생."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = qa_graph.get_state(config)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"thread_id를 찾을 수 없습니다: {e}")

    if not state or not state.values:
        raise HTTPException(status_code=404, detail="해당 thread_id의 상태가 없습니다.")

    return state, config


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/monitor/start", summary="센서 데이터 수신 및 그래프 실행")
async def start_monitor(sensor_data: SensorData):
    """
    센서 데이터를 받아 QA 그래프를 실행한다.

    - 이상이 감지되지 않으면 즉시 완료 상태를 반환한다.
    - 이상이 감지되면 그래프가 interrupt에서 일시 정지하고
      n8n webhook을 호출한 뒤 `waiting_for_approval` 상태를 반환한다.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "sensor_data": sensor_data.model_dump(exclude_none=True),
        "analysis": "",
        "is_anomaly": False,
        "anomaly_details": "",
        "expert_decision": "",
        "expert_note": "",
        "action_result": "",
        "status": "started",
    }

    loop = asyncio.get_event_loop()

    # 그래프 실행 (interrupt 지점까지만 진행 후 반환)
    await loop.run_in_executor(
        _executor,
        lambda: qa_graph.invoke(initial_state, config),
    )

    state = qa_graph.get_state(config)
    is_interrupted = bool(state.next)

    response: Dict[str, Any] = {
        "thread_id": thread_id,
        "is_anomaly": state.values.get("is_anomaly", False),
        "analysis": state.values.get("analysis", ""),
        "status": "waiting_for_approval" if is_interrupted else "completed",
    }

    if is_interrupted:
        response["anomaly_details"] = state.values.get("anomaly_details", "")
        response["message"] = (
            "이상이 감지되었습니다. "
            f"POST {BASE_URL}/monitor/{thread_id}/approve 로 전문가 결정을 전송하세요."
        )
        # n8n에 알림 (비동기, 응답 차단 없음)
        asyncio.create_task(_call_n8n_webhook(thread_id, state.values))
    else:
        response["action_result"] = state.values.get("action_result", "")

    return response


@app.get("/monitor/{thread_id}/status", summary="인터럽트 대기 상태 확인")
async def get_status(thread_id: str):
    """
    해당 thread_id의 그래프가 전문가 검토를 기다리고 있는지 확인한다.

    - `waiting_for_approval: true` → interrupt 대기 중
    - `waiting_for_approval: false` → 완료 또는 아직 시작 전
    """
    state, _ = _get_state_or_404(thread_id)
    is_interrupted = bool(state.next)

    return {
        "thread_id": thread_id,
        "waiting_for_approval": is_interrupted,
        "status": state.values.get("status", "unknown"),
        "is_anomaly": state.values.get("is_anomaly", False),
        "analysis": state.values.get("analysis", ""),
        "anomaly_details": state.values.get("anomaly_details", ""),
        "action_result": state.values.get("action_result", ""),
        "next_nodes": list(state.next) if state.next else [],
    }


@app.post("/monitor/{thread_id}/approve", summary="전문가 결정 전송 및 그래프 재개")
async def approve(thread_id: str, decision: ExpertDecision):
    """
    전문가 결정(approve/reject)을 전송하고 일시 정지된 그래프를 재개한다.

    - `action`: `"approve"` 또는 `"reject"`
    - `note`: 전문가 메모 (선택)
    """
    if decision.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=422,
            detail="action 값은 'approve' 또는 'reject' 이어야 합니다.",
        )

    state, config = _get_state_or_404(thread_id)

    if not state.next:
        raise HTTPException(
            status_code=400,
            detail="이미 완료된 스레드이거나 인터럽트 대기 상태가 아닙니다.",
        )

    loop = asyncio.get_event_loop()

    # interrupt()에 결정을 전달하여 그래프 재개
    await loop.run_in_executor(
        _executor,
        lambda: qa_graph.invoke(
            Command(resume=decision.model_dump()),
            config,
        ),
    )

    final_state = qa_graph.get_state(config)

    return {
        "thread_id": thread_id,
        "status": "completed",
        "expert_decision": decision.action,
        "expert_note": decision.note,
        "action_result": final_state.values.get("action_result", ""),
    }


# ── 실행 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_monitor:app", host="0.0.0.0", port=8000, reload=True)
