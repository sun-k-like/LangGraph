import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# 1. 환경 변수 로드 (민감 정보 보호)
load_dotenv()

# 2. 스트리밍 모드가 활성화된 모델 초기화
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    streaming=True  # 스트리밍 활성화
)

print("--- 실시간 응답 시작 ---")

# 3. .stream() 메서드로 토큰 단위 응답 반복
# invoke()와 달리 결과가 완성될 때까지 기다리지 않고 조각(chunk)을 즉시 반환합니다.
for chunk in llm.stream("짧은 시 한 편 써줘"):
    # chunk.content에는 실시간으로 생성된 1~2글자가 담겨 있습니다.
    # end=""로 줄바꿈을 막고, flush=True로 즉시 화면에 뿌려줍니다.
    print(chunk.content, end="", flush=True)

print("\n--- 실시간 응답 종료 ---")