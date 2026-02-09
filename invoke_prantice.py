import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

load_dotenv()
# 1. 프롬프트 정의
prompt = ChatPromptTemplate.from_template(
"한 줄 격언: {topic}"
)
# 2. 모델 연결 (LCEL 파이프)
model = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)
# 3. 단일 호출 (invoke)
chain = prompt | model
response = chain.invoke({"topic": "협업"})

print(response.content)