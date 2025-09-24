import os


class Config:
    
    UPLOAD_FOLDER = 'uploads'
    RESULTS_FOLDER = 'results'
    
    YOLO_MODEL_PATH = 'yolov8s.pt'
    CONFIDENCE_THRESHOLD = 0.1
    
    HOST = '0.0.0.0'
    PORT = 5001
    DEBUG = True
    
    ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp']
    
    VIDEO_FRAME_ANALYSIS_COUNT = 10  
    
    # Configurações de detecção otimizadas para drone
    IMAGE_SIZE = 1280              # Tamanho maior para melhor detecção
    IOU_THRESHOLD = 0.3            # Non-Maximum Suppression mais permissivo
    MAX_DETECTIONS = 300           # Máximo de detecções por imagem
    
    # Classes de veículos COCO
    VEHICLE_CLASSES = {
        2: 'car',
        3: 'motorcycle', 
        5: 'bus',
        7: 'truck'
    }
    
    @classmethod
    def init_folders(cls):
        """
        Cria as pastas necessárias se não existirem
        """
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.RESULTS_FOLDER, exist_ok=True)
