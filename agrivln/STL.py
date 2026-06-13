# AgriVLN - The Subtask List Module

import ollama
import json
import re


def load_instruction_from_info(file_path):
   with open(file_path, 'r') as f:
      info = json.load(f)
   return info['instruction']


def save_subtask_list(message, output_path="STL.json"):
   content = message
   match = re.search(r"<subtask_list>\s*(\[.*?\])\s*</subtask_list>", content, re.DOTALL)
   if not match:
      print("[ERROR] Cannot find the content in <subtask_list> tag.")
      return
   try:
      subtask_list = json.loads(match.group(1))
   except json.JSONDecodeError as e:
      print("[ERROR] Fail to decode JSON:", e)
      return
   with open(output_path, "w") as f:
      json.dump(subtask_list, f, indent=3)
   print(f"[INFO] Subtask list is saved to {output_path}.")


def generate_initial_stl_state(stl_path, output_path):
   with open(stl_path, "r") as f:
      subtask_list = json.load(f)
   state = {
      "time": "0'0",
      "subtask_list": [
         {"step": subtask["step"], "state": "pending"} for subtask in subtask_list
      ]
   }
   with open(output_path, "w") as f:
      json.dump([state], f, indent=3)
   print(f"[INFO] Initial state of Subtask List is generated to: {output_path}.")


def STL(my_model, exp, place, id):

   with open(f"dataset/{place}_{id}/info.json", 'r') as f:
      instruction = json.load(f)['instruction']

   my_system = """
   You are an expert in Vision-and-Language Navigation (VLN) for guiding an agricultural robot. Normally, instruction is directly sent to robot. In our setup, the instruction is not directly given to the robot. Instead, we first decompose it into a structured list of subtasks. This subtask list is easier for the robot to understand and execute.

   Your task is to decompose a natural language instruction into a subtask list. Each subtask should include the following fields:
   - "step": a number indicating the order
   - "subtask": a natural language description of the action
   - "start_condition": when the subtask should start (e.g., "always", "yellow bench visible")
   - "end_condition": a visually verifiable or logical condition indicating the subtask is complete

   Rules: 
   - The first subtask's "start_condition" must be "always". 
   - From the second subtask on, the "start_condition" typically mirrors the "end_condition" of the previous one. 
   - Only the final subtask can involve stopping the robot. Its "subtask" should follow this format: "Stop when ...". The word "stop" should appear only in the final subtask.

   Input format: 
   <instruction> {instruction text} </instruction>

   Output format:
   <thought> {your reasoning before producing the subtask list} </thought>
   <subtask_list>
   [
      {
         "step": 1,
         "subtask": "...",
         "start_condition": "...",
         "end_condition": "..."
      },
      {
         "step": 2,
         ...
      }
   ]
   </subtask_list>
   """

   my_user = f"""<instruction> {instruction} </instruction>"""

   messages = [
      {
         'role': 'system',
         'content': my_system
      },
      {
         'role': 'user',
         'content': my_user
      }
   ]
   response = ollama.chat(model=my_model, messages=messages)
   message = response['message']['content']
   print(f'[INFO] {my_model} message:')
   print(message)

   STL_path = f"runs/{exp}/{place}_{id}/STL.json"
   log_path = f"runs/{exp}/{place}_{id}/log.json"

   save_subtask_list(message, STL_path)
   generate_initial_stl_state(STL_path, log_path)

   return True
