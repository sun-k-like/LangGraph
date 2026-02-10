import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser # 파서 임포트

load_dotenv()

# 1. 모델과 프롬프트 준비
model = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)
prompt = ChatPromptTemplate.from_template("{topic}에 대해 3행시 지어줘.")

# 2. LCEL 체인 연결 (파서 추가!)
# 파이프(|)로 파서를 마지막에 연결하면 결과가 자동으로 문자열이 됩니다.
chain = prompt | model | StrOutputParser()

# 3. 실행
# .content를 붙이지 않아도 결과가 바로 문자열로 나옵니다.
result = chain.invoke({"topic": "이레라"})
print(result)