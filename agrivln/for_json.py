# AgriVLN - The JSON Tools

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
   
   if os.path.exists(action_file):
      with open(action_file, 'r') as f:
         data = json.load(f)
   else:
      data = []

   data.append({
      "time": time_value,
      "action": action_value,
      "thought": thought,
      "state": state,
      "judge": 'null'
   })

   with open(action_file, 'w') as f:
      json.dump(data, f, indent=3)


def get_stop_start_time(label_list):
   for entry in label_list:
      if entry["action"] == "[STOP]":
         return entry["time_range"][0]
   return None 


def clean_format_stl_state(filepath="STL_state.json"):
   with open(filepath, "r", encoding="utf-8") as f:
      data = json.load(f)

   with open(filepath, "w", encoding="utf-8") as f:
      f.write("[\n")
      for i, entry in enumerate(data):
         f.write("  {\n")
         f.write(f"    \"time\": \"{entry['time']}\",\n")
         subtask_str = json.dumps(entry['subtask_list'], separators=(",", ": "))
         f.write(f"    \"subtask_list\": {subtask_str}\n")
         f.write("  }" + (",\n" if i < len(data) - 1 else "\n"))
      f.write("]\n")
