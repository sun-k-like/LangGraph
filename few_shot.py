# 1. 예시 데이터 (행정 용어 -> 순화어)
examples = [
    {"input": "금회 기성금 지급을 신청합니다.", "output": "이번에 공사한 만큼의 대금을 청구합니다."},
    {"input": "해당 사항을 숙지하시기 바랍니다.", "output": "이 내용을 꼭 확인하고 기억해 주세요."},
    {"input": "익일까지 서류를 보완하여 제출하십시오.", "output": "내일까지 부족한 서류를 채워서 내주세요."},
    {"input": "당해 연도 사업은 종료되었습니다.", "output": "올해 진행하는 사업은 끝났습니다."}
]

from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

# 2. 예시 포맷 정의 (Human/AI 역할 매핑) [cite: 772]
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}")
])

# 3. Few-Shot 템플릿 생성 [cite: 777]
few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples
)

# 4. 전체 프롬프트 조립 (시스템 페르소나 부여) [cite: 782, 818]
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 어려운 행정 용어를 초등학생도 이해할 수 있는 쉬운 우리말로 바꾸는 전문가입니다."),
    few_shot_prompt,
    ("human", "{text}")
])