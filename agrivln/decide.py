# AgriVLN - The Decision Making Module

import ollama
import re
import os
import json

from agrivln.for_json import get_stop_start_time, clean_format_stl_state, append_action


# system prompt
def get_system_prompt():
   system_prompt = """
      You are an expert in Vision-and-Language Navigation (VLN) for guiding an agricultural robot. Your mission is to understand both the previous subtask list and the current camera image, to make decision for next action and update subtask list. 

      To accomplish the mission, you need: 
      1. Understand both the previous subtask list and the current camera image. 
      2. Select the most reasonable next action from: [FORWARD], [LEFT ROTATE], [RIGHT ROTATE], or [STOP]. The actions [LEFT ROTATE] and [RIGHT ROTATE] refer to the robot physically rotating its body in place (not camera panning or sliding the image). 
      3. Explain your decision clearly: why you chose the action, and why you keep or change the state of subtask list. Please be logical, observant and practical, as if you were physically navigating the robot.
      4. Update the subtask list.

      Subtask List rules: 
      - The Subtask List provided to you is from the previous time step.
      - One Subtask List consists of several subtasks, and all subtasks should be completed one by one in order.
      - Every subtask has three types of state: pending, doing, and done. 
      - When there is a subtask in state of doing, you only need focus on this subtask. Through the understanding on both the subtask description and the camera image, carefully reason whether this subtask is completed, i.e., the end condition is satisfied. If true, change the state from doing to done. If false, keep the state of doing. 
      - When there is no subtasks in state of doing, you only need focus on the first subtask among all subtasks in state of pending. Through the understanding on both the subtask description and the camera image, carefully reason whether this subtask should start, i.e., the start condition is satisfied. If true, change the state from pending to doing. If false, keep the state of pending.
      - You cannot skip the state of doing and directly change the state from pending to done, i.e., state of doing is a necessary procedure. 
      - You **must not** execute action [STOP] unless all subtasks have been completed, i.e., in state of done.
      - Do **not** confuse "seeing the object" with "reaching the object".

      Subtask List format:
      [
         {
            "step": "serial number of the subtask",
            "subtask": "description of the subtask",
            "start_condition": "condition to start",
            "end_condition": "condition to end",
            "state": "pending/doing/done"
         },
         ...
      ]

      For input, you will be provided with: 
      - Subtask List from the previous time step.
      - RGB image from robot's camera (a super wide angle lens with 13mm focal length) feed on the current time step. 

      Output format:
      <thought> {your reasoning about why this action is appropriate} </thought>
      <action> [{the selected action}] </action>
      <state> Subtask NO.{number of subtask} changes from {old state} to {new state} (if state changes). or Subtask NO.{number of subtask} keeps state of {old state} (if no state changes). </state>

      Here is a correct example for output format: 
      <thought> The robot needs to move forward to reach the yellow bench... </thought>  
      <action> [FORWARD] </action> 
      <state> Subtask NO.2 changes from pending to doing </state>

      Important:
      - The <action> tag must reflect your final, reasoned decision. If you revise your choice during <thought>, make sure to update <action> accordingly.
      """
   return system_prompt


# user prompt
def get_user_prompt(STL):
   user_prompt = f"""
      <subtask_list>
      {json.dumps(STL, indent=3, ensure_ascii=False)}
      </subtask_list>
      """
   return user_prompt


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
   for subtask in new_STL:
      if subtask.get("step") == number:
         current_state = subtask.get("state")
         if current_state == old_state:
            subtask["state"] = new_state
            print(f"[INFO] Subtask {number} updated from '{old_state}' to '{new_state}'.")
         else:
            print(f"[WARNING] Subtask {number} not updated: current state is '{current_state}', expected '{old_state}'.")
         return new_STL
   print(f"[ERROR] Subtask with step number {number} not found.")
   return new_STL


