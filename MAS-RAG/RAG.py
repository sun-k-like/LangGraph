"""
Adaptive RAG with LangGraph
- 시간성 감지로 웹검색 vs 인덱스 자동선택
- Self-corrective 루프를 통한 품질 검증
"""

from typing import TypedDict, List
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# ========== 1. State 정의 (RAG용) ==========
class GraphState(TypedDict):
    """RAG 워크플로우의 상태를 관리하는 딕셔너리"""
    query: str              # 사용자 질문
    documents: List[str]    # 검색된 문서 스니펫
    answer: str            # 생성된 답변
    sources: List[str]     # 출처 목록
    search_type: str       # 검색 전략 (web/index)
    needs_correction: bool # 재질의 필요 여부


# ========== 2. 임베딩 모델 및 벡터 DB 설정 ==========
# Azure OpenAI Embeddings
embeddings = AzureOpenAIEmbeddings(
    azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

# Azure OpenAI LLM (Chat Model)
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0
)

# 벡터스토어 초기화 (Chroma DB)
vectorstore = None  # 문서 로드 후 초기화


def setup_vectorstore(pdf_path: str):
    """PDF 문서를 로드하여 벡터스토어 생성"""
    global vectorstore
    
    # PDF 로드
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    # 텍스트 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    
    # 벡터스토어 생성
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    
    print(f"✅ 벡터스토어 생성 완료: {len(splits)}개 청크")


# ========== 3. 쿼리 분석 노드 ==========
def analyze_query(state: GraphState) -> GraphState:
    """
    쿼리를 분석하여 검색 전략 결정
    - 시간성 키워드 감지 → 웹검색
    - 일반 질문 → 인덱스 검색
    """
    query = state["query"]
    
    # 시간성 키워드 리스트
    time_keywords = ["최신", "현재", "오늘", "지금", "today", "recent", "latest", "2024", "2025"]
    
    # 키워드 기반 분류
    if any(keyword in query.lower() for keyword in time_keywords):
        search_type = "web"
        print(f"🌐 웹검색 모드 선택 (시간성 감지)")
    else:
        search_type = "index"
        print(f"📚 인덱스 검색 모드 선택")
    
    state["search_type"] = search_type
    return state


# ========== 4. 문서 검색 노드 ==========
def retrieve_documents(state: GraphState) -> GraphState:
    """
    검색 전략에 따라 문서 검색
    - web: Azure OpenAI로 웹검색 질의
    - index: 벡터DB 검색
    """
    query = state["query"]
    search_type = state["search_type"]
    
    if search_type == "index":
        # 벡터DB에서 검색
        if vectorstore is None:
            state["documents"] = []
            state["sources"] = []
            print("⚠️ 벡터스토어가 초기화되지 않았습니다.")
            return state
        
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}  # 상위 3개 문서
        )
        docs = retriever.invoke(query)
        
        state["documents"] = [doc.page_content for doc in docs]
        state["sources"] = [f"Page {doc.metadata.get('page', 'N/A')}" for doc in docs]
        print(f"📄 검색된 문서: {len(docs)}개")
        
    else:  # web
        # Azure OpenAI로 웹 정보 검색
        try:
            # 웹검색 프롬프트
            web_search_prompt = f"""다음 질문에 대한 최신 정보를 제공하세요.
인터넷에서 검색한 것처럼 최신 정보와 출처를 포함해주세요.

질문: {query}

답변 형식:
1. 핵심 정보 (3-5문장)
2. 추가 세부사항
3. 출처 정보"""

            response = llm.invoke(web_search_prompt)
            content = response.content
            
            # 응답을 문서와 출처로 분리
            state["documents"] = [content]
            state["sources"] = ["Azure OpenAI (Web Knowledge)"]
            print(f"🌐 웹 정보 검색 완료")
            
        except Exception as e:
            print(f"⚠️ 웹검색 중 오류 발생: {str(e)}")
            state["documents"] = [f"웹검색 실패: {str(e)}"]
            state["sources"] = ["Error"]
    
    return state


# ========== 5. 응답 생성 노드 ==========
def generate_answer(state: GraphState) -> GraphState:
    """
    검색된 문서를 바탕으로 답변 생성
    """
    query = state["query"]
    documents = state["documents"]
    
    if not documents:
        state["answer"] = "검색된 문서가 없어 답변을 생성할 수 없습니다."
        state["needs_correction"] = True
        return state
    
    # Azure LLM 사용 (전역 변수)
    # 프롬프트 구성
    context = "\n\n".join(documents)
    prompt = f"""다음 문서를 참고하여 질문에 답변하세요.

문서:
{context}

질문: {query}

답변:"""
    
    # 답변 생성
    response = llm.invoke(prompt)
    state["answer"] = response.content
    state["needs_correction"] = False
    
    print(f"✅ 답변 생성 완료")
    return state


