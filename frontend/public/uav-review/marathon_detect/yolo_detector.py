# yolo_detector.py
from ultralytics import YOLO
from config import *

class YoloDetector:
    def __init__(self, weight="yolov8n.pt"):
        self.model = YOLO(weight)

    def detect(self, frame):
        res = self.model.predict(
            frame,
            device=DEVICE,
            conf=PERSON_CONF
        )
        return res[0]