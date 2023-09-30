from llama_index import VectorStoreIndex, SimpleDirectoryReader
from localsrc.logger_config import get_logger


# Configure logging
logger = get_logger(__name__)


class ChatWithDoc:
    def __init__(self):
        self.index = None

    def load(self, data):
        """Load data for the chat."""
        documents = SimpleDirectoryReader('data').load_data()
        index = VectorStoreIndex.from_documents(documents)
        self.index = index
        logger.info("Documents loaded successfully")

    def query(self, question):
        """Query the chat with a question."""
        if self.data is None:
            print("No data loaded. Please load data first.")
            return
        # Here you can add code to process the question and return an answer based on the loaded data.
        print(f"Processing the question: {question}")

