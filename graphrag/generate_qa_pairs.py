import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils import config_model, generate_response_text
import time
import re

import pandas as pd
import tiktoken

from graphrag.query.indexer_adapters import read_indexer_entities, read_indexer_reports
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch

# Read data from Parquet file into DataFrame
community_reports_list = []
df = pd.read_parquet('create_final_community_reports.parquet')
for index, row in df.iterrows():
    community_reports_list.append(row['summary'])
    
api_key = 'DEFINE_API_SERVICE_KEY'
llm_model = 'DEFINE_MODEL_NAME'
BASE_URL = 'DEFINE_API_BASE_URL'
model = config_model(api_key, BASE_URL)

llm = ChatOpenAI(
    api_key=api_key,
    model=llm_model,
    api_base="https://api.siliconflow.cn/v1",
    max_retries=20,
)

token_encoder = tiktoken.get_encoding("cl100k_base") # could be modified to use other token encoders

# parquet files generated from indexing pipeline
INPUT_DIR = "DEFINE_INPUT_DIR"
COMMUNITY_REPORT_TABLE = "artifacts/create_final_community_reports"
ENTITY_TABLE = "artifacts/create_final_nodes"
ENTITY_EMBEDDING_TABLE = "artifacts/create_final_entities"

# community level in the Leiden community hierarchy from which we will load the community reports
# higher value means we use reports from more fine-grained communities (at the cost of higher computation cost)
COMMUNITY_LEVEL = 0

entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
entity_embedding_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_EMBEDDING_TABLE}.parquet")

reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)


context_builder = GlobalCommunityContext(
    community_reports=reports,
    entities=entities,  # default to None if you don't want to use community weights for ranking
    token_encoder=token_encoder,
)

context_builder_params = {
    "use_community_summary": False,  # False means using full community reports. True means using community short summaries.
    "shuffle_data": True,
    "include_community_rank": True,
    "min_community_rank": 0,
    "community_rank_name": "rank",
    "include_community_weight": True,
    "community_weight_name": "occurrence weight",
    "normalize_community_weight": True,
    "max_tokens": 2048,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    "context_name": "Reports",
}

map_llm_params = {
    "max_tokens": 2048,
    "temperature": 0.0,
    "response_format": {"type": "json_object"}
}

reduce_llm_params = {
    "max_tokens": 2048,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000-1500)
    "temperature": 0.0
}

search_engine = GlobalSearch(
    llm=llm,
    context_builder=context_builder,
    token_encoder=token_encoder,
    max_data_tokens=2048,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    map_llm_params=map_llm_params,
    reduce_llm_params=reduce_llm_params,
    allow_general_knowledge=False,  # set this to True will add instruction to encourage the LLM to incorporate general knowledge in the response, which may increase hallucinations, but could be useful in some use cases.
    json_mode=False,  # set this to False if your LLM model does not support JSON mode.
    context_builder_params=context_builder_params,
    concurrent_coroutines=32,
    response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
)

import asyncio

async def main():
    instruction_answer_list = []
    generated_question_list = []
    for index, summary in enumerate(community_reports_list):
        while True:
            try:
                prompt = f"请你根据下方这个描述来生成一个问题，这个问题无需局限于下面这个描述本身，只是以这个描述为基准，自由地提问，提问的内容应该是一个电力市场相关的专业问题。直接输出一个中文的问题即可: \n{summary}"
                question = generate_response_text(model, prompt, temperature=1, model_name=llm_model)
                generated_question_list.append(question)
                result = await search_engine.asearch(f"请用中文回答以下问题：\n{question}")
                output = result.response
                if "sorry" in output:
                    break
                cleaned_output = re.sub(r'\[Data:.*?\]', '', output)
                temp_dict = {
                    "input": question,
                    "output": cleaned_output
                }
                instruction_answer_list.append(temp_dict)
                
                if index % 10 == 0:
                    with open('generated_question_list.json', 'w', encoding='utf-8') as f:
                        json.dump(generated_question_list, f, ensure_ascii=False, indent=4)
                    with open('instruction_answer_list.json', 'w', encoding='utf-8') as f:
                        json.dump(instruction_answer_list, f, ensure_ascii=False, indent=4)
                
                print(f'{index}/{len(community_reports_list)} is finished')
                break
            except:
                time.sleep(60)
                
    

# Run the main function
asyncio.run(main())