from taipy.gui import Gui, notify
import re
import DG_for_fu
import pandas as pd
path = None
path2 = None
data = None
data2 = None
rest_data = None
pause = False
filename = None
editable = False
prompt_editable = False
table_editable = False
table_data = []
table_data_format = []
progress_value = 0
progressbar_show = False
button_clickable = False
Button_prompt_text = "启用编辑提示词"
prompt_template = DG_for_fu.prompt
temp = DG_for_fu.temp
total = 0
status = ("warning", "目前处于暂停状态，继续生成请点击QA生成")
count = 1

Button_text = "编辑文档"
BASE_URL = DG_for_fu.BASE_URL
API_KEY = DG_for_fu.API_KEY
root_md = "<|toggle|theme|>\n<center>\n<|navbar|>\n</center>"
page1 = """

<|{path}|file_selector|label=上传需要清理的文件|on_action=load_txt_file|extensions=.csv,.txt|>
<|数据清理|button|on_action=button_pressed|>
<|{path}|file_download|label=下载清洗后文件|on_action=after_download|>

<|layout|columns=1 1|
<|{filename}|text|mode=pre|>

<|{Button_text}|button|on_action=active_edit|>


|>
<|{data}|input|multiline=True|width=2800|active={editable}|>

"""
page2 = """


<|刷新|button|on_action=refresh|>
<|QA开始生成|button|on_action=start_gen|active={not button_clickable}|>
<|暂停|button|on_action=on_pause|active={button_clickable}|>

<|{progress_value}|progress|title=正在生成：{count-1}/{total}|title_anchor=top|show_value|linear=True|render={progressbar_show}|>
<|{table_data_format}|table|rebuild=True|editable={not button_clickable}|downloadable=True|>
<|保存至csv|button|on_action=save_csv|>

"""
page3 = """



"""

page4 = """
<|{Button_prompt_text}|button|on_action=active_prompt_edit|>

<|{prompt_template}|input|multiline=True|width=1400|active={prompt_editable}|> 

当前温度是：<|{temp}|slider|min=0.1|max=1.0|on_change=slider_change|step=0.1|label=温度|>

BASE_URL: <|{BASE_URL}|input|width=400|on_change=change_base_url|>

API_KEY: <|{API_KEY}|input|width=400|on_change=change_api_key|password=True|>

"""
md = {
    "/": root_md,
    "Text_Clean": page1,
    "QA_Gen": page2,
    "Card_Quest": page3,
    "Settings": page4,
}


# def load_csv_file(state):
#     state.table_data = pd.read_csv(state.path2)

# def save_csv(state):
#     df = pd.DataFrame(state.table_data_format)
#     df.to_csv('dataset.csv', encoding='utf-8', index=False)


def change_base_url(state):
    DG_for_fu.BASE_URL = state.BASE_URL
def change_api_key(state):
    DG_for_fu.API_KEY = state.API_KEY
    DG_for_fu.change_API()

def slider_change(state):
    DG_for_fu.temp = state.temp




def active_prompt_edit(state):
    if state.prompt_editable == False:
        state.prompt_editable = True
        state.Button_prompt_text = "保存提示词"
    else:
        state.prompt_editable = False
        state.Button_prompt_text = "启用编辑提示词"
        DG_for_fu.prompt = state.prompt_template





def refresh(state):
    notify(state, 'info', f'当前QA数据为: {state.table_data_format}')
    state.path = None
    state.path2 = None
    state.data = None
    state.data2 = None
    state.rest_data = None
    state.pause = False
    state.filename = None
    state.editable = False
    state.table_editable = False
    state.table_data = []
    state.table_data_format = []
    state.progress_value = 0
    state.progressbar_show = False
    state.button_clickable = False

    state.count = 1
    state.Button_text = "编辑文档"

def start_gen(state):
    if state.data != None:
        state.button_clickable = True
        state.progressbar_show = True
        state.pause = False
        DG_for_fu.generate_dataset(state)
    else:
        notify(state,'error','请先在文档清理处加载文档数据')

#c
def on_pause(state):

        state.pause = True
        state.button_clickable = False

def refresh_table(state):
    state.rest_data = state.data
    state.filename = state.path.split('/')[-1]
    state.total = len(state.data.splitlines())
    state.table_data_format = {
        "text": state.data.split('\n'),
        "instruction": [None] * len(state.data.splitlines()),
        "input": [None] * len(state.data.splitlines()),
        "output": [None] * len(state.data.splitlines()),
    }
    state.data2 = state.data

def load_txt_file(state):
    with open(state.path, 'r', encoding='utf-8') as f:
        state.data = f.read()
        refresh_table(state)

def button_pressed(state):
    state.data = clean_text(filter_lines(state.data))
    refresh_table(state)
    with open(state.path, 'w', encoding='utf-8') as outfile:
        outfile.write(state.data)


def active_edit(state):
    if state.editable == False:
        state.editable = True
        state.Button_text = "保存文档"
    else:
        refresh_table(state)
        state.editable = False
        state.Button_text = "编辑文档"
        state.data2 = state.data
        with open(state.path, 'w', encoding='utf-8') as outfile:
            outfile.write(state.data)
def after_download(state):
    state.path = None
def clean_text(text):
    cleaned_lines = []
    current_section = None
    for line in text.split('\n'):
        line = line.strip()  # 去掉行首尾空白
        if re.match(r'^[\dA-Z]+\.\s*\d+', line):  # 如果是小节标题，包括可能的空格
            if current_section:  # 如果已有小节，保存当前小节
                cleaned_lines.append(current_section)
            current_section = line  # 更新当前小节
        elif current_section:  # 如果是内容行且已有小节标题
            content = line.strip()  # 保留内容行
            current_section += ' ' + content  # 合并到当前小节

    if current_section:  # 保存最后的小节
        cleaned_lines.append(current_section)

    return '\n'.join(cleaned_lines)






def filter_lines(input_string):
    lines = input_string.splitlines()
    filtered_lines = []

    for line in lines:
        line = line.replace('本系统所提供的电子文本近供参考，请以正式标准出版物为准。','')
        line = line.replace('本系统所提供的电子文本仅供个人学习、研究之用，未经授权，禁止复制、发行、汇编、翻译或网络传播等，侵权必究。','')
        line = line.replace(' ', '')
        print(line)
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

if __name__ == "__main__":
    Gui(pages=md).run(port="auto")