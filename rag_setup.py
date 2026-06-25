from pathlib import Path
import shutil

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


RUNBOOK_DIR = Path("data/runbooks")
CHROMA_DIR = Path("chroma_runbooks")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_runbooks():
    loader = DirectoryLoader(
        str(RUNBOOK_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    return loader.load()


def build_vectorstore():
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    documents = load_runbooks()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    return vectorstore


def get_retriever():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 3})


if __name__ == "__main__":
    vectorstore = build_vectorstore()
    print(f"Loaded runbooks from {RUNBOOK_DIR}")
    print(f"Persisted ChromaDB to {CHROMA_DIR}")
    print(f"Stored chunks: {vectorstore._collection.count()}")
