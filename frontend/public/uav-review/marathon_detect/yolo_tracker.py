# yolo_tracker.py
from ultralytics import YOLO
from config import *

class YoloTracker:
    def __init__(self, weight="yolov8n.pt"):
        self.model = YOLO(weight)

    def track(self, frame):
        res = self.model.track(
            frame,
            device=DEVICE,
            conf=PERSON_CONF,
            persist=TRACK_PERSIST,
            tracker=TRACK_TRACKER
        )
        return res[0]