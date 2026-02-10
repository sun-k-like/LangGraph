import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. 환경 변수 로드
load_dotenv()

# 2. 모델 설정 (Azure OpenAI)
model = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# 3. 동적 프롬프트 템플릿 정의 (System/User 구조)
# system: AI의 페르소나(역할)를 지정합니다.
# user: 사용자가 입력할 변수가 들어갈 위치를 지정합니다.
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "역할: 한국어 문법 교정기. 사용자의 문장을 자연스럽고 올바르게 교정해줘."),
    ("user", "{text}")
])

# 4. LCEL 체인 구성 (Prompt -> Model -> Parser)
chain = prompt_template | model | StrOutputParser()

# 5. 실행 (변수에 실제 값을 채워 호출)
input_text = "안용? 반가워요."
result = chain.invoke({"text": input_text})

print(f"입력: {input_text}")
print(f"교정 결과: {result}")