
from taipy.gui import notify
import csv
import json
import os
import time
import re
from typing import List, Dict
from openai import OpenAI
import logging
import backoff
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

temp = 0.4
BASE_URL = "https://api.together.xyz/v1"
API_KEY = ""
prompt = f"""
    基于以下文本，生成1个用于指令数据集的高质量条目。条目应该直接关联到给定的文本内容，提出相关的问题或任务。
    请确保生成多样化的指令类型，例如：
    - 问答类："...是什么？"

    "原文占位符，请勿删除"

    请以下面的格式生成条目，确保所有字段都有适当的内容：
    {{
        "instruction": "使用多样化的指令，提出多个具体的、与文本相关的问题（数量由句子数决定），请勿提及章节和书名。",
        "input": " ",
        "output": "根据《DL_T_5181-2017水电水利工程锚喷支护施工规范》的"+"句子中的序号"+"对instruction中多个问题的详细回答"
    }}
    确保所有生成的内容都与给定的文本直接相关，生成的是有效的JSON格式，并且内容高质量、准确、详细。基于文本，生成1个用于指令数据集的高质量条目。
    """
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化 OpenAI 客户端
#client = OpenAI(base_url="https://localhost:11434/v1", api_key="ollama")  # 替换为你的 API 密钥
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def change_API():
    global client
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
def read_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def generate_single_entry(text: str, prompt, temp) -> Dict:

    prompt = prompt.replace("原文占位符，请勿删除", f"文本内容：{text}")

    try:
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature= temp,  # 增加温度以提高多样性
            max_tokens=8196
        )
        logger.info(f"API 响应: {response.choices[0].message.content}")

        json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
        if json_match:
            entry = json.loads(json_match.group())
            required_keys = ['instruction', 'input', 'output']
            if isinstance(entry, dict) and all(key in entry for key in required_keys):
                # 根据 input 是否为空来设置 text 字段

                #entry['text'] = text
                logger.info("成功生成完整条目")
                return entry
            else:
                logger.warning("JSON 解析成功，但缺少必要字段")
                return {}
        else:
            logger.error("无法从API响应中提取有效的JSON")
            return {}

    except Exception as e:
        logger.error(f"生成条目时发生错误: {str(e)}")
        raise

def return_and_remove_first_line(text):
    lines = text.splitlines()
    if lines:
        first_line = lines.pop(0)
        text = '\n'.join(lines)
        return first_line, text
    else:
        return 0

def generate_dataset(state):
        text = state.rest_data
        rest = text

        while rest:
            if not state.pause:

                notify(state, 'info', f'正在生成第 {state.count} 个条目')
                logger.info(f"  正在生成第 {state.count} 个条目")
                state.rest_data = rest
                first_line, rest = return_and_remove_first_line(rest)

                print(first_line)
                print(state.pause)
                entry = generate_single_entry(first_line, prompt,temp)


                #if entry and all(key in entry for key in ['instruction', 'input', 'output', 'text']):
                if entry and all(key in entry for key in ['instruction', 'input', 'output']):
                    state.table_data.append(entry)
                    notify(state, 'success', f'成功生成 1 个完整条目')
                    logger.info(f"  成功生成 1 个完整条目")
                    state.progress_value = 100 * state.count / len(state.data.splitlines())
                    state.table_data_format["instruction"][state.count-1] = entry['instruction']
                    print(state.table_data)
                    state.table_data_format["input"][state.count-1] = entry['input']
                    state.table_data_format["output"][state.count-1] = entry['output']
                    state.count = state.count + 1
                    state.table_data_format = state.table_data_format
                else:
                    logger.warning(f"  跳过不完整的条目")
                # df = pd.DataFrame(state.table_data)
                # state.table_data_format = {
                #     "text": state.data.split('\n'),
                #     "instruction": df["instruction"].tolist(),
                #     "input": df["input"].tolist(),
                #     "output": df["output"].tolist(),
                #
                # }


                time.sleep(2)  # 在请求之间增加延迟到2秒
            else:
                  state.rest_data = rest
                  print("成功暂停")
                  break

def save_dataset_as_parquet(dataset: List[Dict], output_file: str):
    schema = pa.schema([
        ('instruction', pa.string()),
        ('input', pa.string()),
        ('output', pa.string()),

    ])

    arrays = [
        pa.array([entry['instruction'] for entry in dataset]),
        pa.array([entry['input'] for entry in dataset]),
        pa.array([entry['output'] for entry in dataset]),

    ]

    table = pa.Table.from_arrays(arrays, schema=schema)
    pq.write_table(table, output_file)

def save_dataset_as_csv(dataset: List[Dict], output_file: str):
    fieldnames = ['instruction', 'input', 'output']
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # 写入列名
        writer.writeheader()

        # 写入数据行
        for row in dataset:
            writer.writerow(row)



