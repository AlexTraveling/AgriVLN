import cv2
import os

def extract_frames(video_path, output_dir, frame_interval=5, output_size=None):
   os.makedirs(output_dir, exist_ok=True)
   
   cap = cv2.VideoCapture(video_path)
   if not cap.isOpened():
      print(f"无法打开视频文件：{video_path}")
      return

   fps = cap.get(cv2.CAP_PROP_FPS)
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

# 示例用法：
video_path = "video/garden_7_30fps.mp4"
output_dir = "frame"
frame_interval = 6
output_size = (640, 360)  # 你想要的尺寸，宽x高，也可以设为 None

extract_frames(video_path, output_dir, frame_interval, output_size)
