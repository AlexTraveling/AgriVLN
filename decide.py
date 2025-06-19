from openai import OpenAI
import base64
from pathlib import Path
import re
import json

from prompt import get_system_prompt, get_user_prompt
from for_json import save_subtasks_to_file, load_subtasks_from_file, append_action
from for_json import get_stop_start_time, clean_format_stl_state


def extract(gpt_output):

   action_match = re.search(r"<action>\s*(.*?)\s*</action>", gpt_output, re.DOTALL)
   state_match = re.search(r"<state>\s*(.*?)\s*</state>", gpt_output, re.DOTALL)
   thought_match = re.search(r"<thought>\s*(.*?)\s*</thought>", gpt_output, re.DOTALL)

   result = {
      "action": action_match.group(1).strip() if action_match else None,
      "state": state_match.group(1).strip() if state_match else None,
      "thought": thought_match.group(1).strip() if thought_match else None
   }

   return result


def extract_state(text):

   match = re.search(r"NO\.(\d+)\s+changes from (\w+)\s+to (\w+)", text)
   if match:
      subtask_no = int(match.group(1))
      from_state = match.group(2)
      to_state = match.group(3)
      return subtask_no, from_state, to_state
   else:
      return None, None, None
   

def update_subtask_state(new_STL, number, old_state, new_state):
   # new_STL = copy.deepcopy(STL)  # 创建深拷贝，避免修改原对象
   # print(type(new_STL))
   # print(type(new_STL[0]))
   # print(new_STL[0])
   for subtask in new_STL:
      # print(subtask)
      if subtask.get("step") == number:
         current_state = subtask.get("state")
         if current_state == old_state:
            subtask["state"] = new_state
            print(f"✅ Subtask {number} updated from '{old_state}' to '{new_state}'.")
         else:
            print(f"⚠️ Subtask {number} not updated: current state is '{current_state}', expected '{old_state}'.")
         return new_STL

   print(f"❌ Subtask with step number {number} not found.")
   return new_STL


def append_stl_state(state_path, new_entry):
   try:
      with open(state_path, 'r') as f:
         data = json.load(f)
   except FileNotFoundError:
      data = []  # 如果文件不存在，创建一个新列表

   data.append(new_entry)

   with open(state_path, 'w') as f:
      # json.dump(data, f, indent=3)
      json.dump(data, f, indent=3, separators=(",", ": "))

   # print(f"✅ Appended new entry at time {new_entry['time']} to {state_path}")


def load_json(path):
   with open(path, 'r') as f:
      return json.load(f)
   

def merge_stl_and_state(stl_path, state_path, current_time):
   STL = load_json(stl_path)
   STL_states = load_json(state_path)

   # 将时间字符串转换为标准格式
   def time_str_to_float(time_str):
      minutes, tenths = time_str.split("'")
      return int(minutes) + int(tenths) / 10

   current_time_val = time_str_to_float(current_time)

   # 找到最近的（小于等于当前时间）状态快照
   closest_state = None
   for state_snapshot in STL_states:
      snapshot_time = time_str_to_float(state_snapshot['time'])
      if snapshot_time <= current_time_val:
         closest_state = state_snapshot
      else:
         break

   if closest_state is None:
      raise ValueError(f"No matching STL state found for time {current_time}")

   # 构造 step 到 state 的映射
   state_dict = {s['step']: s['state'] for s in closest_state['subtask_list']}

   # 合并 state 信息到 STL
   merged_STL = []
   for subtask in STL:
      step = subtask['step']
      merged_subtask = dict(subtask)  # 复制一份以免修改原始数据
      merged_subtask['state'] = state_dict.get(step, "unknown")  # fallback
      merged_STL.append(merged_subtask)

   return merged_STL


def decide(my_model, exp, place, id, api):

   # Lao Zhang API
   # client = OpenAI(
   #    api_key="sk-0EGoOpwuIIjPdNxi3f5a17EfA9F84bA88949841f0aBaAe4e", 
   #    base_url="https://api.laozhang.ai/v1"
   # )
   client = api

   t_a = 0
   t_b = 0
   t_b_interval = 2

   label_path = f"dataset/{place}_{id}/label.json"
   with open(label_path, "r") as f:
      labels = json.load(f)

   stop_start_time = get_stop_start_time(labels)
   print("🛑 STOP 动作起始时间：", stop_start_time)
   max_time = int(stop_start_time) + 1
   print(f'max time: {max_time}')

   stop_quantity = 0

   while t_a < max_time:

      t = f'{t_a}\'{t_b}' # time

      STL_path = f"runs/{exp}/{place}_{id}/STL.json"
      log_path = f"runs/{exp}/{place}_{id}/log.json"
   
      STL = merge_stl_and_state(STL_path, log_path, current_time=t)
      # STL = merge_stl_and_state(f'dataset/{place}_{id}/STL.json', f'dataset/{place}_{id}/log.json', current_time=t)
      
      system_prompt = get_system_prompt()
      user_prompt = get_user_prompt(STL)

      my_image = base64.b64encode(Path(f"dataset/{place}_{id}/frames/frame_{t}.jpg").read_bytes()).decode('utf-8')

      completion = client.chat.completions.create(
         model=my_model, 
         store=False,
         messages=[
            {"role": "system", 
            "content": system_prompt
            },
            {"role": "user", 
            "content": [{"type": "text", 
                        "text": user_prompt},
                        {"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{my_image}"}}]
            },
         ]
      )
      message = completion.choices[0].message

      # print()
      # print(f'【system】{system_prompt}')
      # print()
      # print(f'【user】{user_prompt}')
      # print()
      print(f'Time: {t}')
      # print()
      print(f'【{my_model}】', end=' ')
      print()
      print(message.content)
      print()

      result = extract(message.content)
      action = result['action']
      thought = result['thought']
      state = result['state']
      predict_path = f"runs/{exp}/{place}_{id}/predict.json"
      # predict_path = f"dataset/{place}_{id}/predict.json"
      append_action(predict_path, t, action, thought, state)

      if 'keep' in state:
         # print('keep yes')
         new_STL = STL

      if 'change' in state:
         # print('change yes')
         number, old_state, new_state = extract_state(state)
         # print('STL:')
         # print(STL)
         new_STL = update_subtask_state(STL, number, old_state, new_state)

      t_b += t_b_interval
      if t_b == 10:
         t_b = 0
         t_a += 1

      new_STL_slimmed = [
         {"step": item["step"], "state": item["state"]}
         for item in new_STL
      ]
      next_STL_state = {
         "time": f"{t_a}'{t_b}",
         "subtask_list": new_STL_slimmed
      }
      append_stl_state(log_path, next_STL_state)
      clean_format_stl_state(log_path)
      # append_stl_state(f'dataset/{place}_{id}/log.json', next_STL_state)
      # clean_format_stl_state(f'dataset/{place}_{id}/log.json')

      if action == '[STOP]':
         stop_quantity += 1
      if stop_quantity >= 3:
         break


if __name__ == '__main__':

   # my_model = "gpt-4.1-mini"
   my_model = "gemini-1.5-flash"
   exp = 'ours'
   place = 'greenhouse'
   id = 1

   decide(my_model, exp, place, id)