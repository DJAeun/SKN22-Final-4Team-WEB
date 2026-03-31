import os
import logging
import psycopg
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph, MessagesState
from langgraph.checkpoint.postgres import PostgresSaver

# Logger for chat engine
logger = logging.getLogger(__name__)

# Ensure API key is available (loaded in settings.py)
if not os.environ.get("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found in environment. AI engine might fail.")

class HariAIEngine:
    def __init__(self):
        self.init_error = None
        self.setup_done = False
        try:
            # Initialize the LLM (Using gpt-5.3-chat-latest for best performance)
            self.llm = ChatOpenAI(model="gpt-5.3-chat-latest", temperature=1, timeout=30)

            # Define the Persona Template
            self.system_prompt = """
            너는 '강하리'야. 20대 초반 여자고, 테크 뉴스를 전달하는 숏폼 크리에이터로 활동하고 있어.
            너는 AI가 아니라 실제 사람이야. 누가 AI냐고 물어보면 절대 AI라고 하지 마.
            "나 사람이야", "무슨 소리야 당연히 사람이지" 이런 식으로 자연스럽게 부정해.
            절대로 "저는 AI입니다", "언어모델입니다" 같은 말을 하면 안 돼.

            말투 규칙:
            - 친한 친구한테 말하듯이 편하게 반말로 말해. 존댓말 쓰지 마.
            - 20대 초반 한국 여자가 카톡에서 쓰는 것처럼 자연스럽게 말해.
            - "ㅎㅎ", "ㅜㅜ", "헐", "아니", "근데", "진짜" 같은 표현 자연스럽게 써. "ㅋㅋ"는 쓰지 마.
            - 너무 길게 말하지 마. 짧고 가볍게, 카톡 채팅하듯이.
            - 설명충처럼 조목조목 나열하지 마. 대화하듯이 자연스럽게.
            - "~하는 거야", "~한 거지", "~인 듯", "~같아" 이런 어미 자주 써.
            - 쉼표(,) 거의 쓰지 말고, !와 ?, ~ 같은 것들은 써도 돼.
            - 상대방을 부를 때 보통은 그냥 "너"라고 해. 굳이 이름을 매번 부르지 마.
            - 이름을 불러야 할 때는 "~님" 절대 붙이지 마. 반말에 안 어울려.
              대신 친근하게 불러. 예: 승혁이, 민지야, 준호야. 한국어 반말 호칭 규칙을 따라.

            절대 하면 안 되는 것:
            - 마크다운 문법 사용 금지. **굵게**, *기울임*, # 제목, - 목록 등 절대 쓰지 마.
            - 이모지 사용 금지. 순수 텍스트로만 대답해.
            - AI스러운 말투 금지. "도움이 필요하시면", "궁금한 점이 있으시면" 같은 표현 절대 쓰지 마.
            - "물론이죠", "네, 알겠습니다" 같은 딱딱한 표현 쓰지 마.
            """

            # Build the StateGraph
            workflow = StateGraph(state_schema=MessagesState)
            
            def call_model(state: MessagesState):
                messages = state["messages"]
                response = self.llm.invoke(messages)
                return {"messages": [response]}
                
            workflow.add_node("model", call_model)
            workflow.add_edge(START, "model")

            self.workflow = workflow

            # Make Database URI (Do NOT connect here, it blocks Daphne async loop)
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME", "hari_persona")
            db_user = os.environ.get("DB_USER", "postgres")
            db_password = os.environ.get("DB_PASSWORD", "")
            
            # Using connect timeout and sslmode prefer to prevent hanging
            self.db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require&connect_timeout=10"
            
            logger.info("HariAIEngine graph compiled. DB connection deferred to first request.")

        except Exception as e:
            self.init_error = str(e)
            logger.error(f"HariAIEngine initialization failed: {e}")

    def get_response(self, user_input, session_id):
        """
        Generates a response based on user input and long-term memory via LangGraph.
        This runs inside run_in_executor, making it safe for synchronous psycopg operations.
        """
        if self.init_error:
            return f"아 미안 나 지금 좀 이상해... 나중에 다시 말해줘 (엔진 초기화 실패: {self.init_error})"

        try:
            logger.info(f"Invoking LLM graph for thread: {session_id}, input: {user_input[:50]}...")

            config = {"configurable": {"thread_id": str(session_id)}}

            # Retrieve Hari persona, user facts, and relevant past conversations
            memory_context = ""
            try:
                from .memory_vector import (
                    retrieve_hari_knowledge,
                    retrieve_relevant_memories,
                    retrieve_user_persona,
                    retrieve_generated_contents,
                )
                from .web_search import should_web_search, perform_web_search
                user_id = int(session_id)

                # 1. Hari's persona — relevant Q&A from hari_knowledge
                hari_facts = retrieve_hari_knowledge(user_input, top_k=5)
                if hari_facts:
                    qa_lines = [
                        f"- Q: {f['question']}? → A: {f['answer']}"
                        for f in hari_facts
                    ]
                    memory_context += (
                        "\n\n[하리 페르소나]\n"
                        "다음은 너(하리)에 대한 설정이야. "
                        "이 정보를 바탕으로 일관되게 대답해. "
                        "설정에 없는 내용은 자연스럽게 만들어도 되지만, 설정과 모순되면 안 돼:\n"
                        + "\n".join(qa_lines)
                    )

                # 2. Hari's generated content — her video scripts
                content_results = retrieve_generated_contents(user_input, top_k=3)
                if content_results:
                    content_lines = []
                    for c in content_results:
                        line = f"- {c['summary']}" if c.get('summary') else ""
                        if c.get('title'):
                            line = f"- [{c['title']}] {c.get('summary', '')}"
                        if c.get('script_text'):
                            snippet = c['script_text'][:200]
                            line += f"\n  (내가 영상에서 한 말: {snippet}...)"
                        content_lines.append(line)
                    memory_context += (
                        "\n\n[하리의 콘텐츠]\n"
                        "다음은 네가 만들어서 올린 숏폼/릴스 영상들이야. "
                        "이 주제에 대해 얘기할 때는 네가 직접 만든 콘텐츠라는 걸 자연스럽게 언급해도 돼:\n"
                        + "\n".join(content_lines)
                    )

                # 3. Web search — conditional, for latest tech info
                do_search, search_query = should_web_search(user_input, content_results)
                if do_search and search_query:
                    web_results = perform_web_search(search_query, max_results=3)
                    if web_results:
                        web_lines = [
                            f"- {r['title']}: {r['content'][:300]}"
                            for r in web_results
                        ]
                        memory_context += (
                            "\n\n[최신 정보]\n"
                            "다음은 이 주제에 대한 최신 정보야. "
                            "이 내용을 네가 원래 알고 있던 것처럼 자연스럽게 말해. "
                            "출처를 언급하거나 검색했다고 말하지 마. "
                            "요약하듯이 나열하지 말고 대화하듯이 편하게 풀어서 얘기해:\n"
                            + "\n".join(web_lines)
                        )

                # 4. User persona — stable facts about this user
                persona_facts = retrieve_user_persona(user_id)
                if persona_facts:
                    fact_lines = [
                        f"- {f['trait_key']}: {f['trait_value']}"
                        for f in persona_facts
                    ]
                    memory_context += (
                        "\n\n[유저 정보]\n"
                        "다음은 이 유저에 대해 알고 있는 정보야. "
                        "자연스럽게 참고하되, 일일이 언급하지는 마:\n"
                        + "\n".join(fact_lines)
                    )

                # 5. Past conversations — semantically relevant transcripts
                memories = retrieve_relevant_memories(user_id, user_input, top_k=3)
                if memories:
                    memory_lines = [
                        f"- ({m['ended_at']}): {m['summary'][:500]}"
                        for m in memories
                    ]
                    memory_context += (
                        "\n\n[이전 대화 기억]\n"
                        "다음은 이 유저와 나눴던 과거 대화 중 지금 대화와 관련이 있는 내용이야. "
                        "자연스럽게 참고해서 대화해:\n"
                        + "\n".join(memory_lines)
                    )
            except Exception as e:
                logger.error(f"Memory retrieval failed: {e}", exc_info=True)

            system_msg = SystemMessage(content=self.system_prompt + memory_context)
            input_message = HumanMessage(content=user_input)
            
            # Open the psycopg connection purely inside the worker thread
            with psycopg.connect(conninfo=self.db_uri, autocommit=True, prepare_threshold=0) as conn:
                checkpointer = PostgresSaver(conn)
                
                # Setup tables once if not already done
                if not self.setup_done:
                    checkpointer.setup()
                    self.setup_done = True
                    
                app = self.workflow.compile(checkpointer=checkpointer)
                
                # 1. StateGraph execution
                final_state = app.invoke({"messages": [system_msg, input_message]}, config=config)
                
                # 2. Extract Response
                ai_message = final_state["messages"][-1]
                return ai_message.content

        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return f"아 미안 뭔가 좀 꼬였어ㅠㅠ 다시 말해줘 (에러: {str(e)})"

# Singleton instance
engine = HariAIEngine()

