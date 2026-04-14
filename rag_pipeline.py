
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

load_dotenv()


class HybridRetriever:
    def __init__(self, top_k: int = 5):
        self.top_k = top_k
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.faiss_index: FAISS | None = None
        self.bm25_index: BM25Okapi | None = None
        self.all_chunks: list[str] = []

    def add_pdf(self, pdf_path: str) -> int:
        """
        the pdf is uploaded by the UI and 
        when it is uploaded it builds FAISS + BM25 from scratch
        once uploaded it merges new chunks into both existing indexes
        and returns the number of chunks indexed from this PDF
        """
        path = Path(pdf_path)
        texts = self._load_and_split([path])

        if self.faiss_index is None:
            # First document: build both indexes fresh
            self.all_chunks = texts
            self.faiss_index = FAISS.from_texts(texts, self.embeddings)
            tokenised = [t.lower().split() for t in self.all_chunks]
            self.bm25_index = BM25Okapi(tokenised)
        else:
            
            self.all_chunks.extend(texts)
            new_faiss = FAISS.from_texts(texts, self.embeddings)
            self.faiss_index.merge_from(new_faiss)
            tokenised = [t.lower().split() for t in self.all_chunks]
            self.bm25_index = BM25Okapi(tokenised)

        print(f"[RAG] Added {len(texts)} chunks from '{path.name}'. "
              f"Total chunks in index: {len(self.all_chunks)}")
        return len(texts)

    def retrieve(self, query: str) -> list[str]:
        #Return top-k chunks
        if not self.faiss_index or not self.bm25_index:
            raise RuntimeError("No documents indexed yet. Upload a PDF first.")
        faiss_results = self._dense_search(query)
        bm25_results  = self._sparse_search(query)
        fused = self._reciprocal_rank_fusion(faiss_results, bm25_results)
        return fused[: self.top_k]

    def is_ready(self) -> bool:
        """Returns True once at least one PDF has been indexed."""
        return self.faiss_index is not None and self.bm25_index is not None


    def _load_and_split(self, pdf_paths: list[Path]) -> list[str]:
        """Load PDFs and split into text chunks."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
        texts = []
        for path in pdf_paths:
            print(f"[RAG] Loading '{path.name}'...")
            loader = PyPDFLoader(str(path))
            docs  = loader.load()
            chunks = splitter.split_documents(docs)
            texts.extend(chunk.page_content for chunk in chunks)
        return texts

    def _dense_search(self, query: str) -> list[str]:
        docs = self.faiss_index.similarity_search(query, k=self.top_k * 2)
        return [d.page_content for d in docs]

    def _sparse_search(self, query: str) -> list[str]:
        
        scores   = self.bm25_index.get_scores(query.lower().split())
        top_idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.top_k * 2]
        return [self.all_chunks[i] for i in top_idxs]

    @staticmethod
    def _reciprocal_rank_fusion(list1: list[str], list2: list[str], k: int = 60) -> list[str]:
        #it basically compare and generate the top score answers for external knowledge base
        scores: dict[str, float] = {}
        for rank, text in enumerate(list1):
            scores[text] = scores.get(text, 0.0) + 1.0 / (rank + k)
        for rank, text in enumerate(list2):
            scores[text] = scores.get(text, 0.0) + 1.0 / (rank + k)
        return sorted(scores, key=lambda t: scores[t], reverse=True)