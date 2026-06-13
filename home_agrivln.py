# AgriVLN - The Home Page

import argparse
import time
import os
import json
import sys

from agrivln.STL import STL
from agrivln.decide import decide
from agrivln.evaluate import evaluate


def check_label_format(label_path):
   valid_actions = {"[FORWARD]", "[LEFT ROTATE]", "[RIGHT ROTATE]", "[STOP]", "[WAIT]"}
   with open(label_path, "r") as f:
      labels = json.load(f)
   for i in range(len(labels)):
      entry = labels[i]
      if entry["action"] not in valid_actions:
         print(f"[ERROR] Action NO. {i} is invalid: {entry['action']}")
         return False
      if i < len(labels) - 1:
         end_time = round(labels[i]["time_range"][1], 3)
         next_start_time = round(labels[i + 1]["time_range"][0], 3)
         if end_time != next_start_time:
            print(f"[ERROR] Time steps {i} and {i+1} are not connected: {end_time} ≠ {next_start_time}")
            return False
   return True


if __name__ == '__main__':

   parser = argparse.ArgumentParser()
   parser.add_argument("--place", type=str, required=True, help="Place")
   parser.add_argument("--id_range", type=int, nargs='+', required=True, help="Input the range of ID")
   parser.add_argument("-t", "--if_token", type=str, required=False, default='False', help="Token calculation")
   args = parser.parse_args()
   place = args.place
   id_range = args.id_range
   if_token = args.if_token

   if len(id_range) == 1:
      id_range = id_range
   elif len(id_range) == 2:
      id_range = list(range(id_range[0], id_range[1] + 1))
   elif len(id_range) > 2:
      id_range = id_range
   else:
      print('[ERROR] Invalid ID range.')
      sys.exit(1)

   if if_token not in ['True', 'False']:
      print('[ERROR] Invalid if_token.')
      sys.exit(1)

   # Running information
   if if_token == 'True':
      exp = 'token-AgriVLN'
   else:
      exp = 'AgriVLN'
   LLM = 'deepseek-r1:32b'
   VLM = 'qwen2.5vl:32b'

   print(f'[INFO] Experiment: {exp}')
   print(f'[INFO] LLM: {LLM}')
   print(f'[INFO] VLM: {VLM}')
   print(f"[INFO] Place: {place}")
   print(f'[INFO] ID range: {id_range}')
   
   for id in id_range:
      dir_path = f"runs/{exp}/{place}_{id}"
      os.makedirs(dir_path, exist_ok=True)
      label_path = f"dataset/{place}_{id}/label.json"
      if check_label_format(label_path) == False:
         print(f'[ERROR] {place}_{id} label format is wrong.')
      else:
         print(f"[INFO] {place}_{id} label format is correct.")
         print(f'--- {place}_{id} starts ---')

         STL(LLM, exp, place, id)
         time.sleep(0.1)

         decide(VLM, exp, place, id, if_token)
         time.sleep(0.1)

         evaluate(exp, place, id)
         time.sleep(0.1)

         print(f'--- {place}_{id} ends ---')
         