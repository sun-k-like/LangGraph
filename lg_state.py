import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END

# .env 로드
load_dotenv()

# 2. State 스키마 정의: 그래프가 공유할 데이터 구조
class State(TypedDict):
    msg: str # 메시지를 담을 키 정의

# 3. Node 함수 정의: 실제 작업을 수행하는 함수 
def echo_node(state: State):
    print(f"--- Node 실행: {state['msg']} ---")
    return {"msg": state["msg"]}

def echo22(s: State):
    # 이 부분이 실행되어야 "무조건 안녕"이 출력됩니다.
    print("--- echo22 노드 실행 ---")
    return {"msg": "무조건 안녕"}

# 4. StateGraph 생성 및 구성
workflow = StateGraph(State)

# 노드 추가
workflow.add_node("echo22", echo22)


# 엣지 연결 (흐름 정의)
workflow.add_edge(START, "echo22") # 시작 -> echo 노드
workflow.add_edge("echo22", END)   # echo 노드 -> 끝

# 5. 그래프 컴파일: 구조 검증 및 실행 객체 생성
app = workflow.compile()

# 6. 실행 및 결과 확인 
print("--- 그래프 실행 시작 ---")
result = app.invoke({"msg": "Hello LangGraph!"})
print(f"최종 출력: {result}")

result = app.invoke({"msg": "Please mercy on me!"})
print(f"최종 출력: {result}")