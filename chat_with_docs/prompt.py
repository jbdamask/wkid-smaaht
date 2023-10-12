from langchain.prompts import PromptTemplate
CONCISE_SUMMARY_MAP_PROMPT_TEMPLATE = """Write a concise summary of the following:


"{text}"


CONCISE SUMMARY:"""

CONCISE_SUMMARY_MAP_PROMPT = PromptTemplate(
    template=CONCISE_SUMMARY_MAP_PROMPT_TEMPLATE, 
    input_variables=["text"]
)  

CONCISE_SUMMARY_COMBINE_PROMPT_TEMPLATE = """Write a concise, comprehensive summary of the following:


"{text}"

Also provide up to five suggested follow-up questions as a bulleted list. Only include questions that are 
likely answerable by the text and are not already answered in the summary you provided.

CONCISE SUMMARY:"""

CONCISE_SUMMARY_COMBINE_PROMPT = PromptTemplate(
    template=CONCISE_SUMMARY_COMBINE_PROMPT_TEMPLATE, 
    input_variables=["text"]
)  


CONCISE_SUMMARY_PROMPT_TEMPLATE = """Write a concise, comprehensive summary of the following:


"{text}"


CONCISE SUMMARY:"""

CONCISE_SUMMARY_PROMPT = PromptTemplate(
    template=CONCISE_SUMMARY_PROMPT_TEMPLATE, 
    input_variables=["text"]
)  