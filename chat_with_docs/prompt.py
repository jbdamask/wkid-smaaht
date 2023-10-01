from langchain.prompts import PromptTemplate
CONCISE_SUMMARY_PROMPT_TEMPLATE = """Write a concise, comprehensive summary of the following:


"{text}"


CONCISE SUMMARY:"""

CONCISE_SUMMARY_PROMPT = PromptTemplate(
    template=CONCISE_SUMMARY_PROMPT_TEMPLATE, 
    input_variables=["text"]
)  