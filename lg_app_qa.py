"""
제조/에너지 현장 HITL 시스템
- 이상 징후 AI 자동 감지
- 전문가 승인 기반 가동 중지 결정
- 안전 프로토콜 준수율 추적
"""

import uuid
import asyncio
from datetime import datetime
from typing import Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver


# ============================================
# 1. 상태 정의 (제조 현장 데이터)
# ============================================
class FacilityState(TypedDict):
    # 센서 데이터
    sensor_data: dict
    # AI 분석 결과
    ai_analysis: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommended_action: str
    # 인간 승인 관련
    human_approval: Optional[bool]
    expert_comment: Optional[str]
    # 최종 액션
    final_action: str
    # 메타데이터
    timestamp: str
    facility_id: str


# ============================================
# 2. 센서 데이터 시뮬레이션
# ============================================
def get_sensor_data(scenario: str = "normal") -> dict:
    """실제 현장에서는 SCADA/IoT 시스템에서 데이터 수집"""
    
    scenarios = {
        "normal": {
            "temperature": 72.5,
            "pressure": 101.3,
            "vibration": 0.5,
            "flow_rate": 150.0,
            "power_consumption": 850.0
        },
        "overheating": {
            "temperature": 95.8,  # 임계값 초과
            "pressure": 105.2,
            "vibration": 2.3,
            "flow_rate": 145.0,
            "power_consumption": 1050.0
        },
        "pressure_spike": {
            "temperature": 75.0,
            "pressure": 125.5,  # 위험 수준
            "vibration": 1.8,
            "flow_rate": 140.0,
            "power_consumption": 920.0
        },
        "vibration_anomaly": {
            "temperature": 73.0,
            "pressure": 102.0,
            "vibration": 5.2,  # 비정상 진동
            "flow_rate": 148.0,
            "power_consumption": 870.0
        }
    }
    
    return scenarios.get(scenario, scenarios["normal"])


