import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages # 메시지 누적 리듀서

load_dotenv()

# 1. State 정의: MessagesState 설정 패턴 적용
class State(TypedDict):
    # add_messages 리듀서를 사용하여 메시지 히스토리를 누적함
    messages: Annotated[list, add_messages] 

# 2. 대화 노드 구현
def chat_node(state: State):
    print("--- [Node: Chat] 이전 대화 맥락 읽는 중... ---")
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION")
    )
    
    # 누적된 전체 메시지 리스트를 LLM에 전달하여 컨텍스트 기반 응답 생성
    response = llm.invoke(state["messages"])
    
    # 새 응답을 리스트 형식으로 반환하면 리듀서가 기존 히스토리에 합쳐줌(Append)
    return {"messages": [response]}

# 3. 그래프 구성 및 Persistence 설정
builder = StateGraph(State)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

# 대화 연속성 확인을 위한 체크포인터 연결
memory = MemorySaver()
app = builder.compile(checkpointer=memory)

# 4. 멀티턴 대화 테스트
config = {"configurable": {"thread_id": "test_session_001"}}

print("\n--- [Round 1: 첫 인사] ---")
user_input_1 = {"messages": [("user", "안녕? 내 이름은 김제미니야.")]}
app.invoke(user_input_1, config)

print("\n--- [Round 2: 이름 기억 확인] ---")
# 동일한 thread_id로 호출하여 이전 이름을 기억하는지 확인
user_input_2 = {"messages": [("user", "내 이름이 뭐라고 했었지?")]}
result = app.invoke(user_input_2, config)

# 최종 출력
print(f"AI 응답: {result['messages'][-1].content}")