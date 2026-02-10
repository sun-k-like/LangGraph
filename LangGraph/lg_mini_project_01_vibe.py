import os
from typing import Annotated, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


# 0. 환경 설정
load_dotenv()

# 1. State 정의
class State(TypedDict):
    messages: Annotated[list, add_messages] 
    intent: str 

# 2. LLM 설정
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# 3. FAQ 문서 데이터 (키워드 기반)
faq_database = [
    {
        "keywords": ["가입", "비용", "요금", "가격", "얼마", "회원"],
        "content": "가입 비용은 월 10,000원입니다. 첫 달은 50% 할인됩니다.",
        "category": "pricing"
    },
    {
        "keywords": ["프로모션", "이벤트", "할인", "혜택", "2월"],
        "content": "2월 프로모션은 2월 28일까지 진행되며, 신규 가입자에게 첫 달 50% 할인 혜택을 제공합니다.",
        "category": "promotion"
    },
    {
        "keywords": ["이용시간", "운영시간", "영업시간", "시간", "언제"],
        "content": "서비스 이용 시간은 평일 09:00 ~ 18:00이며, 주말 및 공휴일은 휴무입니다.",
        "category": "operation"
    },
    {
        "keywords": ["환불", "취소", "해지", "철회"],
        "content": "환불 정책: 가입 후 7일 이내 전액 환불 가능하며, 이후에는 월 단위로 일할 계산됩니다.",
        "category": "refund"
    },
    {
        "keywords": ["고객센터", "연락처", "전화", "문의", "상담"],
        "content": "고객센터 연락처는 1588-1234이며, 평일 09:00 ~ 18:00에 운영됩니다.",
        "category": "contact"
    },
    {
        "keywords": ["결제", "카드", "계좌", "송금", "방법"],
        "content": "결제는 신용카드, 계좌이체, 간편결제(카카오페이, 네이버페이)를 지원합니다.",
        "category": "payment"
    },
    {
        "keywords": ["배송", "택배", "배달", "도착"],
        "content": "배송은 주문 후 2-3일 내 도착하며, 무료 배송입니다.",
        "category": "delivery"
    }
]

# 4. 키워드 기반 검색 함수
def keyword_search(query: str, top_k: int = 2):
    """키워드 매칭 기반으로 관련 문서 검색"""
    query_lower = query.lower()
    scores = []
    
    for doc in faq_database:
        score = 0
        matched_keywords = []
        
        for keyword in doc["keywords"]:
            if keyword in query_lower:
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            scores.append({
                "document": doc,
                "score": score,
                "matched_keywords": matched_keywords
            })
    
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top_k]

# 5. 바이브 코딩 함수 수정 부분
def execute_vibe_code(user_request: str) -> str:
    print("--- [Vibe Coding] 시각화 포함 코드 생성 중... ---")
   
    code_prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 Python 전문가입니다. 요청에 맞는 순수 파이썬 코드만 출력하세요. "
                   "그래프를 그릴 때는 plt.savefig('output_chart.png')를 사용하세요."),
        ("user", "{request}")
    ])
    
    chain = code_prompt | llm
    response = chain.invoke({"request": user_request})
    code = response.content.strip() 
    
    import matplotlib.pyplot as plt
    import numpy as np
    import builtins 

    import matplotlib.font_manager as fm
    plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    try:
        safe_globals = {
            "plt": plt,
            "np": np,
            "__builtins__": {
                "__import__": builtins,
                "print": print,
                "range": range,
                "sum": sum,
                "list": list,
                "dict": dict,
                "len": len,
                "getattr": getattr,
                "hasattr": hasattr,
                "isinstance": isinstance,
                "type": type,
                "str": str,
                "int": int,
                "float": float,
                "tuple": tuple,
                "set": set,
            }
        }
        
        # 파일 초기화 및 실행 로직 동일
        if os.path.exists("output_chart.png"):
            os.remove("output_chart.png")

        exec(code, {"plt": plt, "np": np})
        
        if os.path.exists("output_chart.png"):
            return "그래프를 성공적으로 생성했습니다! 'output_chart.png' 파일을 확인하세요."
        return "코드가 실행되었습니다."
    
    except Exception as e:
        return f"시각화 코드 실행 오류: {str(e)}"

