import os

class Config:
    
    UPLOAD_FOLDER = 'uploads'
    RESULTS_FOLDER = 'results'
    
    # Modelo treinado para detecção aérea (2 classes: enpty, not_enpty)
    YOLO_MODEL_PATH = 'models/best.pt'
    
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