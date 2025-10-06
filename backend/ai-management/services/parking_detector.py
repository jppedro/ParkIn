"""
Serviço de Detecção de Vagas e Veículos com Modelo YOLO Customizado
"""

from ultralytics import YOLO
from datetime import datetime
from config import Config
import os
import cv2
import tempfile
import json

class ParkingDetector:
    """
    Usa um modelo YOLO treinado para detectar 'parking_spot' e 'car',
    e então calcula a ocupação baseada na sobreposição (IoU).
    """

    def __init__(self, model_path=None):
        if model_path is None:
            model_path = Config.YOLO_MODEL_PATH

        if not os.path.exists(model_path):
            print(f"AVISO: Modelo customizado não encontrado em '{model_path}'. Carregando 'yolov8s.pt' padrão.")
            self.model = YOLO('yolov8s.pt')
        else:
            self.model = YOLO(model_path)
            print(f"Modelo YOLO customizado carregado de '{model_path}'.")

        self.class_names = self.model.names
        print(f"Classes detectáveis: {self.class_names}")

    def _calculate_iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        unionArea = float(boxAArea + boxBArea - interArea)
        return interArea / unionArea if unionArea > 0 else 0

    def detect_cars_in_image(self, image_path):
        results = self.model(image_path, verbose=False)[0]
        detected_spots, detected_cars = [], []

        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = self.class_names.get(class_id)
            if class_name == 'parking_spot':
                detected_spots.append(box.xyxy[0].tolist())
            elif class_name in ['car', 'motorcycle', 'bus', 'truck']:
                detected_cars.append(box.xyxy[0].tolist())

        if not detected_spots:
            return {'timestamp': datetime.now().isoformat(), 'error': 'Nenhuma vaga detectada.', 'parking_analysis': {'total_spots': 0, 'occupied_spots': 0, 'free_spots': 0, 'occupancy_rate': 0, 'spots': []}}

        occupied_count = 0
        spot_statuses = []
        for i, spot_box in enumerate(detected_spots):
            is_occupied = any(self._calculate_iou(spot_box, car_box) > Config.IOU_OCCUPANCY_THRESHOLD for car_box in detected_cars)
            status = 'occupied' if is_occupied else 'free'
            if is_occupied: occupied_count += 1
            spot_statuses.append({'spot_id': i + 1, 'box': spot_box, 'status': status})

        total_spots = len(detected_spots)
        return {'timestamp': datetime.now().isoformat(), 'parking_analysis': {'total_spots': total_spots, 'occupied_spots': occupied_count, 'free_spots': total_spots - occupied_count, 'occupancy_rate': round((occupied_count / total_spots * 100), 2), 'spots': spot_statuses}}

    def detect_cars_in_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, total_frames // Config.VIDEO_FRAME_ANALYSIS_COUNT)
        frame_analyses, frame_count = [], 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            if frame_count % frame_interval == 0:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                    cv2.imwrite(tmp_file.name, frame)
                    try:
                        analysis = self.detect_cars_in_image(tmp_file.name)
                        if 'error' not in analysis: frame_analyses.append(analysis['parking_analysis'])
                    finally:
                        os.unlink(tmp_file.name)
            frame_count += 1
        cap.release()

        return self._consolidate_video_results(frame_analyses) if frame_analyses else {'timestamp': datetime.now().isoformat(), 'error': 'Nenhum frame do vídeo pôde ser analisado.', 'parking_analysis': {}}

    def _consolidate_video_results(self, frame_analyses):
        total_spots = frame_analyses[0].get('total_spots', 0)
        avg_occupied = round(sum(a.get('occupied_spots', 0) for a in frame_analyses) / len(frame_analyses))
        return {'timestamp': datetime.now().isoformat(), 'file_type': 'video', 'frames_analyzed': len(frame_analyses), 'parking_analysis': {'total_spots': total_spots, 'occupied_spots': avg_occupied, 'free_spots': total_spots - avg_occupied, 'occupancy_rate': round((avg_occupied / total_spots * 100), 2), 'description': 'Resultados baseados na ocupação média do vídeo.'}}

if __name__ == '__main__':
    TEST_IMAGE_PATH = 'uploads/parking_image_test.jpg'
    print("\n--- INICIANDO TESTE DO DETECTOR ---")
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"ERRO: Imagem de teste não encontrada em '{TEST_IMAGE_PATH}'")
    else:
        try:
            detector = ParkingDetector()
            print(f"\nAnalisando a imagem: {TEST_IMAGE_PATH}...")
            results = detector.detect_cars_in_image(TEST_IMAGE_PATH)
            print("\n--- RESULTADO DA ANÁLISE ---")
            print(json.dumps(results, indent=2))
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")