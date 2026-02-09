import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)
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

# 3. Step 1: Few-shot 예시 데이터셋 구성
examples = [
    {"input": "아니 배송이 왜 아직도 안와요? 장난해요?", "output": "불편을 드려 죄송합니다. 배송 조회 결과 현재 이동 중으로 확인됩니다. 오늘 중 도착 예정이며, 지연 시 바로 안내드리겠습니다. 주문번호를 알려주시면 더 정확히 확인해드릴게요."},
    {"input": "환불 언제 돼요? 지난주에 신청했는데요", "output": "기다리게 해드려 죄송합니다. 환불은 접수 후 영업일 기준 3~5일 소요될 수 있습니다. 신청일과 결제수단을 알려주시면 현재 처리 상태를 확인해드리겠습니다."},
    {"input": "너네 앱 왜 이따구임? 로그인도 안됨", "output": "이용에 불편을 드려 죄송합니다. 현재 로그인 오류가 발생하는지 확인 중입니다. 우선 앱을 최신 버전으로 업데이트 후 재시도 부탁드립니다. 계속 문제가 있으면 기기/OS 버전과 오류 화면을 알려주시면 빠르게 도와드리겠습니다."},
    {"input": "쿠폰 적용이 안돼요. 조건이 뭔데요?", "output": "불편을 드려 죄송합니다. 쿠폰은 상품/기간/최소 결제금액 조건에 따라 적용이 제한될 수 있습니다. 쿠폰명과 결제 화면을 알려주시면 적용 조건을 함께 확인해드리겠습니다."}
]

# 4. Step 2: FewShot 템플릿 설정
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}")
])

few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

# 5. 최종 시스템 메시지 및 페르소나 설정
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "너는 친절하고 전문적인 CS 상담원이야. '사과/공감 -> 안내/해결 -> 추가 요청/마무리' 구조로 3~6문장 이내로 답변해. 없는 정책을 지어내지 마."),
    few_shot_prompt,
    ("human", "{question}")
])

# 6. LCEL 체인 구성 및 실행
chain = final_prompt | model | StrOutputParser()

customer_inquiry = "이거 산 지 하루만에 고장났는데 어쩔거임? 교환해줘요."
print(f"고객 문의: {customer_inquiry}\n")
print("--- 상담원 답변 ---")
print(chain.invoke({"question": customer_inquiry}))