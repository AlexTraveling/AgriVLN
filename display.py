import os
import re
import json
from PIL import Image
import numpy as np
from moviepy.editor import VideoClip

def parse_timestamp_str(t_str):
   # 把 "15'6" 转成 15.6 (秒)
   match = re.match(r"(\d+)'(\d+)", t_str)
   if match:
      minutes = int(match.group(1))
      tenths = int(match.group(2))
      return round(minutes + tenths / 10, 1)
   raise ValueError(f"时间格式错误: {t_str}")

def parse_timestamp(frame_name):
   # 从文件名解析时间戳 float秒
   match = re.search(r"frame_(\d+)'(\d+)\.jpg", frame_name)
   if match:
      minutes = int(match.group(1))
      tenths = int(match.group(2))
      return round(minutes + tenths / 10, 1)
   return float('inf')

def load_predictions(json_path):
   with open(json_path, 'r') as f:
      data = json.load(f)
   # 构造时间点到action的映射
   action_map = {}
   for entry in data:
      t = parse_timestamp_str(entry['time'])
      action_map[t] = entry['action']
   return action_map

def compose_frame_with_icon(bg_path, icon_path, icon_scale=0.1, icon_pos=('center', 'bottom')):
   bg = Image.open(bg_path).convert("RGBA")
   icon = Image.open(icon_path).convert("RGBA")

   # 缩放icon
   icon_w = int(bg.width * icon_scale)
   icon_h = int(icon.height * (icon_w / icon.width))
   icon = icon.resize((icon_w, icon_h), Image.LANCZOS)

   # 计算位置
   if icon_pos[0] == 'center':
      x = (bg.width - icon_w) // 2
   elif isinstance(icon_pos[0], int):
      x = icon_pos[0]
   else:
      x = 0

   if icon_pos[1] == 'bottom':
      y = bg.height - icon_h - 20  # 离底部10像素
   elif isinstance(icon_pos[1], int):
      y = icon_pos[1]
   else:
      y = 0

   # 叠加icon
   bg.alpha_composite(icon, (x, y))
   return np.array(bg.convert("RGB"))

def generate_video_with_icons(frame_dir, predict_json, arrow_dir, output_path,
                              input_fps=5, output_fps=30,
                              icon_scale=0.1, icon_pos=('center', 'bottom'), duration=None):

   action_map = load_predictions(predict_json)
   frame_files = [f for f in os.listdir(frame_dir) if f.endswith(".jpg")]
   sorted_frames = sorted(frame_files, key=parse_timestamp)

   # action对应icon文件名映射
   action_icon_map = {
      "[FORWARD]": "forward.png",
      "[LEFT ROTATE]": "left_rotate.png",
      "[RIGHT ROTATE]": "right_rotate.png",
      "[STOP]": "stop.png"
   }

   # 把每个frame对应的时间戳和路径放列表里，方便索引
   frames_info = []
   for f in sorted_frames:
      t = parse_timestamp(f)
      path = os.path.join(frame_dir, f)
      frames_info.append((t, path))

   # 确定视频总时长
   if duration is None:
      duration = frames_info[-1][0] + (1 / input_fps)  # 最后一帧时间 + 0.2s

   repeat_count = output_fps // input_fps

   def make_frame(t):
      # 找当前视频时间点对应的5FPS帧时间点（四舍五入）
      current_frame_time = round(t, 1)
      # 找离 current_frame_time 最近的帧（小于等于）
      candidate_frames = [info for info in frames_info if info[0] <= current_frame_time]
      if not candidate_frames:
         return np.zeros((720, 1280, 3), dtype=np.uint8)
      frame_time, frame_path = candidate_frames[-1]

      # 取对应action
      action = action_map.get(frame_time, None)
      if action in action_icon_map:
         icon_path = os.path.join(arrow_dir, action_icon_map[action])
         return compose_frame_with_icon(frame_path, icon_path,
                                        icon_scale=icon_scale, icon_pos=icon_pos)
      else:
         # 无icon，直接读原图
         img = Image.open(frame_path).convert("RGB")
         return np.array(img)

   clip = VideoClip(make_frame, duration=duration)
   os.makedirs(os.path.dirname(output_path), exist_ok=True)
   clip.write_videofile(output_path, fps=output_fps, codec='libx264')

# 调用示例
generate_video_with_icons(
   frame_dir="dataset/episode_demo/frames",
   predict_json="dataset/episode_demo/predict.json",
   arrow_dir="arrow",
   output_path="output_display/output_demo.mp4",
   input_fps=5,
   output_fps=30,
   icon_scale=0.1,          # 图标宽度占frame宽度的10%
   icon_pos=('center', 'bottom')  # 水平居中，靠近底部
)
