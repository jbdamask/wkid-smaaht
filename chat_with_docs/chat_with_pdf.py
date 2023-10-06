from src.logger_config import get_logger
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings

# Configure logging
logger = get_logger(__name__)


class ChatWithDoc:
    def __init__(self, doc):
        self.doc = doc
        # self.client = chromadb.Client()

    def load(self, documents, openai_api_key):
        """Load data for the chat."""
        # documents = SimpleDirectoryReader('data').load_data()
        # index = VectorStoreIndex.from_documents(documents)
        # split it into chunks
        embeddings = OpenAIEmbeddings(openai_api_key = openai_api_key)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)
        # load it into Chroma
        self.db = Chroma.from_documents(docs, embeddings)        
        logger.info("Documents loaded successfully")

    def query(self, question):
        """Query the chat with a question."""
        if self.db is None:
            print("No data loaded. Please load data first.")
            return
        # Here you can add code to process the question and return an answer based on the loaded data.
        print(f"Processing the question: {question}")
        return self.db.similarity_search(question)