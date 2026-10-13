import cv2
from config import VIDEO_PATH
from api import process_frame

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"视频fps={fps}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("视频读取结束")
        break

    out_frame = process_frame(frame)
    cv2.imshow("Marathon Pose Detect", out_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()