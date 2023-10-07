import langchain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentType, load_tools
from langchain.document_loaders import PyPDFLoader, OnlinePDFLoader, UnstructuredWordDocumentLoader, UnstructuredFileLoader, WebBaseLoader
# from custom_agent_types import CustomAgentType
import pandas as pd
import abc
import os
import requests
from io import StringIO
from src.logger_config import get_logger
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

    # TODO - I think I can remove this
    def _read_file_content(self, url, SLACK_BOT_TOKEN) :
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        response = requests.get(url, headers=headers)
        return response.content
    
    # TODO - May or may not want to keep this method
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

    # Not all filetypes are accessible by LangChain over the web.
    # Some need to be downloaded locally
    def download_local_file(self, url, headers, directory='downloads'):
        import requests
        import uuid        
        file_type = url.split('.')[-1]
        response = requests.get(url, headers=headers)
        # Generate a random UUID
        file_uuid = uuid.uuid4()
        # Convert the UUID to a string and append the .docx extension
        filename = str(file_uuid) + '.' + file_type
        # Check if the directory exists and create it if it doesn't
        if not os.path.exists(directory):
            os.makedirs(directory)
        filepath = os.path.join(directory, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath

    # You slob. Clean up after yourself!
    def delete_local_file(self, filepath):
        if os.path.isfile(filepath):
            os.remove(filepath)

class PDFHandler(Handler):
    def handle(self):
        return f"Handling PDF file: {self.file}"

    def read_file(self, url, SLACK_BOT_TOKEN):
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        logger.info(url)
        loader = OnlinePDFLoader(url, headers=headers)
        self.documents = loader.load_and_split()
        return self.documents

class DOCXHandler(Handler):
    def handle(self):
        return f"Handling DOCX file: {self.file}"
    
    def read_file(self, url, SLACK_BOT_TOKEN):
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        logger.info(url)
        filename = self.download_local_file(url, headers)
        loader = UnstructuredWordDocumentLoader(filename, headers=headers)
        self.documents = loader.load_and_split()
        self.delete_local_file(filename)
        return self.documents             

class TxtHandler(Handler):
    def handle(self):
        return f"Handling txt file: {self.file}"  
    
    def read_file(self, url, SLACK_BOT_TOKEN):
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        logger.info(url)
        filename = self.download_local_file(url, headers)
        loader = UnstructuredFileLoader(filename, headers=headers)
        self.documents = loader.load_and_split()
        self.delete_local_file(filename)        
        return self.documents     

class WebHandler(Handler):
    def handle(self):
        return f"Handling web page: {self.file}"
    
    def read_file(self, url):
        logger.info(url)
        loader = WebBaseLoader(url)
        self.documents = loader.load_and_split()  
        return self.documents    
    
# TODO - Need to implement these 
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
    # Note - WebHandler isn't in here because this factory is based on 
    # filetype. Instead, we instantiate it directly if we know we're
    # dealing with a web page
    handlers = {
        "pdf": PDFHandler, 
        "docx": DOCXHandler, 
        "txt": TxtHandler,
        # "xlsx": ExcelHandler, 
        # "json": JSONHandler,
        # "md": MarkdownHandler,
        # "csv": CSVHandler,
        }

    @classmethod
    def get_handler(cls, file, open_api_key):
        _, file_extension = os.path.splitext(file)
        file_type = file_extension.lstrip('.').lower()
        Handler = cls.handlers.get(file_type)
        if Handler is None:
            raise ValueError(f"No handler for file type {file_type}")
        return Handler(file, open_api_key)

def create_file_handler(file, openai_api_key, webpage=False):
    if webpage:
        handler = WebHandler(file, openai_api_key)
    else:
        handler = HandlerFactory.get_handler(file, openai_api_key)
    return handler

class FileRegistry:
    def __init__(self):
        self.registry = {}

    def add_file(self, filename, channel_id, thread_ts, file_id, private_url, handler, chatWithDoc):
        if filename not in self.registry:
            self.registry[filename] = {}
        key = (channel_id, thread_ts)
        if key not in self.registry[filename]:
            self.registry[filename][key] = []
        self.registry[filename][key].append(
                {'file_id': file_id, 
                 'private_url': private_url, 
                 'handler': handler, 
                 'chat': chatWithDoc})

    def get_files(self, filename, channel_id, thread_ts):
        key = (channel_id, thread_ts)
        if filename in self.registry and key in self.registry[filename]:
            return self.registry[filename][key]
        else:
            return None

    def list_files(self, filename):
        if filename in self.registry:
            return [file for sublist in self.registry[filename].values() for file in sublist]
        else:
            return None
