"""
FAQ + HITL 하이브리드 챗봇 시스템 (간단 버전)
"""

import sqlite3
from datetime import datetime

class HybridChatbot:
    def __init__(self, db_path="chatbot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_db()
        
    def init_db(self):
        """데이터베이스 초기화"""
        cursor = self.conn.cursor()
        
        # FAQ 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY,
                category TEXT,
                question TEXT,
                answer TEXT
            )
        """)
        
        # 상담 세션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                status TEXT,
                message TEXT,
                created_at TEXT
            )
        """)
        
        self.conn.commit()
        self.insert_sample_data()
    
    def insert_sample_data(self):
        """샘플 FAQ 삽입"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM faq")
        if cursor.fetchone()[0] > 0:
            return
            
        faqs = [
            ("계정", "비밀번호를 잊어버렸어요", "로그인 페이지에서 '비밀번호 찾기'를 클릭하세요."),
            ("결제", "환불은 어떻게 하나요?", "마이페이지 > 주문내역에서 환불 신청이 가능합니다."),
            ("배송", "배송 기간은 얼마나 걸리나요?", "주문 후 2-3일 소요됩니다."),
            ("계정", "회원 탈퇴 방법", "설정 > 계정관리 > 회원탈퇴를 선택하세요."),
            ("결제", "결제 수단은 무엇이 있나요?", "신용카드, 계좌이체, 간편결제가 가능합니다."),
        ]
        
        cursor.executemany("INSERT INTO faq (category, question, answer) VALUES (?, ?, ?)", faqs)
        self.conn.commit()
    
    def show_main_menu(self):
        """메인 메뉴 표시"""
        print("\n" + "="*50)
        print("🤖 하이브리드 챗봇 시스템")
        print("="*50)
        print("1. 📚 자주 묻는 질문 보기 (FAQ)")
        print("2. 💬 1:1 상담하기 (상담사 연결)")
        print("3. 🚪 종료")
        print("="*50)
        
    def show_faq_categories(self):
        """FAQ 카테고리 표시"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM faq")
        categories = cursor.fetchall()
        
        print("\n📚 FAQ 카테고리")
        print("-"*50)
        for idx, (cat,) in enumerate(categories, 1):
            print(f"{idx}. {cat}")
        print(f"{len(categories)+1}. 🔙 메인 메뉴로")
        print(f"{len(categories)+2}. ❌ 취소 (cancel)")
        
        return categories
    
    def show_faq_by_category(self, category):
        """카테고리별 FAQ 표시"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, question, answer FROM faq WHERE category=?", (category,))
        faqs = cursor.fetchall()
        
        print(f"\n📖 {category} 관련 질문")
        print("-"*50)
        for idx, (faq_id, question, answer) in enumerate(faqs, 1):
            print(f"{idx}. {question}")
        print(f"{len(faqs)+1}. 🔙 카테고리 선택으로")
        print(f"{len(faqs)+2}. ❌ 취소 (cancel)")
        
        return faqs
    
    def show_faq_detail(self, faq_id, question, answer):
        """FAQ 상세 내용 표시"""
        print("\n" + "="*50)
        print(f"❓ {question}")
        print("-"*50)
        print(f"✅ {answer}")
        print("="*50)
        print("\n이 답변이 도움이 되셨나요?")
        print("1. ✔️ 해결됨 (do)")
        print("2. ❌ 해결 안됨 - 상담사 연결")
        print("3. 🔙 목록으로")
        print("4. ❌ 취소 (cancel)")
    
    def start_consultation(self, user_id, initial_message=""):
        """상담 시작"""
        cursor = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO sessions (user_id, status, message, created_at)
            VALUES (?, 'waiting', ?, ?)
        """, (user_id, initial_message, now))
        
        self.conn.commit()
        session_id = cursor.lastrowid
        
        print("\n" + "="*50)
        print("💬 1:1 상담 시작")
        print("="*50)
        print(f"상담 번호: {session_id}")
        print("상담사 연결 중입니다...")
        print("\n상담을 원하시는 내용을 입력해주세요.")
        print("(명령어: 'do' - 상담 완료, 'cancel' - 상담 취소)")
        print("="*50)
        
        return session_id
    
    def consultation_chat(self, session_id):
        """상담 채팅"""
        while True:
            user_input = input("\n당신: ").strip()
            
            if user_input.lower() == 'cancel':
                self.cancel_consultation(session_id)
                print("❌ 상담이 취소되었습니다.")
                break
            elif user_input.lower() == 'do':
                self.complete_consultation(session_id)
                print("✅ 상담이 완료되었습니다. 감사합니다!")
                break
            elif user_input:
                # 실제로는 상담사에게 전달되지만, 여기서는 시뮬레이션
                print(f"상담사: 문의하신 '{user_input}' 내용을 확인했습니다.")
                print("         곧 답변 드리겠습니다.")
    
    def complete_consultation(self, session_id):
        """상담 완료"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET status='completed' WHERE id=?", (session_id,))
        self.conn.commit()
    
    def cancel_consultation(self, session_id):
        """상담 취소"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET status='cancelled' WHERE id=?", (session_id,))
        self.conn.commit()
    
    def run(self):
        """챗봇 실행"""
        user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        while True:
            self.show_main_menu()
            choice = input("\n선택하세요: ").strip()
            
            if choice == '1':
                # FAQ 모드
                self.faq_mode()
            elif choice == '2':
                # 상담 모드
                print("\n상담을 시작하기 전에 간단히 문의 내용을 알려주세요:")
                initial_msg = input("문의 내용: ").strip()
                session_id = self.start_consultation(user_id, initial_msg)
                self.consultation_chat(session_id)
            elif choice == '3':
                print("\n👋 이용해 주셔서 감사합니다!")
                break
            else:
                print("❌ 잘못된 선택입니다. 다시 선택해주세요.")
    
    def faq_mode(self):
        """FAQ 모드"""
        while True:
            categories = self.show_faq_categories()
            choice = input("\n선택하세요: ").strip()
            
            if not choice.isdigit():
                print("❌ 숫자를 입력해주세요.")
                continue
            
            choice = int(choice)
            
            if choice == len(categories) + 1:
                # 메인 메뉴로
                break
            elif choice == len(categories) + 2:
                # 취소
                print("❌ 취소되었습니다.")
                break
            elif 1 <= choice <= len(categories):
                category = categories[choice-1][0]
                
                # FAQ 목록 표시
                while True:
                    faqs = self.show_faq_by_category(category)
                    faq_choice = input("\n질문 번호 선택: ").strip()
                    
                    if not faq_choice.isdigit():
                        print("❌ 숫자를 입력해주세요.")
                        continue
                    
                    faq_choice = int(faq_choice)
                    
                    if faq_choice == len(faqs) + 1:
                        # 카테고리 선택으로
                        break
                    elif faq_choice == len(faqs) + 2:
                        # 취소
                        print("❌ 취소되었습니다.")
                        return
                    elif 1 <= faq_choice <= len(faqs):
                        faq_id, question, answer = faqs[faq_choice-1]
                        
                        # FAQ 상세 표시
                        while True:
                            self.show_faq_detail(faq_id, question, answer)
                            detail_choice = input("\n선택하세요: ").strip()
                            
                            if detail_choice == '1':
                                # 해결됨 (do)
                                print("✅ 도움이 되어 기쁩니다!")
                                return
                            elif detail_choice == '2':
                                # 상담사 연결
                                print("\n상담사에게 연결합니다...")
                                user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                session_id = self.start_consultation(user_id, f"FAQ '{question}' 관련 추가 문의")
                                self.consultation_chat(session_id)
                                return
                            elif detail_choice == '3':
                                # 목록으로
                                break
                            elif detail_choice == '4':
                                # 취소 (cancel)
                                print("❌ 취소되었습니다.")
                                return
                            else:
                                print("❌ 잘못된 선택입니다.")
                    else:
                        print("❌ 잘못된 선택입니다.")
            else:
                print("❌ 잘못된 선택입니다.")
    
    def close(self):
        """데이터베이스 연결 종료"""
        self.conn.close()


if __name__ == "__main__":
    chatbot = HybridChatbot()
    try:
        chatbot.run()
    finally:
        chatbot.close()