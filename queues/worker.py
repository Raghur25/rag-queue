from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI

# The RQ worker is a separate process, so it must load .env itself
load_dotenv()

TOP_K = 10

openai_client = OpenAI()

embedding_model = OpenAIEmbeddings(
    model="embedding",
    check_embedding_ctx_length=False
    )

vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="learning_rag",
    embedding=embedding_model
)

def process_query(query: str):
    print(f"searching for chunks: {query}")

    search_results = vector_db.similarity_search(query=query, k=TOP_K)

    context = "\n\n\n".join([
        f"Page Content: {result.page_content}\n"
        f"Page Number: {result.metadata.get('page_label')}\n"
        f"File Location: {result.metadata.get('source')}"
        for result in search_results
    ])

    SYSTEM_PROMPT = f"""
You are a helpful assistant that answers questions based on the available context retrieved from a PDF file along with page_contents and page numbers.
 You should only answer the user based on the following context and navigate the user to open the right number to know more.
 {context}"""

    response = openai_client.chat.completions.create(
        model="qwen3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
    )

    answer = response.choices[0].message.content
    print(f"Bot: {answer}")
    return answer
