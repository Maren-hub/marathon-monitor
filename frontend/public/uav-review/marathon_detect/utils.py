# utils.py
import cv2
import os
from datetime import datetime

def save_screenshot(frame, save_dir="output"):
    """保存异常截图"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
    path = os.path.join(save_dir, filename)
    cv2.imwrite(path, frame)
    return path

def create_video_writer(out_path, fps, width, height):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    return cv2.VideoWriter(out_path, fourcc, fps, (width, height))