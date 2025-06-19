from openai import OpenAI
import argparse
import time
import os
import json

from STL import STL
from decide import decide
from evaluate import evaluate


def check_label_format(label_path):
   valid_actions = {"[FORWARD]", "[LEFT ROTATE]", "[RIGHT ROTATE]", "[STOP]", "[WAIT]"}  # 加上 [WAIT] 是为了不报错，但你也可以不算它合法

   with open(label_path, "r") as f:
      labels = json.load(f)

   for i in range(len(labels)):
      entry = labels[i]

      # 1. 检查 action 合法性
      if entry["action"] not in valid_actions:
         print(f"❌ 第 {i} 条 action 非法：{entry['action']}")
         return False

      # 2. 检查时间连续性（跳过最后一个）
      if i < len(labels) - 1:
         end_time = round(labels[i]["time_range"][1], 3)
         next_start_time = round(labels[i + 1]["time_range"][0], 3)
         if end_time != next_start_time:
            print(f"❌ 第 {i} 与 第 {i+1} 时间不连续：{end_time} ≠ {next_start_time}")
            return False

   print("✅ label 格式规范！")
   return True


def get_api_key(place):
   api_key_house = {
      "farm": "sk-bjGxtfga3vco50nL813657623c4c429eB0Bb7bA085A0FcAf",
      "greenhouse": "sk-mY5lnwAnT04g0FDqCbCfAbC575F445108640F2Cd61Cb0055",
      "forest": "sk-qR2VkWocbdujoCnkD3E24376E33049098e01835cE58559F9",
      "mountain": "sk-Lcx0kGh0mGqg2BXl15Fc8aE04e4c4b22928f09093a712a78",
      "garden": "sk-mbnk1SpyBDT5u3kbC105C83eEe9e44Cf952fD48c13Ce379b",
      "village": "sk-ir7M8JaWFdhGUhgk5605151675914664Ae12Cb937c5b7110"
   }
   if place not in api_key_house:
      raise ValueError(f"❌ 未知场景：{place}")
   else:
      api_key = api_key_house[place]
      return api_key


if __name__ == '__main__':

   parser = argparse.ArgumentParser()
   parser.add_argument("--place", type=str, required=True, help="要处理的场景名称，比如 farm/garden/orchard")
   args = parser.parse_args()
   place = args.place
   print(f"🌍 当前处理场景为：{args.place}")

   model = "gpt-4.1-mini"
   # model = "gemini-1.5-flash"
   # model = "llama-4-scout"

   exp = model
   # place = 'greenhouse'
   id_range = list(range(1, 25))
   id_range = [10]
   client = OpenAI(api_key=get_api_key(place), base_url="https://api.laozhang.ai/v1")
   # client = OpenAI(api_key="sk-0EGoOpwuIIjPdNxi3f5a17EfA9F84bA88949841f0aBaAe4e", base_url="https://api.laozhang.ai/v1")

   for id in id_range:
      dir_path = f"runs/{exp}/{place}_{id}"
      os.makedirs(dir_path, exist_ok=True)

      label_path = f"dataset/{place}_{id}/label.json"
      if check_label_format(label_path) == False:
         print('label error')
      else:
         STL(model, exp, place, id)
         time.sleep(0.1)

         decide(model, exp, place, id, client)
         time.sleep(0.1)

         evaluate(exp, place, id)
         time.sleep(0.1)