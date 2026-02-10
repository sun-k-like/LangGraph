import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# 1. 환경 변수 로드
load_dotenv()

# 2. 추출할 데이터의 구조(Schema) 정의
class WordInfo(BaseModel):
    word: str = Field(description="추출된 단어명")
    definition: str = Field(description="단어의 사전적 정의")
    examples: List[str] = Field(description="해당 단어가 사용된 예문 리스트")

# 3. 모델 및 파서 초기화
model = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# Pydantic Schema를 파서에 연결합니다.
parser = PydanticOutputParser(pydantic_object=WordInfo)

# 4. 프롬프트 정의 (포맷 지시사항 포함)
prompt = ChatPromptTemplate.from_template(
    "다음 단어에 대한 정보를 추출해줘: {topic}\n\n{format_instructions}"
)

# 파서가 제공하는 포맷 지시사항을 프롬프트에 주입합니다.
prompt_with_instructions = prompt.partial(
    format_instructions=parser.get_format_instructions()
)

# 5. LCEL 체인 구성 및 실행
chain = prompt_with_instructions | model | parser

target_word = "인공지능"
print(f"--- '{target_word}' 데이터 추출 중 ---")

try:
    result = chain.invoke({"topic": target_word})
    # 결과는 단순 문자열이 아닌 WordInfo 객체입니다.
    print(f"단어: {result.word}")
    print(f"정의: {result.definition}")
    print(f"예문: {result.examples}")
except Exception as e:
    print(f"에러 발생: {e}")