def append_stl_state(state_path, new_entry):
   try:
      with open(state_path, 'r') as f:
         data = json.load(f)
   except FileNotFoundError:
      data = []
   data.append(new_entry)
   with open(state_path, 'w') as f:
      json.dump(data, f, indent=3, separators=(",", ": "))


def load_json(path):
   with open(path, 'r') as f:
      return json.load(f)
   

def merge_stl_and_state(stl_path, state_path, current_time):
   STL = load_json(stl_path)
   STL_states = load_json(state_path)

   def time_str_to_float(time_str):
      minutes, tenths = time_str.split("'")
      return int(minutes) + int(tenths) / 10

   current_time_val = time_str_to_float(current_time)
   closest_state = None
   for state_snapshot in STL_states:
      snapshot_time = time_str_to_float(state_snapshot['time'])
      if snapshot_time <= current_time_val:
         closest_state = state_snapshot
      else:
         break
   if closest_state is None:
      raise ValueError(f"No matching STL state found for time {current_time}")
   state_dict = {s['step']: s['state'] for s in closest_state['subtask_list']}
   merged_STL = []
   for subtask in STL:
      step = subtask['step']
      merged_subtask = dict(subtask)
      merged_subtask['state'] = state_dict.get(step, "unknown")  # fallback
      merged_STL.append(merged_subtask)
   return merged_STL


def decide(my_model, exp, place, id, if_token):

   t_a = 0
   t_b = 0
   t_b_interval = 2
   FPS = 5.0
   safe_redundancy = 2

   label_path = f"dataset/{place}_{id}/label.json"
   with open(label_path, "r") as f:
      labels = json.load(f)

   stop_start_time = get_stop_start_time(labels)
   print("[INFO] Label STOP begins at: ", stop_start_time)
   max_time = float(stop_start_time) + (1 / FPS) * safe_redundancy
   print(f'[INFO] Max time step: {max_time}')

   stop_quantity = 0

   while t_a < max_time:

      t = f'{t_a}\'{t_b}'

      STL_path = f"runs/{exp}/{place}_{id}/STL.json"
      log_path = f"runs/{exp}/{place}_{id}/log.json"
   
      STL = merge_stl_and_state(STL_path, log_path, current_time=t)
   
      system_prompt = get_system_prompt()
      user_prompt = get_user_prompt(STL)
      
      image_path = f"dataset/{place}_{id}/frames/frame_{t}.jpg"
      messages = [
         {
            'role': 'system',
            'content': system_prompt
         },
         {
            'role': 'user',
            'content': user_prompt,
            'images': [image_path]
         }
      ]
      response = ollama.chat(model=my_model, messages=messages)
      message = response['message']['content']

      if if_token == 'True':
         
         token_prompt = response.prompt_eval_count
         token_completion = response.eval_count
         token_path = f"runs/{exp}/{place}_{id}/token.json"

         os.makedirs(os.path.dirname(token_path), exist_ok=True)

         if os.path.exists(token_path):
            with open(token_path, "r") as token_f:
               try:
                  data = json.load(token_f)
               except json.JSONDecodeError:
                  data = []
         else:
            data = []

         data.append({
            "place": place,
            "time": t,
            "token_prompt": token_prompt,
            "token_completion": token_completion
         })

         with open(token_path, "w") as token_f:
            json.dump(data, token_f, indent=4)

      result = extract(message)
      action = result['action']
      thought = result['thought']
      state = result['state']
      predict_path = f"runs/{exp}/{place}_{id}/predict.json"
      append_action(predict_path, t, action, thought, state)

      # revision 2025.10.23 start
      if state == None:
         new_STL = STL
         print('[WARNING] State = None.')
      else:
      # revision 2025.10.23 end
         if 'keep' in state:
            new_STL = STL
         if 'change' in state:
            number, old_state, new_state = extract_state(state)
            new_STL = update_subtask_state(STL, number, old_state, new_state)

      print(f'{place}_{id}, {t_a}.{t_b}, {action}')

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
      
      if action == '[STOP]':
         stop_quantity += 1
      if stop_quantity >= 3:
         break
