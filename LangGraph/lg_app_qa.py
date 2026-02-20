"""
센서 QA 모니터링 LangGraph 애플리케이션

흐름:
  START
    → analyze_node      (LLM이 센서 데이터 분석 → 이상/정상 판정)
    → [이상] human_review_node  (interrupt → 전문가 대기)
    → action_node       (전문가 결정에 따른 조치)
    → END
    → [정상] normal_node → END
"""

import os
from typing import Literal, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

load_dotenv()

# ── 1. State ──────────────────────────────────────────────────────────────────

class MonitorState(TypedDict):
    sensor_data: dict           # 입력 센서 데이터
    analysis: str               # LLM 분석 요약
    is_anomaly: bool            # 이상 감지 여부
    anomaly_details: str        # 이상 상세 내용
    expert_decision: str        # "approve" | "reject"
    expert_note: str            # 전문가 메모
    action_result: str          # 최종 조치 내용
    status: str                 # 현재 처리 상태

# ── 2. LLM ────────────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

# ── 3. Nodes ──────────────────────────────────────────────────────────────────

def analyze_node(state: MonitorState) -> Command[Literal["human_review_node", "normal_node"]]:
    """LLM이 센서 데이터를 분석하여 이상 여부를 판정하고 다음 노드를 결정한다."""
    print("--- [Node: Analyze] 센서 데이터 분석 중... ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "당신은 산업용 센서 데이터 분석 전문가입니다.\n"
         "주어진 센서 데이터를 분석하여 이상(anomaly) 여부를 판단하세요.\n\n"
         "반드시 아래 형식으로만 응답하세요:\n"
         "ANOMALY: yes 또는 no\n"
         "DETAILS: 이상 상세 내용 (정상이면 '정상 범위 내')\n"
         "ANALYSIS: 전체 분석 요약 (1-2문장)"),
        ("user", "센서 데이터:\n{sensor_data}"),
    ])

    response = (prompt | llm).invoke({"sensor_data": str(state["sensor_data"])})

    # 응답 파싱
    is_anomaly = False
    anomaly_details = "정상 범위 내"
    analysis = response.content.strip()

    for line in response.content.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("ANOMALY:"):
            is_anomaly = "yes" in line.lower()
        elif line.upper().startswith("DETAILS:"):
            anomaly_details = line.split(":", 1)[-1].strip()
        elif line.upper().startswith("ANALYSIS:"):
            analysis = line.split(":", 1)[-1].strip()

    print(f"    → 이상 감지: {is_anomaly} | {anomaly_details}")

    if is_anomaly:
        return Command(
            update={
                "is_anomaly": True,
                "anomaly_details": anomaly_details,
                "analysis": analysis,
                "status": "anomaly_detected",
            },
            goto="human_review_node",
        )
    else:
        return Command(
            update={
                "is_anomaly": False,
                "anomaly_details": "정상",
                "analysis": analysis,
                "status": "normal",
            },
            goto="normal_node",
        )


def human_review_node(state: MonitorState) -> dict:
    """전문가 검토를 위해 그래프 실행을 중단(interrupt)한다.

    resume 값 형식: {"action": "approve"|"reject", "note": "전문가 메모"}
    """
    print("--- [Node: HumanReview] 전문가 검토 대기 중 (interrupt)... ---")

    decision = interrupt({
        "type": "expert_review_required",
        "sensor_data": state["sensor_data"],
        "analysis": state["analysis"],
        "anomaly_details": state["anomaly_details"],
    })

    # interrupt()가 반환한 값 = POST /approve 에서 전달한 결정
    return {
        "expert_decision": decision.get("action", "approve"),
        "expert_note": decision.get("note", ""),
        "status": "expert_reviewed",
    }


def action_node(state: MonitorState) -> dict:
    """전문가 결정에 따른 구체적인 조치를 LLM으로 생성한다."""
    print(f"--- [Node: Action] 전문가 결정 처리 중: {state['expert_decision']} ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "당신은 산업 설비 운영 전문가입니다.\n"
         "전문가의 결정에 따라 취해야 할 구체적인 조치를 간결하게 작성하세요."),
        ("user",
         "이상 내용: {anomaly_details}\n"
         "전문가 결정: {decision}\n"
         "전문가 메모: {note}\n\n"
         "위 상황에 맞는 조치 사항을 작성하세요."),
    ])

    response = (prompt | llm).invoke({
        "anomaly_details": state["anomaly_details"],
        "decision": state["expert_decision"],
        "note": state.get("expert_note", ""),
    })

    return {
        "action_result": response.content.strip(),
        "status": "action_completed",
    }


def normal_node(state: MonitorState) -> dict:
    """정상 판정 처리 — 별도 조치 없이 완료."""
    print("--- [Node: Normal] 정상 상태 처리 완료 ---")
    return {
        "action_result": f"정상 판정. 분석 결과: {state['analysis']}",
        "status": "completed",
    }

# ── 4. Graph 구성 ─────────────────────────────────────────────────────────────

_builder = StateGraph(MonitorState)

_builder.add_node("analyze_node", analyze_node)
_builder.add_node("human_review_node", human_review_node)
_builder.add_node("action_node", action_node)
_builder.add_node("normal_node", normal_node)

_builder.add_edge(START, "analyze_node")
# analyze_node → (Command로 분기) → human_review_node 또는 normal_node
_builder.add_edge("human_review_node", "action_node")
_builder.add_edge("action_node", END)
_builder.add_edge("normal_node", END)

memory = MemorySaver()
qa_graph = _builder.compile(checkpointer=memory)
