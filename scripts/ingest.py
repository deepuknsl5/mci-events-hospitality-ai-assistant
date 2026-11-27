from app.rag.retriever import EventRetriever

if __name__ == "__main__":
    retriever = EventRetriever()
    count = retriever.ingest(reset=True)
    print(f"Ingested {count} event knowledge chunks.")
