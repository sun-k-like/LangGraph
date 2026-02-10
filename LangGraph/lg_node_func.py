import os
from typing import Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END

# .env 로드
load_dotenv()

# 1. State 정의: 미니 프로젝트 요구사항 반영 
class State(TypedDict):
    question: str  # 사용자 질문 
    intent: str    # 의도 분류 결과 
    response: str  # 최종 응답 메시지 

# 2. Node 함수 정의
# [의도 분류 노드] 질문에 '가격'이나 '요금'이 포함되면 FAQ로 분류 
def classify_node(state: State):
    print("--- [Node: classify] 의도 분석 중... ---")
    q = state["question"]
    if "가격" in q or "요금" in q:
        intent = "faq" 
    else:
        intent = "escalate" 
    return {"intent": intent} 

# [FAQ 노드] 단순 가격 정보 응답 
def faq_node(state: State):
    print("--- [Node: faq] 답변 생성 ---")
    return {"response": "제품 가격은 월 10,000원입니다."}

# [에스컬레이션 노드] 전문 상담원 연결 안내 
def escalate_node(state: State):
    print("--- [Node: escalate] 상담 안내 ---")
    return {"response": "전문 상담원에게 연결해 드리겠습니다. 잠시만 기다려 주세요."}

# 3. 그래프 구성 
workflow = StateGraph(State)

workflow.add_node("classify", classify_node) 
workflow.add_node("faq", faq_node) 
workflow.add_node("escalate", escalate_node)

# 흐름 정의: 시작하면 무조건 분류 노드로 
workflow.add_edge(START, "classify")

# 조건부 엣지: intent 값에 따라 faq 또는 escalate로 라우팅 
workflow.add_conditional_edges(
    "classify",
    lambda s: s["intent"], # 상태의 intent 값을 읽어옴 
    {"faq": "faq", "escalate": "escalate"} # 매핑 딕셔너리 
)

# 최종 응답 후 종료 
workflow.add_edge("faq", END)
workflow.add_edge("escalate", END)

app = workflow.compile()

# 4. 실행 및 검증 (KPI: 라우팅 정확도 체크) 
print("\n--- [테스트 1: FAQ 경로] ---")
res1 = app.invoke({"question": "이 서비스 가격이 얼마인가요?"})
print(f"의도: {res1['intent']} | 응답: {res1['response']}")

print("\n--- [테스트 2: 상담 경로] ---")
res2 = app.invoke({"question": "사용법이 너무 어려워요 도와주세요."})
print(f"의도: {res2['intent']} | 응답: {res2['response']}")