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
    """
    키워드 매칭 기반으로 관련 문서 검색
    """
    query_lower = query.lower()
    
    # 각 문서에 대해 매칭 점수 계산
    scores = []
    for doc in faq_database:
        score = 0
        matched_keywords = []
        
        # 쿼리에 포함된 키워드 개수로 점수 계산
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
    
    # 점수 기준 내림차순 정렬
    scores.sort(key=lambda x: x["score"], reverse=True)
    
    # Top-K 문서 반환
    return scores[:top_k]

# 5. Node 함수 정의
def classify_intent_node(state: State) -> Command[Literal["faq_node", "escalate_node"]]:
    print("--- [Node: Classify] LLM 의도 분류 중... ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "사용자의 질문을 분석하여 'faq' 또는 'escalate' 중 하나로 분류하세요. "
                   "가격, 요금, 서비스 안내, 환불, 운영시간, 결제, 배송 등은 'faq', "
                   "그 외 복잡한 문제나 불만은 'escalate'입니다. "
                   "오직 한 단어(faq 또는 escalate)만 응답하세요."),
        ("placeholder", "{messages}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    intent = response.content.lower().strip()
    
    target = "faq_node" if "faq" in intent else "escalate_node"
    return Command(update={"intent": intent}, goto=target)

def faq_node(state: State):
    print("--- [Node: FAQ] 키워드 기반 답변 생성 중... ---")
    
    # 마지막 사용자 메시지 추출 (수정된 부분)
    user_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    if not user_question:
        return {"messages": [AIMessage(content="질문을 이해하지 못했습니다.")]}
    
    try:
        # 키워드 검색 실행
        search_results = keyword_search(user_question, top_k=2)
        
        if not search_results:
            # 관련 문서를 찾지 못한 경우
            return {"messages": [AIMessage(content="죄송합니다. 해당 질문에 대한 정보를 찾지 못했습니다. "
                                                   "고객센터(1588-1234)로 문의해 주세요.")]}
        
        # 검색된 문서 내용 추출
        context_docs = []
        print(f"[검색된 문서 수: {len(search_results)}]")
        for i, result in enumerate(search_results):
            doc = result["document"]
            score = result["score"]
            keywords = result["matched_keywords"]
            
            context_docs.append(doc["content"])
            print(f"  문서 {i+1} (점수: {score}, 키워드: {keywords}): {doc['content'][:50]}...")
        
        # LLM에게 컨텍스트와 함께 답변 요청
        rag_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "당신은 고객 서비스 FAQ 봇입니다. "
             "제공된 참고 문서를 기반으로 정확하고 친절하게 답변하세요. "
             "문서 내용을 그대로 전달하되, 자연스러운 문장으로 만들어주세요.\n\n"
             "참고 문서:\n{context}"),
            ("placeholder", "{messages}")
        ])
        
        context_text = "\n\n".join([f"- {doc}" for doc in context_docs])
        
        chain = rag_prompt | llm
        response = chain.invoke({
            "context": context_text,
            "messages": state["messages"]
        })
        
        answer = response.content
        
        return {"messages": [AIMessage(content=answer)]}
    
    except Exception as e:
        print(f"[RAG 오류]: {e}")
        return {"messages": [AIMessage(content="죄송합니다. 일시적인 오류가 발생했습니다.")]}

def escalate_node(state: State):
    print("--- [Node: Escalate] 상담원 연결 안내 ---")
    return {"messages": [AIMessage(content="상세한 확인을 위해 전문 상담원을 연결해 드릴까요? "
                                           "고객센터: 1588-1234 (평일 09:00-18:00)")]}

# 6. 그래프 구성
builder = StateGraph(State)

builder.add_node("classify", classify_intent_node)
builder.add_node("faq_node", faq_node)
builder.add_node("escalate_node", escalate_node)

builder.add_edge(START, "classify")
builder.add_edge("faq_node", END)
builder.add_edge("escalate_node", END)

# 7. Persistence 설정
memory = MemorySaver()
app = builder.compile(checkpointer=memory)

# 8. 실행 테스트
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "mini_project_01"}}
    
    print("\n=== [사용자 질문 1] ===")
    for chunk in app.stream({"messages": [HumanMessage(content="가입 비용이 얼마인가요?")]}, config):
        print(chunk)
    
    print("\n=== [사용자 질문 2 (맥락 유지)] ===")
    for chunk in app.stream({"messages": [HumanMessage(content="방금 말한 프로모션은 언제까지인가요?")]}, config):
        print(chunk)
    
    print("\n=== [사용자 질문 3] ===")
    for chunk in app.stream({"messages": [HumanMessage(content="환불 정책 알려주세요")]}, config):
        print(chunk)
    
    print("\n=== [사용자 질문 4] ===")
    for chunk in app.stream({"messages": [HumanMessage(content="결제는 어떻게 하나요?")]}, config):
        print(chunk)
    
    print("\n=== [사용자 질문 5] ===")
    for chunk in app.stream({"messages": [HumanMessage(content="고객센터 전화번호 알려주세요")]}, config):
        print(chunk)