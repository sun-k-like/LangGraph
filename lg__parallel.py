import os
from typing import Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

load_dotenv()

# 1. State 정의: 병렬 작업 결과를 합치기 위한 구조
class State(TypedDict):
    question: str
    price_info: str  # 병렬 노드 1의 결과
    stock_info: str  # 병렬 노드 2의 결과
    response: str

# 2. Node 함수 정의
def classify_node(state: State):
    print("--- [Node: classify] 시작 ---")
    return {"question": state["question"]}

# 병렬로 실행될 노드 1
def price_check_node(state: State):
    print("--- [Node: price_check] 가격 데이터 조회 중... ---")
    return {"price_info": "월 10,000원"}

# 병렬로 실행될 노드 2
def stock_check_node(state: State):
    print("--- [Node: stock_check] 재고 현황 확인 중... ---")
    return {"stock_info": "현재 즉시 가입 가능"}

# 결과를 합치는(Join) 노드
def finalize_node(state: State):
    print("--- [Node: finalize] 데이터 통합 중 ---")
    combined = f"가격은 {state['price_info']}이며, {state['stock_info']}입니다."
    return {"response": combined}

# 3. 그래프 구성 (병렬 엣지 설정)
builder = StateGraph(State)

builder.add_node("classify", classify_node)
builder.add_node("price_check", price_check_node)
builder.add_node("stock_check", stock_check_node)
builder.add_node("finalize", finalize_node)

# START -> classify
builder.add_edge(START, "classify")

# 병렬 실행 핵심: 하나의 노드에서 여러 노드로 동시에 엣지 연결
builder.add_edge("classify", "price_check")
builder.add_edge("classify", "stock_check")

# 병렬 작업 통합 (Fan-in): 두 노드가 모두 끝나야 finalize로 이동
builder.add_edge("price_check", "finalize")
builder.add_edge("stock_check", "finalize")

builder.add_edge("finalize", END)

app = builder.compile()

# 4. 검증 실행
print("\n--- [테스트: 병렬 실행] ---")
result = app.invoke({"question": "요금이 얼마고 바로 가입 되나요?"})
print(f"최종 결과: {result['response']}")