import langchain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentType, load_tools
from langchain.document_loaders import PyPDFLoader, OnlinePDFLoader
# from custom_agent_types import CustomAgentType
import pandas as pd
import abc
import os
import requests
from io import StringIO
from localsrc.logger_config import get_logger
langchain.verbose = True

# Configure logging
logger = get_logger(__name__)

class Handler(abc.ABC):

    first_impression = "What's this file about?"

    def __init__(self, file, openai_api_key):
        _, file_extension = os.path.splitext(file)
        self.file_type = file_extension.lstrip('.').lower()
        self.file = file
        self.openai_api_key = openai_api_key
        self.llm = ChatOpenAI(temperature=0,openai_api_key=self.openai_api_key)
        # self.llm = OpenAI(temperature=0,openai_api_key=self.openai_api_key)

    # def handle(self, file):
    def handle(self):
        raise NotImplementedError
    
    @abc.abstractmethod
    def read_file(self):
        pass

    # def read_file(self, url, SLACK_BOT_TOKEN):
    #     self.file_content = self._read_file_content(url, SLACK_BOT_TOKEN)

    def _read_file_content(self, url, SLACK_BOT_TOKEN) :
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        response = requests.get(url, headers=headers)
        return response.content
    
    def q_and_a(self, question):
        # Assumes an agent has been configured. 
        result = None
        try:
            result = self.agent.run(question)
        except Exception as e:
            logger.error(e)
            result = "Sorry, I ran into a problem with the file"
        return result
        # return self.agent(question) # This invokes the default __call__ method

class PandasWrapperHandler(Handler):
    def handle(self):
        return f"Wrapping {self.file} in Pandas dataframe"
    
    # def read_file(self):
    #     pass

    def _create_agent(self):
        self.df.columns = self.df.columns.str.strip()
        tools = load_tools(["python_repl"], llm=self.llm)
        self.agent = create_pandas_dataframe_agent(
            tools=tools, 
            llm=self.llm, 
            df=self.df, 
            verbose=True, 
            # These are the only two agents impelemnted for pandas at the moment
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            # agent_type=AgentType.OPENAI_FUNCTIONS,
            # max_execution_time=2,
            # early_stopping_method="generate",
            format_instructions = FORMAT_INSTRUCTIONS
            )

class PDFHandler(Handler):
    def handle(self):
        return f"Handling PDF file: {self.file}"

    def read_file(self, url, SLACK_BOT_TOKEN):
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        logger.info(url)
        loader = OnlinePDFLoader(url, headers=headers)
        pages = loader.load_and_split()
        return pages
        # from langchain.prompts import PromptTemplate
        # from langchain.chains.summarize import load_summarize_chain
        # prompt_template = """Write a concise, comprehensive summary of the following:


        # "{text}"


        # CONCISE SUMMARY:"""
        # PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])  
        # llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k", openai_api_key=self.openai_api_key)        
        # chain = load_summarize_chain(llm, chain_type="map_reduce", map_prompt=PROMPT, combine_prompt=PROMPT)
        # result = chain.run(pages)
        # return result

class DOCXHandler(Handler):
    def handle(self):
        return f"Handling DOCX file: {self.file}"
    
    def read_file(self):
        pass    

# class ExcelHandler(Handler):
class ExcelHandler(PandasWrapperHandler):
    def handle(self):
        return f"Handling Excel file: {self.file}"
    
    def read_file(self, url, SLACK_BOT_TOKEN): 
        file_content = self._read_file_content(url, SLACK_BOT_TOKEN)
        self.df = pd.read_excel(file_content, sheet_name=0)                   
        # df.columns = df.columns.str.strip()
        # tools = load_tools(["llm-math"], llm=self.llm)
        # self.agent = create_pandas_dataframe_agent(
        #     tools=tools, 
        #     llm=self.llm, 
        #     df=df, 
        #     verbose=True, 
        #     agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        #     max_execution_time=1,
        #     early_stopping_method="generate"
        #     )
        self._create_agent()
        return self.q_and_a(self.first_impression)
        
class CSVHandler(PandasWrapperHandler):
    def handle(self):
        return f"Handling CSV file: {self.file}"

    def read_file(self, url, SLACK_BOT_TOKEN):  
        file_content = self._read_file_content(url, SLACK_BOT_TOKEN).decode('utf-8')
        self.df = pd.read_csv(StringIO(file_content))     
        # df.columns = df.columns.str.strip()
        # tools = load_tools(["llm-math"], llm=self.llm)        
        # self.agent = create_pandas_dataframe_agent(tools=tools, llm=self.llm, df=df, verbose=True, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
        # # print(agent.agent.llm_chain.prompt.template)
        # # return (agent.run(self.first_impression))     
        self._create_agent()
        return self.q_and_a(self.first_impression)
            # self.agent.run("What's the average rate of change from month to month?"))

class TxtHandler(Handler):
    def handle(self):
        return f"Handling txt file: {self.file}"  
    
    def read_file(self, url, SLACK_BOT_TOKEN):
        file_content = self._read_file_content(url, SLACK_BOT_TOKEN)

class JSONHandler(Handler):
    def handle(self):
        return f"Handling JSON file: {self.file}"   
    
    def read_file(self, url, SLACK_BOT_TOKEN):
        file_content = self._read_file_content(url, SLACK_BOT_TOKEN)
        str_content = file_content.decode('utf-8')
        df = pd.read_json(StringIO(str_content))
        df.columns = df.columns.str.strip()
        agent = create_pandas_dataframe_agent(OpenAI(temperature=0, openai_api_key=self.openai_api_key), df=df, verbose=True, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
        # print(agent.agent.llm_chain.prompt.template)

class MarkdownHandler(Handler):
    def handle(self):
        return f"Handling Markdown file: {self.file}"  

    def read_file(self):
        pass    

class HandlerFactory:
    handlers = {
        "pdf": PDFHandler, 
        "docx": DOCXHandler, 
        "xlsx": ExcelHandler, 
        "txt": TxtHandler,
        "json": JSONHandler,
        "md": MarkdownHandler,
        "csv": CSVHandler}

    @classmethod
    def get_handler(cls, file, open_api_key):
        _, file_extension = os.path.splitext(file)
        file_type = file_extension.lstrip('.').lower()
        Handler = cls.handlers.get(file_type)
        if Handler is None:
            raise ValueError(f"No handler for file type {file_type}")
        return Handler(file, open_api_key)

def create_file_handler(file, openai_api_key):
    handler = HandlerFactory.get_handler(file, openai_api_key)
    return handler
    # return handler.handle(file)