# 6. Node 함수 정의
def classify_intent_node(state: State) -> Command[Literal["faq_node", "vibe_code_node", "escalate_node"]]:
    print("--- [Node: Classify] LLM 의도 분류 중... ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "사용자의 질문을 분석하여 'faq', 'vibe_code', 'escalate' 중 하나로 분류하세요.\n\n"
         "- faq: 가격, 요금, 서비스 안내, 환불, 운영시간, 결제, 배송 등\n"
         "- vibe_code: 계산, 코드 작성, 알고리즘, 데이터 처리 요청\n"
         "  예: '1부터 100까지 더해줘', '피보나치 수열 10개', '소수 찾기'\n"
         "- escalate: 복잡한 문제나 불만\n\n"
         "오직 한 단어(faq, vibe_code, escalate)만 응답하세요."),
        ("placeholder", "{messages}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    intent = response.content.lower().strip()
    
    if "vibe" in intent or "code" in intent:
        target = "vibe_code_node"
    elif "faq" in intent:
        target = "faq_node"
    else:
        target = "escalate_node"
    
    return Command(update={"intent": intent}, goto=target)

def faq_node(state: State):
    print("--- [Node: FAQ] 키워드 기반 답변 생성 중... ---")
    
    user_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    if not user_question:
        return {"messages": [AIMessage(content="질문을 이해하지 못했습니다.")]}
    
    try:
        search_results = keyword_search(user_question, top_k=2)
        
        if not search_results:
            return {"messages": [AIMessage(content="죄송합니다. 해당 질문에 대한 정보를 찾지 못했습니다. "
                                                   "고객센터(1588-1234)로 문의해 주세요.")]}
        
        context_docs = []
        print(f"[검색된 문서 수: {len(search_results)}]")
        for i, result in enumerate(search_results):
            doc = result["document"]
            score = result["score"]
            keywords = result["matched_keywords"]
            
            context_docs.append(doc["content"])
            print(f"  문서 {i+1} (점수: {score}, 키워드: {keywords}): {doc['content'][:50]}...")
        
        rag_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "당신은 고객 서비스 FAQ 봇입니다. "
             "제공된 참고 문서를 기반으로 정확하고 친절하게 답변하세요.\n\n"
             "참고 문서:\n{context}"),
            ("placeholder", "{messages}")
        ])
        
        context_text = "\n\n".join([f"- {doc}" for doc in context_docs])
        
        chain = rag_prompt | llm
        response = chain.invoke({
            "context": context_text,
            "messages": state["messages"]
        })
        
        return {"messages": [AIMessage(content=response.content)]}
    
    except Exception as e:
        print(f"[RAG 오류]: {e}")
        return {"messages": [AIMessage(content="죄송합니다. 일시적인 오류가 발생했습니다.")]}

def vibe_code_node(state: State):
    print("--- [Node: Vibe Code] 코드 실행 중... ---")
    
    user_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    if not user_question:
        return {"messages": [AIMessage(content="요청을 이해하지 못했습니다.")]}
    
    try:
        # 코드 생성 및 실행
        result = execute_vibe_code(user_question)
        
        response_message = f"코드를 실행한 결과입니다:\n\n{result}"
        return {"messages": [AIMessage(content=response_message)]}
    
    except Exception as e:
        print(f"[Vibe Code 오류]: {e}")
        return {"messages": [AIMessage(content=f"코드 실행 중 오류가 발생했습니다: {str(e)}")]}

def escalate_node(state: State):
    print("--- [Node: Escalate] 상담원 연결 안내 ---")
    return {"messages": [AIMessage(content="상세한 확인을 위해 전문 상담원을 연결해 드릴까요? "
                                           "고객센터: 1588-1234 (평일 09:00-18:00)")]}

# 7. 그래프 구성
builder = StateGraph(State)

builder.add_node("classify", classify_intent_node)
builder.add_node("faq_node", faq_node)
builder.add_node("vibe_code_node", vibe_code_node)
builder.add_node("escalate_node", escalate_node)

builder.add_edge(START, "classify")
builder.add_edge("faq_node", END)
builder.add_edge("vibe_code_node", END)
builder.add_edge("escalate_node", END)

# 8. Persistence 설정
memory = MemorySaver()
app = builder.compile(checkpointer=memory)

# 9. 인터랙티브 실행 (대화형 모드)
if __name__ == "__main__":
    import sys
    
    # 모드 선택
    print("=" * 60)
    print("🤖 LangGraph 챗봇 시작!")
    print("=" * 60)
    print("모드를 선택하세요:")
    print("1. 자동 테스트 모드 (미리 정의된 질문들 실행)")
    print("2. 대화형 모드 (직접 질문 입력)")
    print("=" * 60)
    
    mode = input("모드 선택 (1 또는 2): ").strip()
    
    config = {"configurable": {"thread_id": "mini_project_01"}}
    
    if mode == "1":
        # 자동 테스트 모드
        print("\n[자동 테스트 모드 시작]\n")
        
        test_questions = [
            "가입 비용이 얼마인가요?",
            "1부터 100까지 더해줘",
            "피보나치 수열 10개 출력해줘",
            "1부터 20까지 중 소수만 찾아줘",
            "환불 정책 알려주세요"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'=' * 60}")
            print(f"[질문 {i}] {question}")
            print('=' * 60)
            
            for chunk in app.stream({"messages": [HumanMessage(content=question)]}, config):
                print(chunk)
    
    elif mode == "2":
        # 대화형 모드
        print("\n[대화형 모드 시작]")
        print("종료하려면 '종료', 'exit', 'quit'를 입력하세요.\n")
        
        while True:
            print("-" * 60)
            user_input = input("💬 질문: ").strip()
            
            # 종료 조건
            if user_input.lower() in ["종료", "exit", "quit", "q"]:
                print("\n👋 챗봇을 종료합니다. 감사합니다!")
                break
            
            # 빈 입력 처리
            if not user_input:
                print("⚠️  질문을 입력해주세요.")
                continue
            
            print()
            
            # 스트리밍 출력
            for chunk in app.stream({"messages": [HumanMessage(content=user_input)]}, config):
                # AI 메시지만 추출하여 출력
                if 'faq_node' in chunk:
                    messages = chunk['faq_node'].get('messages', [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            print(f"🤖 답변: {msg.content}\n")
                
                elif 'vibe_code_node' in chunk:
                    messages = chunk['vibe_code_node'].get('messages', [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            print(f"🤖 답변: {msg.content}\n")
                
                elif 'escalate_node' in chunk:
                    messages = chunk['escalate_node'].get('messages', [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            print(f"🤖 답변: {msg.content}\n")
    
    else:
        print("⚠️  잘못된 입력입니다. 프로그램을 종료합니다.")