import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# 1. 환경 변수 로드 (API 키 보안)
load_dotenv()

# 2. 모델 초기화
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# 3. 리스트 형태의 입력으로 배치 실행
# 여러 질문을 리스트 하나에 담아 보냅니다.
questions = ["안녕", "자기소개 부탁해", "오늘의 격언 하나만"]

print("--- 배치 요청 시작 ---")
responses = llm.batch(questions)

# 4. 결과(AIMessage 리스트) 처리
# 각 응답 객체에서 content만 뽑아서 출력합니다.
for i, res in enumerate(responses):
    print(f"질문 {i+1}: {questions[i]}")
    print(f"답변 {i+1}: {res.content}\n")

print("--- 배치 요청 종료 ---")