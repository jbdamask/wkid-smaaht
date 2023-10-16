from langchain.chat_models import ChatOpenAI
from prompt import QUESTION_VARIANT_PROMPT

class RagFusion:
    """Class for generating multiple questions from seed."""

    # Function to generate queries using OpenAI's ChatGPT
    def generate_queries_chatgpt(user_text, openai_api_key):
        llm = ChatOpenAI(openai_api_key=openai_api_key)
        formatted_template = QUESTION_VARIANT_PROMPT.format_messages(text=user_text)
        results = llm(formatted_template)
        return results.content.split("\n")
