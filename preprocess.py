from moviepy.editor import VideoFileClip
import os
import cv2
import json
import re
import time


def convert_video_to_30fps(input_path, output_path=None):
   # 自动生成输出路径
   if output_path is None:
      base, ext = os.path.splitext(input_path)
      output_path = f"{base}_30fps{ext}"

   print(f"加载视频: {input_path}")
   clip = VideoFileClip(input_path)

   # raw_fps = clip.fps
   raw_fps = 14.3
   print(f"原始帧率: {raw_fps}，目标帧率: 30")
   clip_resampled = clip.set_fps(30)

   os.makedirs(os.path.dirname(output_path), exist_ok=True)
   print(f"正在保存到: {output_path}")
   clip_resampled.write_videofile(output_path, fps=30, codec='libx264')


def extract_frames(video_path, output_dir, frame_interval, output_size=None):
   os.makedirs(output_dir, exist_ok=True)
   
   cap = cv2.VideoCapture(video_path)
   if not cap.isOpened():
      print(f"无法打开视频文件：{video_path}")
      return

   # fps = cap.get(cv2.CAP_PROP_FPS)
   fps = 30
   frame_count = 0
   saved_count = 0
   
   while True:
      ret, frame = cap.read()
      if not ret:
         break

      if frame_count % frame_interval == 0:
         # 计算当前帧对应的时间（秒）
         time_in_sec = frame_count / fps
         sec = int(time_in_sec)
         # print(round((time_in_sec - sec) * 10))
         # fraction = int((time_in_sec - sec) * 10)  # 只保留一位小数作为 b
         fraction = round((time_in_sec - sec) * 10)

         if output_size is not None:
            frame = cv2.resize(frame, output_size)

         # 命名为 frame_a'b.jpg
         frame_filename = os.path.join(output_dir, f"frame_{sec}'{fraction}.jpg")
         cv2.imwrite(frame_filename, frame)
         saved_count += 1

      frame_count += 1

   cap.release()
   print(f"提取完成：共提取 {saved_count} 帧。")


def timeline(input_video, output_video, input_fps):
   # 打开视频
   cap = cv2.VideoCapture(input_video)

   if not cap.isOpened():
      print("❌ Error: Cannot open video.")
      return

   # 获取总帧数和视频持续时长
   total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
   duration = total_frames / input_fps

   # 用相同的fps和分辨率保存输出视频
   fourcc = cv2.VideoWriter_fourcc(*'avc1')  # 选择 H.264 编码保存为 .mp4
   out = cv2.VideoWriter(output_video, fourcc, input_fps, 
                         (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 
                          int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

   if not out.isOpened():
      print(f"❌ Error: Cannot open video writer for {output_video}")
      return

   while cap.isOpened():
      ret, frame = cap.read()
      if not ret:
         break

      # 当前帧时间
      current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
      current_time = current_frame / input_fps
      time_text = f"{current_time:.2f}s / {duration:.2f}s"

      # 设置字体样式
      font = cv2.FONT_HERSHEY_SIMPLEX
      font_scale = 1.5  # 字体放大
      thickness = 4     # 字体加粗
      color = (255, 255, 255)  # 白色文字

      # 计算文本宽度和高度，确保文本水平居中
      (text_width, text_height), _ = cv2.getTextSize(time_text, font, font_scale, thickness)
      center_position = ((frame.shape[1] - text_width) // 2, frame.shape[0] - text_height - 50)  # 50像素高的位置

      # 先画一个黑底背景框（文本框居中）
      cv2.rectangle(frame,
                    (center_position[0] - 10, center_position[1] - text_height - 15),
                    (center_position[0] + text_width + 10, center_position[1] + 20),
                    (0, 0, 0), -1)  # 背景框颜色为黑色

      # 然后叠上时间文字
      cv2.putText(frame, time_text, center_position, font, font_scale, color, thickness)

      # 将处理后的帧写入输出视频
      out.write(frame)

   cap.release()
   out.release()

   print(f"✅ Done! Saved the video with timestamp to {os.path.abspath(output_video)}")


def json_info(save_path, place, id):

   data = {
      "episode_id": f"{place}_{id}",
      "instruction": "write here",
      "length": -1.0
      # "stop_t": -1,
      # "SR": -1,
      # "NE": -1,
      # "ISR": [-1, -1]
   }
   os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
   with open(save_path, 'w') as f:
      json.dump(data, f, indent=3)

   print(f"✅ JSON 文件已成功创建：{save_path}")


def json_label(save_path):
   
   data = [
      {"time_range": [0.0, -1.1], "action": "[WAIT]"},
      {"time_range": [-1.1, -2.2], "action": "[FORWARD]"},
      {"time_range": [-2.2, -3.3], "action": "[LEFT ROTATE]"},
      {"time_range": [-3.3, 999], "action": "[STOP]"}
   ]

   os.makedirs(os.path.dirname(save_path), exist_ok=True)

   # 先用 json.dumps 格式化字符串
   json_str = json.dumps(data, indent=3)

   # 使用正则把 time_range 的数组格式化成一行
   json_str = re.sub(r'\[\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]', r'[\1, \2]', json_str)

   with open(save_path, 'w') as f:
      f.write(json_str)

   print(f"✅ Label JSON 文件（紧凑 time_range）已保存到：{save_path}")


if __name__ == "__main__":

   place = 'village'
   # id_range = [5, 6]
   id_range = list(range(12, 25))

   for id in id_range:

      # fps from 14 to 30
      camera_path = f"camera/{place}_{id}.MP4"
      fps30_path = f"video/{place}_{id}_30fps.mp4"
      convert_video_to_30fps(camera_path, fps30_path)
      time.sleep(1)

      # video to frame
      frame_path = f"dataset/{place}_{id}/frames"
      frame_interval = 6
      output_size = (640, 360)
      extract_frames(fps30_path, frame_path, frame_interval, output_size)
      time.sleep(1)

      # timeline
      timeline_path = f"video/{place}_{id}_timeline.mp4"
      input_fps = 30
      timeline(fps30_path, timeline_path, input_fps)

      # info & label
      info_path = f"dataset/{place}_{id}/info.json"
      label_path = f"dataset/{place}_{id}/label.json"
      if not os.path.exists(info_path):
         json_info(info_path, place, id)
      else:
         print(f"⚠️ 已存在：{info_path}，跳过生成")
      if not os.path.exists(label_path):
         json_label(label_path)
      else:
         print(f"⚠️ 已存在：{label_path}，跳过生成")
      time.sleep(1)

