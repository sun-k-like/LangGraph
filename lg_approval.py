import uuid
import asyncio
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

# ============================================
# 1. State 정의
# ============================================
class State(TypedDict):
    action_details: str
    status: str


# ============================================
# 2. 노드 함수 구현
# ============================================
def approval_node(state: State) -> Command[Literal["do", "cancel"]]:
    """
    그래프 실행을 일시 중단하고 사용자의 승인을 대기합니다.
    """
    approved = interrupt({
        "question": "이 작업을 승인하시겠습니까?",
        "action": state["action_details"]
    })
    
    if approved:
        return Command(
            goto="do",
            update={"status": "approved"}
        )
    else:
        return Command(
            goto="cancel",
            update={"status": "rejected"}
        )


def execute_action(state: State):
    print(f"--- 작업 실행: {state['action_details']} ---")
    return {"status": "completed"}


def cancel_action(state: State):
    print("--- 작업 취소됨 ---")
    return {"status": "cancelled"}


# ============================================
# 3. 그래프 구성
# ============================================
builder = StateGraph(State)
builder.add_node("approval", approval_node)
builder.add_node("do", execute_action)
builder.add_node("cancel", cancel_action)

builder.add_edge(START, "approval")
builder.add_edge("do", END)
builder.add_edge("cancel", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


# ============================================
# 4. 비동기 스트리밍 HITL 구현 (수정 버전)
# ============================================
async def run_streaming_hitl():
    """비동기 스트리밍 방식으로 Human-in-the-Loop 처리"""
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print(f"새로운 세션 ID: {config['configurable']['thread_id']}")
    
    initial_input = {"action_details": "서버 재부팅"}
    print("\n=== 비동기 스트림 시작 ===\n")
    
    # astream 반환값 언패킹 수정
    async for event in graph.astream(
        initial_input,
        stream_mode=["updates"],
        config=config
    ):
        # event는 (metadata, (mode, chunk)) 형식
        # 또는 단순히 chunk 형식일 수 있음
        
        # 디버깅: 이벤트 구조 확인
        print(f"[DEBUG] 이벤트 타입: {type(event)}")
        print(f"[DEBUG] 이벤트 내용: {event}\n")
        
        # updates 모드에서 chunk 추출
        if isinstance(event, tuple) and len(event) == 2:
            metadata, content = event
            if isinstance(content, tuple) and len(content) == 2:
                mode, chunk = content
            else:
                chunk = content
        else:
            chunk = event
        
        # 인터럽트 감지
        if isinstance(chunk, dict) and "__interrupt__" in chunk:
            interrupt_info = chunk["__interrupt__"][0].value
            print(f"\n{'='*50}")
            print(f"[보류 중] 질문: {interrupt_info['question']}")
            print(f"[보류 중] 대상 작업: {interrupt_info['action']}")
            print(f"{'='*50}\n")
            
            # 사용자 입력 받기
            user_input = input("승인하시겠습니까? (yes/no): ").strip().lower()
            user_response = user_input == 'yes'
            
            print(f"\n--- '{user_response}' 값으로 재개합니다 ---\n")
            
            # 그래프 재개
            await run_resumed_stream(user_response, config)
            break
        else:
            # 일반 업데이트 출력
            if isinstance(chunk, dict):
                print(f"[업데이트] {chunk}")


async def run_resumed_stream(response: bool, config: dict):
    """그래프 재개 후 스트리밍"""
    
    async for event in graph.astream(
        Command(resume=response),
        stream_mode=["updates"],
        config=config
    ):
        # 동일한 언패킹 로직
        if isinstance(event, tuple) and len(event) == 2:
            metadata, content = event
            if isinstance(content, tuple) and len(content) == 2:
                mode, chunk = content
            else:
                chunk = content
        else:
            chunk = event
            
        if isinstance(chunk, dict):
            print(f"[재개 후 업데이트] {chunk}")
    
    print("\n=== 작업 완료 ===")


# ============================================
# 5. 간단한 동기 버전 (비교용)
# ============================================
def run_simple_hitl():
    """동기 방식의 간단한 HITL 예제"""
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print(f"세션 ID: {config['configurable']['thread_id']}")
    
    initial_input = {"action_details": "서버 재부팅"}
    
    # 첫 번째 실행 (인터럽트까지)
    print("\n=== 첫 번째 실행 ===")
    result = graph.invoke(initial_input, config=config)
    
    # 인터럽트 확인
    if "__interrupt__" in result:
        interrupt_info = result["__interrupt__"][0].value
        print(f"\n질문: {interrupt_info['question']}")
        print(f"작업: {interrupt_info['action']}\n")
        
        user_input = input("승인하시겠습니까? (yes/no): ").strip().lower()
        user_response = user_input == 'yes'
        
        # 재개
        print(f"\n=== '{user_response}'로 재개 ===")
        final_result = graph.invoke(Command(resume=user_response), config=config)
        print(f"최종 상태: {final_result.get('status')}")
    else:
        print(f"최종 결과: {result}")


# ============================================
# 6. 실행
# ============================================
if __name__ == "__main__":
    print("실행 모드를 선택하세요:")
    print("1. 비동기 스트리밍 방식 (권장)")
    print("2. 동기 방식 (간단)")
    
    choice = input("\n선택 (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(run_streaming_hitl())
    elif choice == "2":
        run_simple_hitl()
    else:
        print("잘못된 선택입니다. 동기 방식으로 실행합니다.")
        run_simple_hitl()