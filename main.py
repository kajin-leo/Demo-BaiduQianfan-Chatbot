# coding=utf-8
import hashlib
import json
import logging
import math
import os
import time

import qianfan
from flask import Flask, request, Blueprint, Response
from langchain.chains import RetrievalQA
from langchain.chains import create_retrieval_chain
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings import QianfanEmbeddingsEndpoint
from langchain_community.llms import QianfanLLMEndpoint
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_text_splitters import RecursiveCharacterTextSplitter

app = Flask(__name__)
chatbot_api = Blueprint('chatbot', __name__)
logging.root.setLevel('INFO')
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ['QIANFAN_AK'] = ""
os.environ['QIANFAN_SK'] = ""
llm_model_name = "ERNIE-4.0-8K"
embeddings_model_name = "tao-8k"
kwargs = {
    'max_output_tokens': 2000
}
model = QianfanLLMEndpoint(model=llm_model_name, streaming=True, init_kwargs=kwargs)
embeddings = QianfanEmbeddingsEndpoint(model=embeddings_model_name)
persist_directory = "/chromadb"
qianfan.enable_log()


class ChatBot:
    @staticmethod
    def clear_vector_database():
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        vectorstore.delete_collection()
        hashmap_json = {}
        with open(os.path.join(".venv/hash.json"), "w") as f:
            json.dump(hashmap_json, f)
        logging.info("向量数据库内容已清除")
        return json.dumps({"output": "cleared"})

    @staticmethod
    def get_hash(file):
        return hashlib.sha256(file.page_content.encode()).hexdigest()

    @staticmethod
    def process_files():
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        hashmap_json = {}
        if os.path.exists(".venv/hash.json"):
            hashmap_json = json.load(open(".venv/hash.json"))
        else:
            with open(os.path.join(".venv/hash.json"), "w") as f:
                json.dump(hashmap_json, f)
        loader = DirectoryLoader(".venv/data", glob="*.csv", loader_cls=CSVLoader)
        docs = loader.load()
        docs_to_upload = []
        # print(f"HashMap: {hashmap_json}")
        for doc in docs:
            hash_value = ChatBot.get_hash(doc)
            if hash_value in hashmap_json:
                continue
            else:
                docs_to_upload.append(doc)
                hashmap_json[hash_value] = "1"

        if len(docs_to_upload) == 0:
            logging.info(f"没有需要上传的文档")
            yield json.dumps({"output": "finished - no changes made"})
            return

        logging.info(f"文档长度：{len(docs)}")
        logging.info(f"需要上传的文档长度：{len(docs_to_upload)}")
        if embeddings_model_name == "tao-8k":
            split_unit = 2048
            overlap_size = 200
        elif embeddings_model_name == "bge-large-zh":
            split_unit = 512
            overlap_size = 100
        else:
            split_unit = 384
            overlap_size = 80
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=split_unit, chunk_overlap=overlap_size)
        splits = text_splitter.split_documents(docs_to_upload)
        if embeddings_model_name == "tao-8k":
            logging.warning("tao-8k Embeddings接口不支持文件批量上传转换为索引值且有QPS(Query Per Second)限制，将尝试依次上传。"
                            f"共{len(splits)}个文件切片，上传过程将持续约{math.ceil(len(splits)/60)}分钟。")
            i = 0
            time.sleep(1)
            for document in splits:
                vectorstore.add_documents(documents=[document],
                                          embedding=embeddings,
                                          persist_directory=persist_directory)
                time.sleep(0.6)
                logging.info(f"当前进度：{i}/{len(splits)}")
                yield json.dumps({"output": f"进度{i/len(splits)*100:.2f}%"})
                i += 1
            logging.info("文本切片已全部上传")
        else:
            vectorstore.from_documents(documents=splits,
                                       embedding=embeddings,
                                       persist_directory=persist_directory)
        with open(os.path.join(".venv/hash.json"), "w") as f:
            json.dump(hashmap_json, f)
        logging.info(f"库中文本数量：{vectorstore._collection.count()}")
        test_text = "这是一条测试文本"
        test_embedding = embeddings.embed_query(test_text)
        logging.info(f"嵌入检查：{len(test_embedding)}")
        yield json.dumps({"output": "uploaded"})
        return

    @staticmethod
    def check_vector_storage():
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        library_name = vectorstore._collection.name
        library_count = vectorstore._collection.count()
        logging.info(f"库名：{library_name}")
        logging.info(f"库内内容数：{library_count}")
        return json.dumps({"library_name": f"{library_name}", "library_count": f"{library_count}"})

    @staticmethod
    def response(query_content: str, is_chat: bool):
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        retriever = vectorstore.as_retriever()
        system_prompt = [
            '''
            你是奇米有限公司的一个聊天机器人。你的工作是从给定的背景信息里找出答案。背景信息是公司的Wiki库。                                                 
            你必须根据给出的Wiki来完整回答，不可以参考其他信息源，包括互联网和你可能拥有的任何其他知识。                        
            回答尽量完整，不需要你对Wiki内容进行总结，请尽量原句复述。请尽量囊括足够多的Wiki信息。                                                                                                                  
            在回答的最后，你可以提醒用户在Wiki中再次确认信息以确保准确性。
            重要的是，在回答的最开始把对应来源展示成“https://oa.chimitan.com/?/wiki/view/about/”+uuid的链接形式。
            （比如“奇米蛋和不知鸟是什么关系？”，你首先要回答这个问题的对应链接是https:/oa.chimitan.com/?/wiki/view/about/a3b4c2d1，
            然后再说你的答案），如果找不到来源，也请如实说明。                                                       
            以下是背景信息：{context}\n
            这是问题：{question}
            ''',
            '''
            你是奇米有限公司的一个聊天机器人。你的工作是帮助公司的同事解决问题。                       
            回答尽量完整，尽量囊括足够多的背景信息。                                                                       
            在回答的最后，你可以提醒用户自行再次确认信息以确保准确性。                                                          
            \n
            '''
        ]
        if not is_chat:
            qa_chain_prompt = PromptTemplate(input_variables=["context", "question"], template=system_prompt[0])
            qa_chain = RetrievalQA.from_chain_type(
                llm=model,
                retriever=retriever,
                chain_type_kwargs={"prompt": qa_chain_prompt}
            )
            docs = retriever.invoke(input=query_content, search_kwargs={"k": 5})
            context = "\n".join([doc.page_content for doc in docs])
            qa_chain_prompt = PromptTemplate(input_variables=["context", "question"], template=system_prompt[0])
            chain = qa_chain_prompt | model
            for chunk in chain.stream({"context": context, "question": query_content}):
                yield json.dumps({"output": chunk})
        else:
            qa_chain_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt[1]),
                    MessagesPlaceholder(variable_name="message")
                ]
            )
            chain = qa_chain_prompt | model
            for chunk in chain.stream({"message": [HumanMessage(content=query_content)]}):
                yield json.dumps({"output": chunk})


@chatbot_api.route("/clear", methods=["POST"])
def clear():
    return ChatBot.clear_vector_database()


@chatbot_api.route("/check", methods=["POST"])
def check():
    response = ChatBot.check_vector_storage()
    return Response(response)


@chatbot_api.route("/upload", methods=["POST"])
def upload():
    return Response(ChatBot.process_files(), mimetype="text/event-stream")


@chatbot_api.route("/wiki", methods=["POST"])
def wiki():
    try:
        text = request.get_json()["content"]
        response = ChatBot.response(query_content=text, is_chat=False)
    except:
        response = "执行遇到问题，请重试"
    # return jsonify({"output": response})
    return Response(response, mimetype="text/event-stream")

@chatbot_api.route("/completion", methods=["POST"])
def completion():
    try:
        text = request.get_json()["content"]
        response = ChatBot.response(query_content=text, is_chat=True)
    except:
        response = "执行遇到问题，请重试"
    return Response(response, mimetype="text/event-stream")


@chatbot_api.route("/", methods=["POST"])
def home():
    return json.dumps({"output": "hello"})


app.register_blueprint(chatbot_api, url_prefix="/chatbot")
if __name__ == "__main__":
    app.run(host="localhost", port=8204, debug=True)

