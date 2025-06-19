import json
import os
import time

from for_json import get_stop_start_time


def time_str_to_float(time_str):
   minutes, tenths = time_str.split("'")
   return int(minutes) + int(tenths) / 10


def judge_predictions(predict_path, label_path):
   # 读取预测文件
   with open(predict_path, 'r') as f:
      predictions = json.load(f)

   # 读取标签文件
   with open(label_path, 'r') as f:
      labels = json.load(f)

   # 遍历每一条预测
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
            # 获取上下文 action
            prev_action = labels[match_idx - 1]["action"] if match_idx > 0 else None
            next_action = labels[match_idx + 1]["action"] if match_idx < len(labels) - 1 else None

            if pred_action == prev_action or pred_action == next_action:
               pred["judge"] = "True"
            else:
               pred["judge"] = "False"
         else:
            pred["judge"] = str(pred_action == label_action)
      else:
         pred["judge"] = "False"  # 未匹配任何时间区间

   # 写回预测文件
   with open(predict_path, 'w') as f:
      json.dump(predictions, f, indent=3)

   print("✅ Judge 字段已更新并写回文件！")


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
      """计算两个时间区间的重叠长度"""
      return max(0.0, min(a_end, b_end) - max(a_start, b_start))

   t1 = 0.0  # stop_t 到 label_stop_t 内的 FORWARD 总时长
   t2 = 0.0  # 0 到 label_stop_t 内的 FORWARD 总时长

   for item in label_list:
      if item["action"] != "[FORWARD]":
         continue  # 跳过非 FORWARD 的 action

      start, end = item["time_range"]  # 解包时间范围

      # 与 [stop_t, label_stop_t] 的重合部分
      t1 += overlap(start, end, stop_t, label_stop_t)

      # 与 [0.0, label_stop_t] 的重合部分
      t2 += overlap(start, end, 0.0, label_stop_t)

   relative_NE = t1 / t2 if t2 > 0 else 0.0

   if path_length > 0:  # if this episode has path length
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

   # 找到 stop_t 时刻前（含）的最后一条记录
   latest_subtask_list = None
   max_time = -1.0
   for entry in STL_state_list:
      t = time_str_to_float(entry["time"])
      if t <= stop_t and t > max_time:
         max_time = t
         latest_subtask_list = entry["subtask_list"]

   if latest_subtask_list is None:
      print('CLICK! ')
      return (0, total)  # 找不到记录就默认没有完成

   # total = len(latest_subtask_list)
   print(f'CHECK TOTAL: {total}')
   done_count = sum(1 for s in latest_subtask_list if s["state"] == "done")

   return (done_count, total)


def update_info_json(info_path, stop_t, SR, NE, ISR):
   # 读取原始 info.json
   with open(info_path, "r") as f:
      info = json.load(f)

   # 更新字段
   info["stop_t"] = stop_t
   info["SR"] = SR
   info["NE"] = NE
   info["ISR"] = ISR

   # 写回文件
   with open(info_path, "w") as f:
      json.dump(info, f, indent=3)

   print("✅ info.json 已更新完毕！")


def json_evaluate(save_path, exp, place, id, SR, NE, ISR, stop_t):

   data = {
      "exp": exp,
      "episode_id": f"{place}_{id}",
      "SR": SR,
      "NE": NE,
      "ISR": ISR,
      "stop_t": stop_t,
   }
   os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
   with open(save_path, 'w') as f:
      json.dump(data, f, indent=3)

   print(f"✅ JSON 文件已成功创建：{save_path}")


def evaluate(exp, place, id):

   t = 0.0
   interval = 0.2
   stop_t = -1.0
   threshold = 2.0
   speed = 1.3
   SR_threshold = 3.0  # 3m

   # path
   predict_path = f"runs/{exp}/{place}_{id}/predict.json"
   label_path = f"dataset/{place}_{id}/label.json"
   STL_path = f"runs/{exp}/{place}_{id}/STL.json"
   log_path = f"runs/{exp}/{place}_{id}/log.json"
   info_path = f"dataset/{place}_{id}/info.json"
   evaluate_path = f"runs/{exp}/{place}_{id}/evaluate.json"

   # judge first
   judge_predictions(predict_path, label_path)
   time.sleep(0.5)

   results = load_judged_results(predict_path)
   results = convert_time_to_float(results)

   with open(label_path, "r") as f:
      labels = json.load(f)

   stop_start_time = get_stop_start_time(labels)
   print("🛑 STOP 动作起始时间：", stop_start_time)

   type = 'no_stop'

   while t <= stop_start_time:

      # if '该t所对应的action为[STOP]':
      if any(item["time"] == round(t, 1) and item["action"] == "[STOP]" for item in results):
         stop_t = t
         type = 'valid_stop'
         break

      # if '在过去的threshold时间内，不存在任何一个judge为True':
      start_check = round(max(0.0, t - threshold), 1)
      recent_judges = [
         item for item in results
         if start_check <= item["time"] <= round(t, 1)
      ]
      if all(item["judge"] is False or item["judge"] == "False" for item in recent_judges):
      
         stop_t = t - threshold
         # stop_t = t
         type = 'deviation'
         break

      t = round(t + interval, 1)

   # stop_t = 12.8

   print(f'type: {type}')
   print(f'stop t: {stop_t}')

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
   # revision 6.15
   if type == 'no_stop':
      done = total - 1
   elif SR == 1:
      done = total
   ISR = done / total if total > 0 else 0.0
   print(f"ISR = {ISR:.2f} ({done}/{total} subtasks done)")

   # update_info_json(evaluate_path, stop_t, SR, NE, [done, total])
   json_evaluate(evaluate_path, exp, place, id, SR, NE, [done, total], stop_t)


if __name__ == '__main__':

   exp = 'ours'
   place = 'mountain'
   id = 6

   evaluate(exp, place, id)