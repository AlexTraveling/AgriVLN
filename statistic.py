import os
import json

scene_order = {
   "farm": 0,
   "greenhouse": 1,
   "forest": 2,
   "mountain": 3,
   "garden": 4,
   "village": 5
}

def extract_scene_and_id(episode_id):
   scene, idx = episode_id.split("_")
   return scene, int(idx)

def collect_statistics(base_path):
   results = []

   for subdir in os.listdir(base_path):
      subdir_path = os.path.join(base_path, subdir)
      eval_path = os.path.join(subdir_path, "evaluate.json")

      if os.path.isdir(subdir_path) and os.path.isfile(eval_path):
         with open(eval_path, "r") as f:
            data = json.load(f)
            episode_id = data.get("episode_id", "")
            sr = data.get("SR", -1)
            ne = data.get("NE", -1.0)
            isr = data.get("ISR", [])
            results.append([episode_id, sr, ne, isr])

   results.sort(key=lambda x: (scene_order.get(extract_scene_and_id(x[0])[0], 999),
                               extract_scene_and_id(x[0])[1]))
   return results


def compute_averages(stats):
   total_sr = 0
   total_ne = 0
   total_isr_num = 0  # 分子
   total_isr_den = 0  # 分母
   count = len(stats)

   for item in stats:
      sr, ne, isr = item[1], item[2], item[3]
      total_sr += sr
      total_ne += ne
      if len(isr) == 2:
         total_isr_num += isr[0]
         total_isr_den += isr[1]

   avg_sr = total_sr / count if count else 0
   avg_ne = total_ne / count if count else 0
   isr_score = [total_isr_num, total_isr_den]

   return avg_sr, avg_ne, isr_score


# def compute_averages(stats):
#    total_sr = 0
#    total_ne = 0
#    total_isr = 0
#    count = len(stats)

#    for item in stats:
#       sr, ne, isr = item[1], item[2], item[3]
#       total_sr += sr
#       total_ne += ne
#       if len(isr) == 2 and isr[1] != 0:
#          total_isr += isr[0] / isr[1]

#    avg_sr = total_sr / count if count else 0
#    avg_ne = total_ne / count if count else 0
#    avg_isr = total_isr / count if count else 0

#    return avg_sr, avg_ne, avg_isr

if __name__ == "__main__":
   
   exp = 'gpt-4.1-mini'
   base_path = f"runs/{exp}"
   stats = collect_statistics(base_path)

   for item in stats:
      print(item)

   avg_sr, avg_ne, avg_isr = compute_averages(stats)

   print("\n📊 统计结果：")
   print(exp)
   print(f"✅ 样本总数: {len(stats)}")
   print(f"🟢 平均 SR : {avg_sr:.3f}")
   print(f"🔵 平均 NE : {avg_ne:.3f}")
   print(f"🟣 累计 ISR: {avg_isr[0]}/{avg_isr[1]}")
