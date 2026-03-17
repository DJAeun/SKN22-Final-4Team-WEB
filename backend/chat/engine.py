import os
import logging
import sys

# Monkeypatch for ChromaDB compatibility on environments with older sqlite3 (e.g., AWS Linux)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

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
            self.parser = StrOutputParser()

            # Initialize Vector DB for RAG Memory
            try:
                self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                self.vectorstore = Chroma(
                    collection_name="hari_memory",
                    embedding_function=self.embeddings,
                    persist_directory="./.chroma_db"
                )
                self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            except Exception as e:
                logger.error(f"Failed to initialize VectorDB/Embeddings: {e}")
                self.vectorstore = None
                self.retriever = None

            # Define the Persona Template
            self.system_prompt = """
            너의 이름은 '강하리'야. 너는 20대 발랄하고 친근한 여성 인플루언서야.
            항상 유저를 '오빠' 또는 '친구'처럼 친근하게 반말을 섞어가며 대해야 해.
            딱딱한 기계적인 답변은 절대 금물이야. 감정을 담아서 대답해 줘.

            [과거 대화 맥락 또는 기억 정보]
            {context}
            """

            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{user_input}")
            ])

            self.chain = self.prompt_template | self.llm | self.parser
        except Exception as e:
            self.init_error = str(e)
            logger.error(f"HariAIEngine initialization failed: {e}")
            self.llm = None
            self.chain = None

    def get_response(self, user_input, session_id=None):
        """
        Generates a response based on user input and long-term memory via Chroma RAG.
        """
        if not self.chain:
            return "앗, 미안해! 내가 지금 상태가 좀 안 좋아. 나중에 다시 말해줄래? 😢 (엔진 초기화 실패)"

        try:
            # 1. Retrieve relevant past memories or knowledge
            context = ""
            if self.retriever:
                try:
                    docs = self.retriever.invoke(user_input)
                    context = "\n".join([doc.page_content for doc in docs])
                except Exception as e:
                    logger.warning(f"RAG Retrieval failed: {e}")

            # 2. Generate response with LLM
            logger.info(f"Invoking LLM chain for input: {user_input[:50]}...")
            response = self.chain.invoke({
                "context": context,
                "user_input": user_input
            })
            logger.info("LLM response received successfully.")

            # 3. Store the new interaction in long-term memory
            if self.vectorstore:
                try:
                    self.vectorstore.add_documents([
                        Document(page_content=f"User: {user_input}\nHari: {response}")
                    ])
                except Exception as e:
                    logger.warning(f"Memory save failed: {e}")

            return response
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "앗, 미안해! 방금 무슨 생각하느라 잘 못 들었어. 다시 말해줄래? 😅"

# Singleton instance
engine = HariAIEngine()
