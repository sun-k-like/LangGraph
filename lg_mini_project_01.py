import os
from typing import Annotated, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# 0. 환경 설정
load_dotenv()

# 1. State 정의 (교안 스키마 설계 원칙 반영)
class State(TypedDict):
    # 메시지 리스트를 누적하여 컨텍스트 유지
    messages: Annotated[list, add_messages] 
    # 내부 전용 키로 의도 분류 결과 저장
    intent: str 

# 2. LLM 설정 (Azure OpenAI 활용)
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# 3. Node 함수 정의
def classify_intent_node(state: State) -> Command[Literal["faq_node", "escalate_node"]]:
    print("--- [Node: Classify] LLM 의도 분류 중... ---")
    
    # 의도 분류를 위한 프롬프트
    prompt = ChatPromptTemplate.from_messages([
        ("system", "사용자의 질문을 분석하여 'faq' 또는 'escalate' 중 하나로 분류하세요. "
                   "가격, 요금, 서비스 안내는 'faq', 그 외 복잡한 문제나 불만은 'escalate'입니다. "
                   "오직 한 단어(faq 또는 escalate)만 응답하세요."),
        ("placeholder", "{messages}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    intent = response.content.lower().strip()
    
    # Command 패턴을 이용한 동적 라우팅
    target = "faq_node" if "faq" in intent else "escalate_node"
    return Command(update={"intent": intent}, goto=target)

def faq_node(state: State):
    print("--- [Node: FAQ] RAG 기반 답변 생성 중... ---")
    # 실제 RAG 구현 시 여기서 Vector DB 조회가 이루어집니다.
    return {"messages": [("ai", "현재 기본 요금은 월 10,000원이며, 2월 프로모션이 진행 중입니다.")]}

def escalate_node(state: State):
    print("--- [Node: Escalate] 상담원 연결 안내 ---")
    return {"messages": [("ai", "상세한 확인을 위해 전문 상담원을 연결해 드릴까요?")]}

# 4. 그래프 구성
builder = StateGraph(State)

builder.add_node("classify", classify_intent_node)
builder.add_node("faq_node", faq_node)
builder.add_node("escalate_node", escalate_node)

builder.add_edge(START, "classify")
builder.add_edge("faq_node", END)
builder.add_edge("escalate_node", END)

# 5. Persistence 설정 (멀티턴 대화 가능)
memory = MemorySaver()
app = builder.compile(checkpointer=memory)

# 6. 실행 테스트
config = {"configurable": {"thread_id": "mini_project_01"}}

print("\n--- [사용자 질문 1] ---")
for chunk in app.stream({"messages": [("user", "가입 비용이 얼마인가요?")]}, config):
    print(chunk)

print("\n--- [사용자 질문 2 (맥락 유지)] ---")
for chunk in app.stream({"messages": [("user", "방금 말한 프로모션은 언제까지인가요?")]}, config):
    print(chunk)