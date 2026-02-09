import os
from typing import Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command 

load_dotenv()

# 1. State 정의: 'processed' 키 추가 
class State(TypedDict):
    question: str
    processed: bool # 처리 완료 플래그 
    response_type: str # 'long' 또는 'short'
    response: str

# 2. Node 함수 정의 (Command 패턴 적용)
def classify_node(state: State) -> Command[Literal["faq", "escalate"]]:
    print("--- [Node: classify] Command 패턴 실행 ---")
    q = state["question"]
    
    # 로직에 따라 다음 목적지 결정 
    nxt = "faq" if "가격" in q or "요금" in q else "escalate"
    
    # 상태 업데이트와 라우팅을 한 번에 반환
    return Command(
        update={"processed": True}, # 'processed' 상태를 True로 변경
        goto=nxt # 결정된 노드로 이동 
    )

def long_response_node(state: State):
    print("--- [Node: long_response] 상세 답변 생성 ---")
    return {
        "response_type": "long",
        "response": "고객님, 문의하신 서비스의 요금제는 기본형 월 10,000원, 프리미엄형 월 30,000원으로 구성되어 있으며 상세 내용은 다음과 같습니다..."
    }

# [추가된 노드 2] 짧은 응답 처리 
def short_response_node(state: State):
    print("--- [Node: short_response] 간결 답변 생성 ---")
    return {
        "response_type": "short",
        "response": "기본 요금은 월 10,000원입니다."
    }

def escalate_node(state: State):
    print("--- [Node: escalate] 상담원 연결 ---")
    return {"response": "상담원에게 연결 중입니다."}

def faq_node(state: State) -> Command[Literal["long_response", "short_response"]]:
    print("--- [Node: faq] 답변 생성 및 경로 결정 ---")
    
    # 질문 길이에 따라 다음 목적지 결정
    nxt = "long_response" if len(state["question"]) > 15 else "short_response"
    
    # Command를 사용하여 다음 노드로 명시적으로 이동
    return Command(
        goto=nxt
    )

# 3. 그래프 구성 
builder = StateGraph(State)

builder.add_node("classify", classify_node)
builder.add_node("faq", faq_node)
builder.add_node("long_response", long_response_node)
builder.add_node("short_response", short_response_node)
builder.add_node("escalate", escalate_node)

builder.add_edge(START, "classify")
builder.add_edge("long_response", END)
builder.add_edge("short_response", END)
builder.add_edge("escalate", END)

app = builder.compile()

# 4. 검증 실행
print("\n--- [테스트: FAQ 긴 응답] ---")
res1 = app.invoke({"question": "서비스 가격 정책과 상세 요금제가 어떻게 되나요?", "processed": False})
print(f"유형: {res1['response_type']} | 응답: {res1['response']}")

print("\n--- [테스트: FAQ 짧은 응답] ---")
res2 = app.invoke({"question": "요금이 얼마죠?", "processed": False})
print(f"유형: {res2['response_type']} | 응답: {res2['response']}")