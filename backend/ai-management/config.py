import os

class Config:
    
    UPLOAD_FOLDER = 'uploads'
    RESULTS_FOLDER = 'results'
    
    YOLO_MODEL_PATH = 'yolo/runs/detect/yolo_parking_detector/weights/best.pt'
    
    IOU_OCCUPANCY_THRESHOLD = 0.1 # 10% de sobreposição já indica ocupação

    HOST = '0.0.0.0'
    PORT = 5001
    DEBUG = True
    
    ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp']
    
    VIDEO_FRAME_ANALYSIS_COUNT = 10  

    @classmethod
    def init_folders(cls):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.RESULTS_FOLDER, exist_ok=True)