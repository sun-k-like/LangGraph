"""
멀티 에이전트 시스템 - LangGraph 기반 구현
Supervisor 패턴을 활용한 리서치 & 작성 에이전트
(OpenAI API 없이 DuckDuckGo 검색만 사용)
"""

import sqlite3
import json
from typing import TypedDict
from datetime import datetime
from ddgs import DDGS
from langgraph.graph import StateGraph, END


# ======================
# 1. 상태 관리 (State)
# ======================
class AgentState(TypedDict):
    """멀티 에이전트 공유 상태"""
    messages: list
    next_agent: str
    research_notes: str
    draft: str
    final_output: str
    metadata: dict


# ======================
# 2. 툴 바인딩 (Tools)
# ======================
def search_web(query: str, max_results: int = 5) -> list:
    """
    DuckDuckGo 검색 API를 통한 웹 검색
    
    Args:
        query: 검색 키워드
        max_results: 최대 결과 수 (기본 5개)
    
    Returns:
        검색 결과 리스트
    """
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        return results if results else []
    
    except Exception as e:
        print(f"검색 오류: {str(e)}")
        return []


def save_to_db(content: str, content_type: str) -> str:
    """
    SQLite DB에 콘텐츠 저장
    
    Args:
        content: 저장할 내용
        content_type: 콘텐츠 타입 (research/draft/final)
    
    Returns:
        저장 결과 메시지
    """
    try:
        conn = sqlite3.connect('agent_outputs.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS outputs
                     (id INTEGER PRIMARY KEY, 
                      type TEXT, 
                      content TEXT, 
                      timestamp TEXT)''')
        
        c.execute("INSERT INTO outputs (type, content, timestamp) VALUES (?, ?, ?)",
                  (content_type, content, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return f"✅ {content_type} 저장 완료"
    
    except Exception as e:
        return f"❌ DB 저장 오류: {str(e)}"


# ======================
# 3. 리서치 에이전트
# ======================
def research_agent(state: AgentState) -> AgentState:
    """
    검색 → 요약 → 출처 기록 파이프라인 (규칙 기반)
    """
    try:
        messages = state.get("messages", [])
        user_query = messages[0] if messages else "AI 트렌드"
        
        print(f"\n🔍 리서치 에이전트: '{user_query}' 검색 중...")
        
        # 검색 수행
        search_results = search_web(user_query, max_results=3)
        
        if not search_results:
            raise Exception("검색 결과 없음")
        
        # 규칙 기반 요약 생성
        research_notes = "## 검색 결과 요약\n\n"
        research_notes += f"검색어: {user_query}\n"
        research_notes += f"검색 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        research_notes += "### 주요 발견 사항:\n"
        for i, result in enumerate(search_results, 1):
            research_notes += f"{i}. {result['title']}\n"
            research_notes += f"   - 내용: {result['body'][:200]}...\n"
            research_notes += f"   - 출처: {result['href']}\n\n"
        
        # DB 저장
        save_result = save_to_db(research_notes, "research")
        print(f"   {save_result}")
        print("✅ 리서치 완료!")
        
        # 상태 업데이트
        state["research_notes"] = research_notes
        state["next_agent"] = "writer"
        state["metadata"] = {
            "research_timestamp": datetime.now().isoformat(),
            "sources_count": len(search_results),
            "query": user_query
        }
        
        return state
    
    except Exception as e:
        # 폴백 전략: 오류 시 간단한 노트 생성
        print(f"❌ 리서치 오류: {str(e)}")
        state["research_notes"] = f"리서치 실패: {str(e)}\n기본 정보를 사용합니다."
        state["next_agent"] = "writer"
        state["metadata"] = {"error": str(e)}
        return state


# ======================
# 4. 작성 에이전트
# ======================
def writer_agent(state: AgentState) -> AgentState:
    """
    리서치 노트를 기반으로 구조화된 초안 생성 (템플릿 기반)
    """
    try:
        research_notes = state.get("research_notes", "")
        messages = state.get("messages", [])
        user_query = messages[0] if messages else "주제"
        
        print(f"\n✍️ 작성 에이전트: 초안 생성 중...")
        
        # 템플릿 기반 초안 생성
        draft = f"""# {user_query}에 대한 리포트

## 개요
이 문서는 DuckDuckGo 검색을 통해 수집된 '{user_query}'에 대한 정보를 정리한 것입니다.

## 리서치 내용
{research_notes}

## 결론
위의 검색 결과를 통해 '{user_query}'에 대한 다양한 관점과 정보를 확인할 수 있었습니다.
더 자세한 내용은 상단의 출처 링크를 참고하시기 바랍니다.

---
*작성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}*
*작성 방식: 멀티 에이전트 시스템 (Supervisor 패턴)*
"""
        
        # DB 저장
        save_result = save_to_db(draft, "draft")
        print(f"   {save_result}")
        print("✅ 초안 작성 완료!")
        
        # 상태 업데이트
        state["draft"] = draft
        state["next_agent"] = "supervisor"
        
        return state
    
    except Exception as e:
        print(f"❌ 작성 오류: {str(e)}")
        state["draft"] = f"작성 실패: {str(e)}"
        state["next_agent"] = "supervisor"
        return state


# ======================
# 5. Supervisor 노드
# ======================
def supervisor_node(state: AgentState) -> AgentState:
    """
    작업 분석 및 에이전트 라우팅
    """
    messages = state.get("messages", [])
    
    if not messages:
        state["next_agent"] = END
        return state
    
    # 실행 이력 확인
    has_research = bool(state.get("research_notes"))
    has_draft = bool(state.get("draft"))
    
    # 라우팅 로직
    if not has_research:
        print("\n👔 Supervisor: 리서치 에이전트로 라우팅")
        state["next_agent"] = "research"
    elif not has_draft:
        print("\n👔 Supervisor: 작성 에이전트로 라우팅")
        state["next_agent"] = "writer"
    else:
        # 최종 검증
        print("\n👔 Supervisor: 모든 작업 완료, 종료합니다.")
        state["final_output"] = state["draft"]
        
        # 최종 결과 DB 저장
        save_to_db(state["final_output"], "final")
        
        state["next_agent"] = END
    
    return state


# ======================
# 6. 그래프 구성
# ======================
def create_multi_agent_graph():
    """
    Supervisor 패턴 기반 멀티 에이전트 그래프 생성
    """
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research", research_agent)
    workflow.add_node("writer", writer_agent)
    
    # 라우팅 (조건부 엣지)
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {
            "research": "research",
            "writer": "writer",
            END: END
        }
    )
    
    workflow.add_edge("research", "supervisor")
    workflow.add_edge("writer", "supervisor")
    
    # 시작점 설정
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()


# ======================
# 7. 실행 함수
# ======================
def run_agent_system(user_input: str):
    """
    멀티 에이전트 시스템 실행
    """
    print("\n" + "=" * 60)
    print("🚀 멀티 에이전트 시스템 시작")
    print("=" * 60)
    
    graph = create_multi_agent_graph()
    
    initial_state = {
        "messages": [user_input],
        "next_agent": "",
        "research_notes": "",
        "draft": "",
        "final_output": "",
        "metadata": {}
    }
    
    # 그래프 실행
    result = graph.invoke(initial_state)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 멀티 에이전트 시스템 실행 결과")
    print("=" * 60)
    print(f"\n🔍 리서치 노트:\n{result['research_notes']}\n")
    print(f"{'='*60}")
    print(f"\n✍️ 초안:\n{result['draft']}\n")
    print(f"{'='*60}")
    print(f"\n📝 최종 결과:\n{result['final_output']}\n")
    print(f"{'='*60}")
    print(f"\n📌 메타데이터:")
    print(json.dumps(result['metadata'], indent=2, ensure_ascii=False))
    print("=" * 60)
    
    # 파일로 저장
    try:
        with open('final_output.md', 'w', encoding='utf-8') as f:
            f.write(result['final_output'])
        print(f"\n💾 최종 결과가 'final_output.md' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"파일 저장 오류: {e}")
    
    return result


# ======================
# 8. 메인 실행
# ======================
if __name__ == "__main__":
    # 테스트 실행
    run_agent_system("2025년 AI 에이전트 트렌드")