import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_core.runnables import RunnablePassthrough

# 1. 환경 설정 로드
load_dotenv()

# 2. Azure LLM 설정
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    temperature=0.7,
    verbose=True
)

# 3. 각 단계별 체인 정의
# (1) 제목 생성
title_prompt = ChatPromptTemplate.from_template("주제 '{topic}'에 대한 블로그 제목 5개를 추천해줘.")
title_chain = title_prompt | llm

# (2) 목차 생성
outline_prompt = ChatPromptTemplate.from_template("제목: {title}\n위 주제에 대한 블로그 목차 6개를 작성해줘.")
outline_chain = outline_prompt | llm

# (3) 본문 생성
body_prompt = ChatPromptTemplate.from_template("주제: {topic}\n제목: {title}\n목차: {outline}\n본문을 작성해줘.")
body_chain = body_prompt | llm

# 4. 전체 파이프라인 연결
blog_chain = (
    {"topic": RunnablePassthrough()} 
    | RunnablePassthrough.assign(title=title_chain)
    | RunnablePassthrough.assign(outline=outline_chain)
    | body_chain 
)

# 5. 실행 및 결과 출력
print("작업을 시작합니다. 약 30초만 기다려주세요...")
response = blog_chain.invoke("LCEL 완벽 가이드")

print("\n" + "="*50)
print("최종 블로그 포스팅 내용")
print("="*50)
print(response.content) 

# ... (기존 설정 및 body_chain 정의까지는 동일)

# 1. 리라이팅 프롬프트 정의 (규칙 적용)
rewrite_template = """
당신은 청년 정책 전문 가이드입니다. 아래 원본 글을 리라이팅 규칙에 맞춰 수정해주세요.

[리라이팅 규칙]
1. 하단에 반드시 '출처: 2026 정부 정책 공식 홈페이지' 문구 포함
2. 나이, 지원 금액, 신청 날짜 등 필수 정보를 표(Table) 또는 불렛포인트로 요약하여 상단에 배치
3. 더 친근하고 신뢰감 있는 말투로 변경

[원본 글]
{draft_content}
"""
rewrite_prompt = ChatPromptTemplate.from_template(rewrite_template)
rewrite_chain = rewrite_prompt | llm

# 2. 전체 파이프라인 확장 (초안 생성 후 리라이팅)
# .assign을 사용하면 이전 단계의 'draft_content'를 유지한 채 'final_content'를 추가할 수 있습니다.
final_blog_chain = (
    blog_chain 
    | {"draft_content": lambda x: x.content} # 앞선 체인의 결과(AIMessage)에서 텍스트만 추출
    | RunnablePassthrough.assign(final_content=rewrite_chain)
)

# 3. 실행 (주제: 2026 청년 지원 정책)
print("청년 정책 포스팅 및 리라이팅을 시작합니다...")
result = final_blog_chain.invoke("2026 청년 지원 정책")

# 4. 결과 비교 출력 (제출용)
print("\n" + "="*30 + " [STEP 1] 초안 (Draft) " + "="*30)
print(result['draft_content'])

print("\n" + "="*30 + " [STEP 2] 리라이팅 결과 (Final) " + "="*30)
print(result['final_content'].content)