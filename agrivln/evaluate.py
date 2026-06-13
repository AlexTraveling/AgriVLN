# AgriVLN - The Evaluation Module

import json
import os
import time

from agrivln.for_json import get_stop_start_time
from agrivln.hyperparameter import get_hyperparameter


def time_str_to_float(time_str):
   minutes, tenths = time_str.split("'")
   return int(minutes) + int(tenths) / 10


def judge_predictions(predict_path, label_path):
   with open(predict_path, 'r') as f:
      predictions = json.load(f)
   with open(label_path, 'r') as f:
      labels = json.load(f)
   for pred in predictions:
      pred_time = time_str_to_float(pred["time"])
      pred_action = pred["action"]
      match_idx = None
      for i, label in enumerate(labels):
         start, end = label["time_range"]
         if start <= pred_time < end:
            match_idx = i
            break
      if match_idx is not None:
         label_action = labels[match_idx]["action"]
         if label_action == "[WAIT]":
            prev_action = labels[match_idx - 1]["action"] if match_idx > 0 else None
            next_action = labels[match_idx + 1]["action"] if match_idx < len(labels) - 1 else None
            if pred_action == prev_action or pred_action == next_action:
               pred["judge"] = "True"
            else:
               pred["judge"] = "False"
         else:
            pred["judge"] = str(pred_action == label_action)
      else:
         pred["judge"] = "False"
   with open(predict_path, 'w') as f:
      json.dump(predictions, f, indent=3)
   print('[INFO] Judgement on predicted actions is successfully updated.')


def load_judged_results(filepath):
   with open(filepath, "r") as f:
      data = json.load(f)
   result = [
      {
         "time": item["time"],
         "action": item["action"],
         "judge": item["judge"]
      }
      for item in data
   ]
   return result


def convert_time_to_float(result_list):

   def time_str_to_float(time_str):
      minutes, tenths = time_str.split("'")
      return int(minutes) + int(tenths) / 10

   new_list = []
   for item in result_list:
      new_item = item.copy()
      new_item["time"] = time_str_to_float(item["time"])
      new_list.append(new_item)
   return new_list


def calculate_relative_NE(label_list, stop_t, label_stop_t, speed, path_length=-1.0):
   
   def overlap(a_start, a_end, b_start, b_end):
      return max(0.0, min(a_end, b_end) - max(a_start, b_start))

   t1 = 0.0
   t2 = 0.0
   for item in label_list:
      if item["action"] != "[FORWARD]":
         continue
      start, end = item["time_range"]
      t1 += overlap(start, end, stop_t, label_stop_t)
      t2 += overlap(start, end, 0.0, label_stop_t)
   relative_NE = t1 / t2 if t2 > 0 else 0.0
   if path_length > 0:
      absolute_NE = relative_NE * path_length
   else:
      absolute_NE = t1 * speed
   return relative_NE, absolute_NE


def calculate_ISR(STL_state_list, stop_t, STL_path):
   with open(STL_path, "r", encoding="utf-8") as f:
      total = len(json.load(f))
   def time_str_to_float(time_str):
      minutes, tenths = time_str.split("'")
      return int(minutes) + int(tenths) / 10
   latest_subtask_list = None
   max_time = -1.0
   for entry in STL_state_list:
      t = time_str_to_float(entry["time"])
      if t <= stop_t and t > max_time:
         max_time = t
         latest_subtask_list = entry["subtask_list"]
   if latest_subtask_list is None:
      print('[ERROR] The latest subtask list is none.')
      return (0, total)
   done_count = sum(1 for s in latest_subtask_list if s["state"] == "done")
   return (done_count, total)


def json_evaluate(save_path, exp, place, id, SR, NE, ISR, stop_t, type, path_length, label_stop_time):
   data = {
      "exp": exp,
      "episode_id": f"{place}_{id}",
      "SR": SR,
      "NE": NE,
      "ISR": ISR,
      "stop_t": stop_t,
      "type": type,
      "path_length": path_length,
      "label_stop_time": label_stop_time
   }
   os.makedirs(os.path.dirname(save_path), exist_ok=True)
   with open(save_path, 'w') as f:
      json.dump(data, f, indent=3)
   print(f"[INFO] Evaluation result is saved to: {save_path}")


def evaluate(exp, place, id):

   interval = get_hyperparameter('interval')
   stop_t = -1.0
   threshold = get_hyperparameter('threshold')
   speed = get_hyperparameter('speed')
   SR_threshold = get_hyperparameter('SR_threshold')
   accuracy_threshold = get_hyperparameter('accuracy_threshold')

   # Revision 2025.10.21
   t = threshold / 2
   # t = threshold

   # path
   predict_path = f"runs/{exp}/{place}_{id}/predict.json"
   label_path = f"dataset/{place}_{id}/label.json"
   STL_path = f"runs/{exp}/{place}_{id}/STL.json"
   log_path = f"runs/{exp}/{place}_{id}/log.json"
   info_path = f"dataset/{place}_{id}/info.json"
   evaluate_path = f"runs/{exp}/{place}_{id}/evaluate.json"

   # judge first
   judge_predictions(predict_path, label_path)
   time.sleep(0.1)

   results = load_judged_results(predict_path)
   results = convert_time_to_float(results)

   with open(label_path, "r") as f:
      labels = json.load(f)

   stop_start_time = get_stop_start_time(labels)
   print(f'Label stop time: {stop_start_time}')

   type = 'no_stop'

   while t <= stop_start_time:

      if any(item["time"] == round(t, 1) and item["action"] == "[STOP]" for item in results):
         stop_t = t
         type = 'valid_stop'
         break

      start_check = round(max(0.0, t - threshold), 1)
      recent_judges = [
         item for item in results
         if start_check <= item["time"] <= round(t, 1)
      ]

      if len(recent_judges) > 0:
         true_count = sum(1 for item in recent_judges if item["judge"] == "True")
         accuracy = true_count / len(recent_judges)

         if accuracy < accuracy_threshold:
            stop_t = round(t - threshold * 0.5, 1)
            type = 'deviation'
            break

      t = round(t + interval, 1)

   print(f'Predicted stop time: {stop_t}')
   print(f'Type: {type}')

   with open(info_path, 'r') as f:
      path_length = json.load(f).get("length")

   if type == 'no_stop':
      SR = 0
      NE = 0
      RNE = 0
      stop_t = stop_start_time
   if type == 'valid_stop' or type == 'deviation':
      label_list = json.load(open(label_path))
      RNE, NE = calculate_relative_NE(label_list, stop_t, stop_start_time, speed, path_length)
      if NE < SR_threshold:
         SR = 1
      else:
         SR = 0

   NE = round(NE, 3)
   print(f'SR: {SR}')
   print(f'RNE: {round(RNE, 3)}')
   print(f'NE: {NE}')

   with open(log_path, "r") as f:
      STL_state_list = json.load(f)

   done, total = calculate_ISR(STL_state_list, stop_t, STL_path)
   if type == 'no_stop':
      done = total - 1
   elif SR == 1:
      done = total
   ISR = done / total if total > 0 else 0.0
   print(f"ISR = {ISR:.2f} ({done}/{total} subtasks done)")

   json_evaluate(evaluate_path, exp, place, id, SR, NE, [done, total], stop_t, type, path_length, stop_start_time)
