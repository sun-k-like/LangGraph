# LangGraph Mini Projects

LangGraph를 활용한 다양한 챗봇 및 AI 에이전트 구현 프로젝트 모음

## 📁 프로젝트 구조

### 1. `lg_mini_project_01.py`
**LLM 기반 라우팅 및 키워드 RAG 챗봇**

- **주요 기능**:
  - LLM을 활용한 사용자 의도 분류 (FAQ/Escalate)
  - 키워드 매칭 기반 RAG 검색
  - FAQ 데이터베이스 연동 자동 응답
  
- **기술 스택**:
  - LangGraph StateGraph
  - Azure OpenAI (ChatGPT)
  - 키워드 기반 문서 검색
  - MemorySaver를 통한 대화 이력 관리

### 2. `lg_mini_project_01_vibe.py`
**Vibe Coding 통합 멀티모달 챗봇** ⭐

- **주요 기능**:
  - FAQ 검색 + 동적 코드 생성 및 실행
  - 사용자 요청에 따른 Python 코드 자동 생성
  - Matplotlib를 활용한 데이터 시각화
  - 한글 폰트 지원 (Malgun Gothic)
  
- **기술 스택**:
  - LangGraph Command 패턴
  - Azure OpenAI
  - Python `exec()` 기반 코드 실행
  - Matplotlib + NumPy
  
- **주요 해결 과제**:
  - `__builtins__` 설정 오류 해결
  - 한글 폰트 깨짐 문제 해결

### 3. `lg_parallel.py`
**병렬 실행 (Fan-out/Fan-in) 구현**

- **주요 기능**:
  - StateGraph에서 여러 노드 동시 실행
  - Fan-out: 하나의 노드에서 여러 노드로 분기
  - Fan-in: 여러 노드의 결과를 하나로 병합
  
- **활용 사례**:
  - 다중 데이터 소스 병렬 조회
  - 동시 작업 처리 후 결과 통합

### 4. `lg_multiturn.py`
**다중 턴 대화 챗봇 (add_messages 활용)**

- **주요 기능**:
  - 대화 히스토리 자동 관리
  - `add_messages` reducer를 통한 메시지 누적
  - 연속적인 대화 흐름 유지
  
- **기술 스택**:
  - Annotated 타입을 통한 State 정의
  - 메모리 기반 대화 이력 관리

### 5. `lg_node_func.py`
**LangGraph 기초 및 의사결정 트리**

- **주요 기능**:
  - Node 함수 정의 및 연결
  - 조건부 라우팅 (Conditional Edge)
  - Decision Tree 구조 구현
  
- **학습 내용**:
  - StateGraph 기본 구조
  - Node와 Edge의 역할
  - START/END 노드 활용

### 6. `lg_route.py`
**Persistence 및 캐싱 구현**

- **주요 기능**:
  - MemorySaver를 통한 대화 상태 저장
  - CachePolicy 적용 (메모리 최적화)
  - thread_id 기반 세션 관리
  
- **기술 스택**:
  - LangGraph Checkpointer
  - 메모리 기반 영구 저장소

---

## 🚀 실행 방법

### 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필수 라이브러리 설치
pip install langchain langchain-openai langchain-core langgraph python-dotenv
pip install matplotlib numpy  # Vibe Coding용
```

### 환경 변수 설정 (.env)
```env
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
OPENAI_API_VERSION=2024-02-15-preview
```

### 실행
```bash
# Vibe Coding 챗봇 실행
python lg_mini_project_01_vibe.py

# 기타 프로젝트 실행
python lg_mini_project_01.py
python lg_parallel.py
python lg_multiturn.py
```

---

## 📊 주요 성과

### Vibe Coding 시각화 예시
- **입력**: "최근 5개월간 매출이 100, 150, 130, 200, 180일 때 막대 그래프로 시각화해줘"
- **출력**: 한글 제목이 포함된 막대 그래프 이미지 (`output_chart.png`)

### 해결한 기술적 과제
1. ✅ `'dict' object is not callable` 오류 해결
2. ✅ Matplotlib 한글 폰트 깨짐 문제 해결
3. ✅ LangGraph Command 패턴 적용
4. ✅ 동적 코드 실행 환경 구축

---

## 📚 학습 키워드

- **LangGraph**: StateGraph, Command, Node, Edge
- **RAG**: Keyword Matching, Document Retrieval
- **Vibe Coding**: Dynamic Code Execution, Visualization
- **Persistence**: MemorySaver, Checkpointer
- **LLM Routing**: Intent Classification, Conditional Branching

---

## 🔧 향후 개선 사항

- [ ] Vector DB 기반 Semantic Search 추가
- [ ] Vibe Coding 보안 강화 (샌드박스 환경)
- [ ] 스트리밍 응답 개선
- [ ] 웹 UI 개발 (Streamlit/Gradio)

---

## 📝 License

This project is for educational purposes.
