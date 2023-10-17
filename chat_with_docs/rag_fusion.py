from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from .prompt import QUESTION_VARIANT_PROMPT

class RagFusion:
    """Class for generating multiple questions from seed."""

    def __init__(self, openai_api_key, vectordb):
        self.OPENAI_API_KEY = openai_api_key
        self.embeddings = OpenAIEmbeddings(openai_api_key = openai_api_key)
        self.db = vectordb

    def generate_question_variants(self, question):
        llm = ChatOpenAI(model_name='gpt-3.5-turbo', temperature=0.6, openai_api_key=self.OPENAI_API_KEY, streaming=True)
        # results_docs = {}
        formatted_template = QUESTION_VARIANT_PROMPT.format_messages(text=question)
        results = llm(formatted_template)
        return results.content.split('\n')

    # Direct lookup against vectorstore. Arguably, this should be in another class but it's currently single-purpose
    def db_lookup(self, question, search_kwargs=""):
        if not question:
            return
        emb = self.embeddings.embed_query(question)
        return self.db.similarity_search_by_vector_with_relevance_scores(emb, k=4, search_kwargs=search_kwargs)
        
    def reciprocal_rank_fusion(self, search_results_dict, k=60):
        fused_scores = {}
        doc_ranks = {}
        for query, search_results_list in search_results_dict.items():
            fused_scores[query] = {}
            # Filter out any empty elements
            if search_results_list is None:
                continue
            for doc, score in sorted(search_results_list, key=lambda x: x[1], reverse=True):
                doc_name = doc.metadata['filename']
                doc_ranks[doc_name] = doc_ranks.get(doc_name, 0) + 1
                rank = doc_ranks[doc_name]
                fused_scores[query][doc_name] = 1 / (rank + k)

            fused_scores[query] = {doc: score for doc, score in sorted(fused_scores[query].items(), key=lambda x: x[1], reverse=True)}

        return fused_scores    