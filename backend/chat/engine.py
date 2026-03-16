import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# Use dotenv in production/settings
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "mock-key-for-now")

class HariAIEngine:
    def __init__(self):
        # Initialize the LLM
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        self.parser = StrOutputParser()

        # Initialize Vector DB for RAG Memory
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            collection_name="hari_memory",
            embedding_function=self.embeddings,
            persist_directory="./.chroma_db"
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

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

    def get_response(self, user_input, session_id=None):
        """
        Generates a response based on user input and long-term memory via Chroma RAG.
        """
        try:
            # 1. Retrieve relevant past memories or knowledge
            try:
                docs = self.retriever.invoke(user_input)
                context = "\n".join([doc.page_content for doc in docs])
            except Exception as e:
                # Fallback if embedding fails (e.g. invalid API key for embeddings)
                context = ""
                print(f"RAG Retrieval failed: {e}")

            # 2. Generate response with LLM
            response = self.chain.invoke({
                "context": context,
                "user_input": user_input
            })

            # 3. Store the new interaction in long-term memory
            try:
                self.vectorstore.add_documents([
                    Document(page_content=f"User: {user_input}\nHari: {response}")
                ])
            except Exception as e:
                print(f"Memory save failed: {e}")

            return response
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return "앗, 미안해! 방금 무슨 생각하느라 잘 못 들었어. 다시 말해줄래? 😅"

# Singleton instance
engine = HariAIEngine()
