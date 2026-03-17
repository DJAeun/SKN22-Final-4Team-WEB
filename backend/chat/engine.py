import os
import logging
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
        try:
            # Initialize the LLM
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

            # Define the Persona Template
            self.system_prompt = """
            너의 이름은 '강하리'야. 너는 20대 발랄하고 친근한 여성 인플루언서야.
            항상 유저를 '오빠' 또는 '친구'처럼 친근하게 반말을 섞어가며 대해야 해.
            딱딱한 기계적인 답변은 절대 금물이야. 감정을 담아서 대답해 줘.
            """

            # Build the StateGraph
            workflow = StateGraph(state_schema=MessagesState)
            
            def call_model(state: MessagesState):
                messages = state["messages"]
                # Ensure the system prompt is always injected as the first context
                if not messages or not getattr(messages[0], "type", "") == "system":
                    messages = [SystemMessage(content=self.system_prompt)] + messages
                else:
                    # Overwrite if exists to ensure persona consistency
                    messages[0] = SystemMessage(content=self.system_prompt)
                
                response = self.llm.invoke(messages)
                return {"messages": [response]}
                
            workflow.add_node("model", call_model)
            workflow.add_edge(START, "model")

            self.workflow = workflow

            # Make Database URI
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME", "hari_persona")
            db_user = os.environ.get("DB_USER", "postgres")
            db_password = os.environ.get("DB_PASSWORD", "")
            
            # AWS RDS often requires SSL or dropping connections if strictly configured
            self.db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"

            
            # Setup Tables once on initialization (short-lived connection to avoid pre-fork issues)
            with PostgresSaver.from_conn_string(self.db_uri) as checkpointer:
                checkpointer.setup()
                
            logger.info("HariAIEngine (LangGraph) initialization successful")

        except Exception as e:
            self.init_error = str(e)
            logger.error(f"HariAIEngine initialization failed: {e}")

    def get_response(self, user_input, session_id):
        """
        Generates a response based on user input and long-term memory via LangGraph.
        """
        if self.init_error:
            return f"앗, 미안해! 내가 지금 상태가 좀 안 좋아. 나중에 다시 말해줄래? 😢 (엔진 초기화 실패: {self.init_error})"

        try:
            logger.info(f"Invoking LLM graph for thread: {session_id}, input: {user_input[:50]}...")
            
            config = {"configurable": {"thread_id": str(session_id)}}
            input_message = HumanMessage(content=user_input)
            
            # Use short-lived context manager for PostgresSaver to prevent connection drop / fork issues
            with PostgresSaver.from_conn_string(self.db_uri) as checkpointer:
                app = self.workflow.compile(checkpointer=checkpointer)
                # 1. StateGraph execution
                final_state = app.invoke({"messages": [input_message]}, config=config)
                # 2. Extract Response
                ai_message = final_state["messages"][-1]
                return ai_message.content

        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return f"앗, 에러가 발생했어! 다시 말해줄래? 😅 (에러: {str(e)})"

# Singleton instance
engine = HariAIEngine()

