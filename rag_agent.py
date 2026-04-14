# rag_agent.py
from langchain_openai import ChatOpenAI
from rag_pipeline import HybridRetriever


class RAGAgent:
    def __init__(self):
        self.retriever = HybridRetriever(top_k=5)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def add_pdf(self, pdf_path: str) -> int:
        return self.retriever.add_pdf(pdf_path)

    def is_ready(self) -> bool:
        return self.retriever.is_ready()

    def query(self, question: str) -> str:
        if not self.retriever.is_ready():
            return "No documents have been uploaded yet.Please upload a PDF policy document first."
        try:
            chunks = self.retriever.retrieve(question)
            context = "\n\n---\n\n".join(chunks)
            prompt = f"""You are a helpful customer support assistant. 
Use the following context from our policy documents to answer the question.
If the answer is not in the context, say you couldn't find relevant information in the uploaded documents.

Context:
{context}

Question: {question}

Answer:"""
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"RAG Agent error: {str(e)}"