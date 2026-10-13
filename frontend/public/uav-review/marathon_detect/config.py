# config.py
# 设备
DEVICE = "cpu"

# 目标检测置信
PERSON_CONF = 0.1

# pose关键点参数
KEYPOINT_CONF = 0.3    # 关键点置信度门槛，低于这个视为无效点；调小=接受更多噪声点
MIN_VALID_KPTS = 4     # 最少需要几个可信关键点才做判断；调小=允许更多遮挡
FALL_HW_RATIO = 2.2    # 高宽比阈值；数值变大 → 更容易判摔倒；变小 → 更严格
FALL_DIFFY_RATIO = 0.25
# 姿态防抖：连续多少帧异常才判定摔倒
ABNORMAL_CONTINUOUS_FRAME = 25
# track跟踪参数
TRACK_PERSIST = True
TRACK_TRACKER = "bytetrack.yaml"

# 视频路径（相对路径）
VIDEO_PATH = r"videos/drone3.mp4"
