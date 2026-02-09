import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

# 1. 스키마 정의
class WordInfo(BaseModel):
    word: str = Field(description="단어")
    definition: str = Field(description="정의")
    examples: List[str] = Field(description="예문")

# 2. 체인 설정 (이전 실습과 동일)
model = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)
parser = PydanticOutputParser(pydantic_object=WordInfo)
prompt = ChatPromptTemplate.from_template("단어 '{topic}'의 정보를 추출해.\n{format_instructions}")
prompt = prompt.partial(format_instructions=parser.get_format_instructions())

chain = prompt | model | parser

# 3. 데이터 추출 실행
target = "딥러닝"
print(f"'{target}' 분석 중...")
result_obj = chain.invoke({"topic": target})

# 4. 파일 저장 로직 (핵심!)
def save_to_json(data_obj: WordInfo, filename="word_db.json"):
    # Pydantic 객체를 파이썬 딕셔너리로 변환합니다.
    data_dict = data_obj.model_dump() # Pydantic v2 기준 (v1은 .dict())
    
    # 파일을 쓰기 모드('w')로 열고 저장합니다.
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 저장 완료: {os.path.abspath(filename)}")

# 실행
save_to_json(result_obj)