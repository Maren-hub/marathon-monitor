# api.py
from yolo_pose import YoloPose

pose_model = YoloPose()

def process_frame(frame):
    result_frame = pose_model.track_pipeline(frame)
    return result_frame