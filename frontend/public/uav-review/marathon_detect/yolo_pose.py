# yolo_pose.py
from ultralytics import YOLO
import numpy as np
import cv2
from config import *

class YoloPose:
    def __init__(self):
        # 两个模型：det做检测跟踪；pose做关键点推理
        self.det_model = YOLO("./yolov8n.pt")
        self.pose_model = YOLO("./yolov8n-pose.pt")

        self.abnormal_count = {}
        self.trigger_frame = ABNORMAL_CONTINUOUS_FRAME

    def track_pipeline(self, frame):
        results = self.pose_model(frame, conf=0.1,device="cpu")
        for pose_res in results:
            if pose_res.keypoints.data.numel() == 0:
                continue
            keypoints_data = pose_res.keypoints.data
            num_person = keypoints_data.shape[0]
            for i in range(num_person):
                kpts = keypoints_data[i].cpu().numpy()
                box = pose_res.boxes[i]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                crop_person = frame[y1:y2, x1:x2]
                single_abnormal, _ = self.judge_single_person(kpts, crop_person.shape[:2])
                if single_abnormal:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, "FALL", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return frame

    def judge_single_person(self, kpts, crop_shape):
        """单人裁剪图内判断是否姿态异常（摔倒）
        返回：是否摔倒，(0,0,0,0)占位
        """
        h_crop, w_crop = crop_shape
        box_h = h_crop
        box_w = w_crop
        hw_ratio = box_h / (box_w + 1e-6)

        # 有效关键点过滤：置信度高于阈值的关键点数量
        valid_kpt = np.sum(kpts[:, 2] > KEYPOINT_CONF)
        if valid_kpt < MIN_VALID_KPTS:
            return False, (0, 0, 0, 0)

        # 取左右肩膀、左右髋关键点
        shoulder_left = kpts[5][:2]
        shoulder_right = kpts[6][:2]
        hip_left = kpts[11][:2]
        hip_right = kpts[12][:2]

        shoulder_y_avg = (shoulder_left[1] + shoulder_right[1]) / 2.0
        hip_y_avg = (hip_left[1] + hip_right[1]) / 2.0
        diff_y = abs(shoulder_y_avg - hip_y_avg)

        # 条件1：人体框高宽比偏小，身体变扁
        cond1 = (hw_ratio < FALL_HW_RATIO)
        # 条件2：肩膀和髋部竖直方向距离很近，躯干近乎躺平
        cond2 = (diff_y < box_h * FALL_DIFFY_RATIO)

        # 核心修改：两个条件【同时成立】才判定摔倒，减少误报
        is_abnormal = cond1 and cond2

        return is_abnormal, (0, 0, 0, 0)