# ============================================
# 3. AI 분석 노드
# ============================================
def analyze_sensor_data(state: FacilityState) -> dict:
    """센서 데이터 분석 및 위험도 평가"""
    
    sensor_data = state["sensor_data"]
    
    # 임계값 설정 (실제 현장에서는 설비별로 다름)
    TEMP_CRITICAL = 90.0
    TEMP_HIGH = 80.0
    PRESSURE_CRITICAL = 120.0
    PRESSURE_HIGH = 110.0
    VIBRATION_CRITICAL = 4.0
    VIBRATION_HIGH = 2.0
    
    temp = sensor_data.get("temperature", 0)
    pressure = sensor_data.get("pressure", 0)
    vibration = sensor_data.get("vibration", 0)
    
    # 위험도 분석
    critical_issues = []
    high_issues = []
    
    if temp >= TEMP_CRITICAL:
        critical_issues.append(f"온도 위험: {temp}°C (임계값: {TEMP_CRITICAL}°C)")
    elif temp >= TEMP_HIGH:
        high_issues.append(f"온도 주의: {temp}°C")
    
    if pressure >= PRESSURE_CRITICAL:
        critical_issues.append(f"압력 위험: {pressure} kPa (임계값: {PRESSURE_CRITICAL} kPa)")
    elif pressure >= PRESSURE_HIGH:
        high_issues.append(f"압력 주의: {pressure} kPa")
    
    if vibration >= VIBRATION_CRITICAL:
        critical_issues.append(f"진동 위험: {vibration} mm/s (임계값: {VIBRATION_CRITICAL} mm/s)")
    elif vibration >= VIBRATION_HIGH:
        high_issues.append(f"진동 주의: {vibration} mm/s")
    
    # 위험도 레벨 결정
    if critical_issues:
        risk_level = "CRITICAL"
        recommended_action = "IMMEDIATE_SHUTDOWN"
        analysis = f"🚨 긴급 상황 감지!\n" + "\n".join(critical_issues)
    elif high_issues:
        risk_level = "HIGH"
        recommended_action = "CONTROLLED_SHUTDOWN"
        analysis = f"⚠️ 주의 필요!\n" + "\n".join(high_issues)
    else:
        risk_level = "LOW"
        recommended_action = "CONTINUE_MONITORING"
        analysis = "✅ 정상 범위 내 작동 중"
    
    print(f"\n{'='*60}")
    print(f"🤖 AI 분석 완료 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"위험도: {risk_level}")
    print(f"분석 결과:\n{analysis}")
    print(f"권장 조치: {recommended_action}")
    print(f"{'='*60}\n")
    
    return {
        "ai_analysis": analysis,
        "risk_level": risk_level,
        "recommended_action": recommended_action
    }


# ============================================
# 4. 전문가 승인 노드 (interrupt 사용)
# ============================================
def expert_approval_node(state: FacilityState) -> Command[Literal["execute_action", "override_action"]]:
    """
    전문가 승인을 위한 Human-in-the-Loop 노드
    HIGH 또는 CRITICAL 위험도일 경우 반드시 전문가 검토 필요
    """
    
    risk_level = state["risk_level"]
    
    # LOW 위험도는 자동 승인
    if risk_level == "LOW":
        print("✅ 위험도 낮음 - 자동 승인")
        return Command(
            goto="execute_action",
            update={
                "human_approval": True,
                "expert_comment": "자동 승인 (정상 범위)"
            }
        )
    
    # HIGH, CRITICAL은 전문가 승인 필요
    print(f"\n{'='*60}")
    print(f"⏸️  전문가 검토 대기 중...")
    print(f"{'='*60}")
    print(f"설비 ID: {state['facility_id']}")
    print(f"위험도: {risk_level}")
    print(f"AI 권장 조치: {state['recommended_action']}")
    print(f"\n센서 데이터:")
    for key, value in state['sensor_data'].items():
        print(f"  - {key}: {value}")
    print(f"{'='*60}\n")
    
    # interrupt로 전문가 입력 대기
    approval_data = interrupt({
        "type": "expert_approval_required",
        "facility_id": state["facility_id"],
        "risk_level": risk_level,
        "ai_analysis": state["ai_analysis"],
        "recommended_action": state["recommended_action"],
        "sensor_data": state["sensor_data"],
        "timestamp": state["timestamp"]
    })
    
    # 전문가 결정 처리
    approved = approval_data.get("approved", False)
    comment = approval_data.get("comment", "")
    override_action = approval_data.get("override_action", None)
    
    print(f"\n{'='*60}")
    print(f"👤 전문가 결정 수신")
    print(f"{'='*60}")
    print(f"승인 여부: {'✅ 승인' if approved else '❌ 거부'}")
    print(f"전문가 의견: {comment}")
    if override_action:
        print(f"수정된 조치: {override_action}")
    print(f"{'='*60}\n")
    
    update_data = {
        "human_approval": approved,
        "expert_comment": comment
    }
    
    # 전문가가 다른 조치를 지정한 경우
    if override_action:
        update_data["recommended_action"] = override_action
        return Command(goto="override_action", update=update_data)
    
    return Command(goto="execute_action", update=update_data)


# ============================================
# 5. 조치 실행 노드
# ============================================
def execute_action_node(state: FacilityState) -> dict:
    """승인된 조치 실행"""
    
    action = state["recommended_action"]
    approved = state.get("human_approval", False)
    
    if not approved:
        print("❌ 전문가 승인 없음 - 조치 실행 취소")
        return {"final_action": "NO_ACTION_TAKEN"}
    
    print(f"\n{'='*60}")
    print(f"⚙️  조치 실행 중...")
    print(f"{'='*60}")
    
    action_map = {
        "IMMEDIATE_SHUTDOWN": "🛑 긴급 가동 중지 실행",
        "CONTROLLED_SHUTDOWN": "⏬ 제어된 가동 중지 실행",
        "CONTINUE_MONITORING": "👁️ 모니터링 계속",
        "REDUCE_LOAD": "📉 부하 감소 실행",
        "MAINTENANCE_ALERT": "🔧 유지보수 알림 전송"
    }
    
    action_message = action_map.get(action, f"조치: {action}")
    print(f"{action_message}")
    print(f"전문가 의견: {state.get('expert_comment', 'N/A')}")
    print(f"{'='*60}\n")
    
    # 실제 시스템에서는 여기서 SCADA/PLC 제어 명령 전송
    # send_control_command(facility_id, action)
    
    return {"final_action": action}


def override_action_node(state: FacilityState) -> dict:
    """전문가가 조치를 수정한 경우"""
    print(f"\n⚠️ 전문가가 AI 권장 조치를 수정했습니다")
    print(f"원래 권장 조치: {state['ai_analysis']}")
    print(f"수정된 조치: {state['recommended_action']}\n")
    
    return execute_action_node(state)


# ============================================
# 6. 그래프 구성
# ============================================
def create_facility_monitor_graph():
    """HITL 패턴이 적용된 설비 모니터링 그래프 생성"""
    
    builder = StateGraph(FacilityState)
    
    # 노드 추가
    builder.add_node("analyze", analyze_sensor_data)
    builder.add_node("expert_approval", expert_approval_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("override_action", override_action_node)
    
    # 플로우 정의
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "expert_approval")
    # expert_approval_node에서 Command로 라우팅 제어
    builder.add_edge("execute_action", END)
    builder.add_edge("override_action", END)
    
    # 체크포인터 설정 (상태 저장용)
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    
    return graph


# ============================================
# 7. 동기 실행 함수
# ============================================
def run_monitoring_cycle(scenario: str = "overheating"):
    """동기 방식으로 모니터링 사이클 실행"""
    
    graph = create_facility_monitor_graph()
    
    # 세션 설정
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    facility_id = f"PLANT-{uuid.uuid4().hex[:8].upper()}"
    
    print(f"\n{'#'*60}")
    print(f"🏭 설비 모니터링 시작")
    print(f"{'#'*60}")
    print(f"설비 ID: {facility_id}")
    print(f"세션 ID: {config['configurable']['thread_id']}")
    print(f"시나리오: {scenario}")
    print(f"{'#'*60}\n")
    
    # 초기 입력
    initial_state = {
        "sensor_data": get_sensor_data(scenario),
        "facility_id": facility_id,
        "timestamp": datetime.now().isoformat()
    }
    
    # 첫 번째 실행 (interrupt까지)
    print("📊 센서 데이터 수집 중...\n")
    result = graph.invoke(initial_state, config=config)
    
    # interrupt 확인
    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value
        
        # 전문가 입력 시뮬레이션 (실제로는 웹 UI 등에서 입력받음)
        print("\n" + "="*60)
        print("👤 전문가 검토 필요")
        print("="*60)
        print(f"위험도: {interrupt_data['risk_level']}")
        print(f"AI 분석: {interrupt_data['ai_analysis']}")
        print(f"권장 조치: {interrupt_data['recommended_action']}")
        print("="*60 + "\n")
        
        # 사용자 입력
        print("전문가 결정을 입력하세요:")
        approve = input("승인하시겠습니까? (yes/no): ").strip().lower() == 'yes'
        comment = input("의견을 입력하세요: ").strip()
        
        override = None
        if not approve or input("조치를 수정하시겠습니까? (yes/no): ").strip().lower() == 'yes':
            print("\n가능한 조치:")
            print("1. IMMEDIATE_SHUTDOWN")
            print("2. CONTROLLED_SHUTDOWN")
            print("3. REDUCE_LOAD")
            print("4. MAINTENANCE_ALERT")
            print("5. CONTINUE_MONITORING")
            override = input("선택 (숫자 또는 직접 입력): ").strip()
            
            actions = {
                "1": "IMMEDIATE_SHUTDOWN",
                "2": "CONTROLLED_SHUTDOWN",
                "3": "REDUCE_LOAD",
                "4": "MAINTENANCE_ALERT",
                "5": "CONTINUE_MONITORING"
            }
            override = actions.get(override, override)
        
        # 그래프 재개
        expert_decision = {
            "approved": approve,
            "comment": comment if comment else "전문가 검토 완료",
            "override_action": override
        }
        
        print("\n🔄 그래프 재개 중...\n")
        final_result = graph.invoke(Command(resume=expert_decision), config=config)
        
        # 최종 결과
        print("\n" + "#"*60)
        print("📋 최종 리포트")
        print("#"*60)
        print(f"설비 ID: {final_result['facility_id']}")
        print(f"위험도: {final_result['risk_level']}")
        print(f"전문가 승인: {'✅ 예' if final_result.get('human_approval') else '❌ 아니오'}")
        print(f"전문가 의견: {final_result.get('expert_comment', 'N/A')}")
        print(f"실행된 조치: {final_result['final_action']}")
        print(f"타임스탬프: {final_result['timestamp']}")
        print("#"*60 + "\n")
    else:
        print("✅ 정상 작동 - 전문가 개입 불필요")
        print(f"최종 조치: {result.get('final_action', 'N/A')}\n")


# ============================================
# 8. 비동기 실행 함수 (선택사항)
# ============================================
async def run_monitoring_async(scenario: str = "overheating"):
    """비동기 스트리밍 방식으로 모니터링"""
    
    graph = create_facility_monitor_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    facility_id = f"PLANT-{uuid.uuid4().hex[:8].upper()}"
    
    print(f"\n🏭 비동기 모니터링 시작 - {facility_id}\n")
    
    initial_state = {
        "sensor_data": get_sensor_data(scenario),
        "facility_id": facility_id,
        "timestamp": datetime.now().isoformat()
    }
    
    async for event in graph.astream(initial_state, stream_mode=["updates"], config=config):
        # 이벤트 파싱
        if isinstance(event, tuple):
            _, content = event
            chunk = content[1] if isinstance(content, tuple) else content
        else:
            chunk = event
        
        # 인터럽트 감지
        if isinstance(chunk, dict) and "__interrupt__" in chunk:
            interrupt_data = chunk["__interrupt__"][0].value
            
            print("\n⏸️ 전문가 승인 대기 중...")
            approve = input("승인? (yes/no): ").lower() == 'yes'
            comment = input("의견: ").strip()
            
            decision = {"approved": approve, "comment": comment}
            
            # 재개
            async for resume_event in graph.astream(
                Command(resume=decision),
                stream_mode=["updates"],
                config=config
            ):
                if isinstance(resume_event, tuple):
                    _, resume_content = resume_event
                    resume_chunk = resume_content[1] if isinstance(resume_content, tuple) else resume_content
                else:
                    resume_chunk = resume_event
                
                if isinstance(resume_chunk, dict) and "final_action" in resume_chunk:
                    print(f"\n✅ 완료: {resume_chunk['final_action']}")
            break


# ============================================
# 9. 메인 실행
# ============================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏭 제조/에너지 현장 HITL 모니터링 시스템")
    print("="*60)
    
    print("\n시나리오를 선택하세요:")
    print("1. normal - 정상 작동")
    print("2. overheating - 과열 감지")
    print("3. pressure_spike - 압력 급증")
    print("4. vibration_anomaly - 진동 이상")
    
    choice = input("\n선택 (1-4): ").strip()
    
    scenario_map = {
        "1": "normal",
        "2": "overheating",
        "3": "pressure_spike",
        "4": "vibration_anomaly"
    }
    
    selected_scenario = scenario_map.get(choice, "overheating")
    
    print("\n실행 모드:")
    print("1. 동기 방식 (권장)")
    print("2. 비동기 방식")
    
    mode = input("\n선택 (1-2): ").strip()
    
    if mode == "2":
        asyncio.run(run_monitoring_async(selected_scenario))
    else:
        run_monitoring_cycle(selected_scenario)