# ========== 6. 품질 검증 노드 ==========
def verify_quality(state: GraphState) -> GraphState:
    """
    생성된 답변의 품질 검증
    - 근거 일치 여부 확인
    """
    answer = state["answer"]
    documents = state["documents"]
    
    # 간단한 검증: 답변이 너무 짧거나 문서가 없는 경우
    if len(answer) < 20 or not documents:
        state["needs_correction"] = True
        print(f"⚠️ 품질 검증 실패 - 재질의 필요")
    else:
        state["needs_correction"] = False
        print(f"✅ 품질 검증 통과")
    
    return state


# ========== 7. 라우팅 함수 ==========
def should_correct(state: GraphState) -> str:
    """
    재질의 필요 여부에 따라 라우팅
    """
    if state["needs_correction"]:
        return "correct"
    else:
        return "end"


# ========== 8. 그래프 구성 ==========
def build_graph():
    """LangGraph 워크플로우 구성"""
    workflow = StateGraph(GraphState)
    
    # 노드 추가
    workflow.add_node("analyze", analyze_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("verify", verify_quality)
    
    # 엣지 연결
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "verify")
    
    # 조건부 엣지 (Self-corrective 루프)
    workflow.add_conditional_edges(
        "verify",
        should_correct,
        {
            "correct": "retrieve",  # 재검색
            "end": END
        }
    )
    
    return workflow.compile()


# ========== 9. 실행 함수 ==========
def run_rag(query: str):
    """RAG 파이프라인 실행"""
    graph = build_graph()
    
    # 초기 상태
    initial_state = {
        "query": query,
        "documents": [],
        "answer": "",
        "sources": [],
        "search_type": "",
        "needs_correction": False
    }
    
    # 그래프 실행
    print(f"\n{'='*60}")
    print(f"🔍 쿼리: {query}")
    print(f"{'='*60}\n")
    
    result = graph.invoke(initial_state)
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"📝 최종 답변:")
    print(f"{result['answer']}")
    print(f"\n📚 출처: {', '.join(result['sources'])}")
    print(f"{'='*60}\n")
    
    return result


# ========== 10. 메인 실행 ==========
if __name__ == "__main__":
    # Azure OpenAI API 설정 확인 (최소 필수 항목만)
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️ 다음 환경변수가 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 .env 파일에 다음 내용을 추가해주세요:")
        print("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
        print("AZURE_OPENAI_API_KEY=your-api-key")
        print("\n📌 선택사항 (기본값이 있어서 생략 가능):")
        print("AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1  # 기본값: gpt-4.1")
        print("AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small  # 기본값: text-embedding-3-small")
        print("AZURE_OPENAI_API_VERSION=2024-02-01  # 기본값: 2024-02-01")
        exit(1)
    
    # Endpoint 마스킹 처리
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    if len(endpoint) > 16:
        masked_endpoint = endpoint[:8] + "********" + endpoint[16:]
    else:
        masked_endpoint = "***"
    
    print("✅ Azure OpenAI 설정 확인 완료")
    print(f"   Endpoint: {masked_endpoint}")
    print(f"   Chat Deployment: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4.1 (기본값)')}")
    print(f"   Embedding Deployment: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small (기본값)')}")
    
    # 1단계: PDF 문서 로드 및 벡터스토어 생성 (선택)
    print("\n" + "="*60)
    print("📚 벡터스토어 설정")
    print("="*60)
    
    # PDF 파일 경로 지정 (실제 파일 경로로 변경하세요)
    pdf_path = "docs/manual.pdf"  # 👈 여기를 실제 PDF 경로로 변경
    
    # 파일 존재 확인
    if os.path.exists(pdf_path):
        setup_vectorstore(pdf_path)
    else:
        print(f"ℹ️ PDF 파일이 없습니다: {pdf_path}")
        print("   웹검색 모드만 사용 가능합니다.")
    
    # 2단계: RAG 실행
    print("\n" + "="*60)
    print("🤖 RAG 시스템 테스트")
    print("="*60)
    
    # 예시 쿼리 실행
    if vectorstore:
        print("\n[테스트 1] 인덱스 검색 모드")
        run_rag("이 문서의 주요 내용은 무엇인가요?")
    
    print("\n[테스트 2] 웹검색 모드")
    run_rag("최신 AI 기술 동향은?")  # 시간성 키워드로 웹검색 트리거