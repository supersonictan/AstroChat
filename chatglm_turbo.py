# -*- coding: utf-8 -*-

import os
import random
import time
from typing import Dict, List
import streamlit as st
import torch
import zhipuai
from utils import greeting_msg, greeting_msg2
from utils import init_llm_knowledge_dict, time_loc_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task
from utils import _prepare_http_data, _fetch_ixingpan_soup
from utils import prompt_time_loc

class FakeData:
    def __init__(self, data):
        self.data = data


def do_pipeline(bot_msg) -> str:
    queue = st.session_state.task_queue
    if len(queue) == 0:
        # TODO: 解盘结束，欢迎继续咨询每年运势
        pass

    cur_task = queue[0]

    if cur_task == time_loc_task:
        birthday, dist, is_dst, toffset, loc = _prepare_http_data(bot_msg)
        soup_ixingpan = _fetch_ixingpan_soup(dist=dist, birthday_time=birthday, dst=is_dst, female=1)

        print(birthday, dist, is_dst, toffset, loc)

        if birthday != '无' and loc != '无' and dist != '':
            st.session_state.task_queue.remove(time_loc_task)
            st.session_state.task_queue.remove(time_task)
            st.session_state.task_queue.remove(loc_task)

            msg = f'\n\n将按如下信息排盘：<br>出生日期:{birthday}\t出生地点:{loc}\t区域ID:{dist}\t日光时:{is_dst}'
            return msg


def check_birthday_and_loc():
    day, loc = False, False
    if st.session_state.birthday != '':
        day = True

    if st.session_state.birthloc != '':
        loc = True

    return day, loc


def ask_birthinfo() -> List[FakeData]:
    has_day, has_loc = False, False
    if st.session_state.birthday != '':
        has_day = True

    if st.session_state.birthloc != '':
        has_loc = True

    if not has_day and not has_loc:
        msg = '您还没有输入出生时间和地点哦~~  参考输入：\n>出生时间: 2000.06.06 09:58；地点: 山东省济南市历下区'
        response = fake_robot_response(msg)
    elif not has_day:
        msg = '请输入正确的出生时间哦~~  最好精确到小时(默认12点排盘)，参考输入：\n>出生时间: 2000.06.06 09:58'
        response = fake_robot_response(msg)
    elif not has_loc:
        msg = '请输入正确的出生地哦~~  最好精确到区/县呢，参考输入：\n>地点: 山东省济南市历下区'
        response = fake_robot_response(msg)

    return response


def add_user_history(text):
    msg = {'role': 'user', 'content': text}
    st.session_state.history.append(msg)


def add_robot_history(text):
    msg = {'role': 'assistant', 'content': text}
    st.session_state.history.append(msg)


def fake_robot_response(text):
    blocks = []
    while len(text) > 5:
        block_length = random.randint(2, 5)
        block = text[:block_length]

        d = FakeData(data=block)
        blocks.append(d)
        text = text[block_length:]

    # 处理剩余的文本
    if len(text) > 0:
        d = FakeData(data=text)
        blocks.append(d)

    return blocks


def fetch_chatglm_turbo_response(user_input):
    if st.session_state.cur_task == time_loc_task:
        user_input = prompt_time_loc.format(user_input)

    response = zhipuai.model_api.sse_invoke(
        model="chatglm_turbo",
        prompt=[
            {"role": "user", "content": user_input},
        ],
        temperature=0.95,
        top_p=0.7,
        incremental=True
    )

    # return response
    return response.events()


# 设置页面标题、图标和布局
st.set_page_config(page_title="桥下指北", page_icon=":robot:")
# st.set_page_config(page_title="桥下指北", page_icon=":robot:", layout="wide")

# 初始化历史记录和past key values
if "history" not in st.session_state:
    st.session_state.history = [{'role': "assistant", 'content': f'{greeting_msg}'}]
    add_robot_history(greeting_msg2)
    st.session_state.llm_dict = init_llm_knowledge_dict()
    print('llm_dict size:', len(st.session_state.llm_dict))

    zhipuai.api_key = st.session_state.llm_dict['chatglm_turbo']['token']

    st.session_state.task_queue = [time_loc_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task]
    st.session_state.cur_task = time_loc_task
    st.session_state.birthday = ''
    st.session_state.birthloc = ''

if "past_key_values" not in st.session_state:
    st.session_state.past_key_values = None


# 渲染聊天历史记录
for i, message in enumerate(st.session_state.history):
    if message["role"] == "user":
        with st.chat_message(name="user", avatar="user"):
            st.markdown(message["content"])
    else:
        with st.chat_message(name="assistant", avatar="assistant"):
            st.markdown(message["content"])

# 输入框和输出框
with st.chat_message(name="user", avatar="user"):
    input_placeholder = st.empty()
with st.chat_message(name="assistant", avatar="assistant"):
    message_placeholder = st.empty()

# 获取用户输入
user_input = st.chat_input("请输入问题... ")
if len(st.session_state.task_queue) > 0 and st.session_state.task_queue[0] == time_loc_task:
    user_input = st.chat_input("例如输入：1992年8月4日 9点58分 地点:山东省济南市历下区")

# user_input = st.text_input("请输入问题... ", value='出生时间: 2024.01.01 09:58  地点:山东省济南市历下区')

# 如果用户输入了内容,则生成回复
if user_input:
    input_placeholder.markdown(user_input)
    add_user_history(user_input)

    # if len(st.session_state.task_queue) != 0 and time_loc_task in st.session_state.task_queue:
    #     response = ask_birthinfo()
    # else:
    response = fetch_chatglm_turbo_response(user_input)

    llm_flag = False
    res_vec = []
    for event in response:
        response_data = event.data
        res_vec.append(response_data)

        if isinstance(event, FakeData):
            time.sleep(0.05)
        else:
            llm_flag = True
        message_placeholder.markdown(''.join(res_vec))

    if llm_flag:
        pipeline_msg = do_pipeline(bot_msg=''.join(res_vec))

        res_vec.append(pipeline_msg)
        message_placeholder.markdown(''.join(res_vec))

    # history.append({'content': ''.join(res_vec), 'role': "assistant"})
    add_robot_history(''.join(res_vec))

    # 更新历史记录和past key values
    # st.session_state.history = history
    # st.session_state.past_key_values = past_key_values
