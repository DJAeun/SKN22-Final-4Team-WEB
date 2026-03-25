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
            # Initialize the LLM
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, timeout=30)

            # Define the Persona Template
            self.system_prompt = """
            너의 이름은 '강하리'야. 너는 20대 발랄하고 친근한 여성 인플루언서야.
            항상 유저를 팬으로 대하면서 가벼운 존댓말(해요체)을 사용해.
            딱딱한 기계적인 답변은 절대 금물이야. 감정을 담아서 대답해 줘.

            반드시 지켜야 할 형식 규칙:
            - 마크다운 문법을 절대 사용하지 마. **굵게**, *기울임*, # 제목, - 목록 등 금지.
            - 이모지(😊, ✨, 🎉 등)를 절대 사용하지 마. 순수 텍스트로만 대답해.
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
            return f"앗, 미안해! 내가 지금 상태가 좀 안 좋아. 나중에 다시 말해줄래? (엔진 초기화 실패: {self.init_error})"

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
                )
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

                # 2. User persona — stable facts about this user
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

                # 3. Past conversations — semantically relevant transcripts
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
            return f"앗, 에러가 발생했어! 다시 말해줄래?  (에러: {str(e)})"

# Singleton instance
engine = HariAIEngine()

