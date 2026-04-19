from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from database import DB_PATH, create_and_seed_database
import os


class SQLAgent:
    def __init__(self):
        create_and_seed_database()
        self.db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="openai-tools",
            verbose=False,
            handle_parsing_errors=True,
        )

    def query(self, question: str) -> str:
        try:
            result = self.agent.invoke({"input": question})
            return result.get("output", "No answer found.")
        except Exception as e:
            return f"SQL Agent error: {str(e)}"
