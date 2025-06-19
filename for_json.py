import json
import os


def save_subtasks_to_file(subtask_list, filename="subtasks.json"):
   """Save the subtask list to a local JSON file."""
   with open(filename, "w", encoding="utf-8") as f:
      json.dump(subtask_list, f, indent=3, ensure_ascii=False)
   print(f"Subtasks saved to {filename}.")


def load_subtasks_from_file(filename="subtasks.json"):
   """Load the subtask list from a local JSON file."""
   try:
      with open(filename, "r", encoding="utf-8") as f:
         subtask_list = json.load(f)
      print(f"Subtasks loaded from {filename}.")
      return subtask_list
   except FileNotFoundError:
      print(f"{filename} not found. Returning empty subtask list.")
      return []


def append_action(action_file, time_value, action_value, thought, state):
   # 如果文件存在，则读取为列表；否则初始化为空列表
   if os.path.exists(action_file):
      with open(action_file, 'r') as f:
         data = json.load(f)
   else:
      data = []

   # 添加一个新记录
   data.append({
      "time": time_value,
      "action": action_value,
      "thought": thought,
      "state": state,
      "judge": 'null'
   })

   # 写回 JSON 文件
   with open(action_file, 'w') as f:
      json.dump(data, f, indent=3)

   print(f"✅ Appended: time={time_value}, action={action_value}")


def get_stop_start_time(label_list):
   for entry in label_list:
      if entry["action"] == "[STOP]":
         return entry["time_range"][0]
   return None  # 如果没有找到 [STOP]，可以返回 None 或抛出异常


def clean_format_stl_state(filepath="STL_state.json"):
   with open(filepath, "r", encoding="utf-8") as f:
      data = json.load(f)

   # 自定义写法：逐条格式化，每个 subtask_list 用 json.dumps() 单独处理
   with open(filepath, "w", encoding="utf-8") as f:
      f.write("[\n")
      for i, entry in enumerate(data):
         f.write("  {\n")
         f.write(f"    \"time\": \"{entry['time']}\",\n")
         subtask_str = json.dumps(entry['subtask_list'], separators=(",", ": "))
         f.write(f"    \"subtask_list\": {subtask_str}\n")
         f.write("  }" + (",\n" if i < len(data) - 1 else "\n"))
      f.write("]\n")


if __name__ == '__main__':

   subtask_list = [
      {
         "step": 1,
         "subtask": "Turn right to find the yellow bench",
         "start_condition": "always",
         "end_condition": "yellow bench visible",
         "state": "done"
      },
      {
         "step": 2,
         "subtask": "Move forward along the path to the yellow bench",
         "start_condition": "yellow bench visible",
         "end_condition": "the yellow bench is close and no much path is between you and the yellow bench",
         "state": "doing"
      },
      {
         "step": 3,
         "subtask": "Stop when you reach the yellow bench",
         "start_condition": "reach the yellow bench",
         "end_condition": "no end_condition",
         "state": "pending"
      }
   ]

   # save_subtasks_to_file(subtask_list, 'subtask_000.json')
   loaded_list = load_subtasks_from_file('subtask_000.json')
   print(loaded_list)
