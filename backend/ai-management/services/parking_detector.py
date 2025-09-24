"""
Serviço de Detecção de Veículos e Análise de Estacionamento
"""

from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime
from config import Config


class ParkingDetector:
    """
    Classe responsável pela detecção de veículos e análise de vagas de estacionamento
    """
    
    def __init__(self, model_path=None):
        """
        Inicializa o detector com o modelo YOLO
        
        Args:
            model_path (str): Caminho para o modelo YOLO (opcional, usa config se não fornecido)
        """
        if model_path is None:
            model_path = Config.YOLO_MODEL_PATH
            
        self.model = YOLO(model_path)
        self.parking_spots = []
        self.detection_results = {}
        self.vehicle_classes = Config.VEHICLE_CLASSES
    
    def detect_cars_in_video(self, video_path):
        """
        Detecta carros no vídeo e analisa ocupação de vagas
        
        Args:
            video_path (str): Caminho para o arquivo de vídeo
            
        Returns:
            dict: Resultados consolidados da análise
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception("Erro ao abrir o vídeo")
        
        # Processar alguns frames para análise
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Analisar frames em intervalos
        frame_interval = max(1, total_frames // Config.VIDEO_FRAME_ANALYSIS_COUNT)
        
        detections_summary = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                # Executar detecção YOLO com parâmetros otimizados
                results = self.model(
                    frame,
                    imgsz=Config.IMAGE_SIZE,
                    conf=Config.CONFIDENCE_THRESHOLD,
                    iou=Config.IOU_THRESHOLD,
                    max_det=Config.MAX_DETECTIONS,
                    verbose=False
                )
                
                # Processar resultados
                frame_detections = self._process_yolo_results(results[0], frame_count)
                detections_summary.append(frame_detections)
                
            frame_count += 1
        
        cap.release()
        
        # Consolidar resultados
        consolidated_results = self._consolidate_detections(detections_summary)
        return consolidated_results
    
    def detect_cars_in_image(self, image_path):
        """
        Detecta carros em uma única imagem
        
        Args:
            image_path (str): Caminho para o arquivo de imagem
            
        Returns:
            dict: Resultados da análise da imagem
        """
        # Carregar a imagem
        image = cv2.imread(image_path)
        if image is None:
            raise Exception("Erro ao carregar a imagem")
        
        # Executar detecção YOLO com parâmetros otimizados para drone
        results = self.model(
            image,
            imgsz=Config.IMAGE_SIZE,
            conf=Config.CONFIDENCE_THRESHOLD,
            iou=Config.IOU_THRESHOLD,
            max_det=Config.MAX_DETECTIONS,
            verbose=False
        )
        
        # Processar resultados
        image_detections = self._process_yolo_results(results[0], 0)
        
        # Consolidar para formato similar ao vídeo
        cars_detected = image_detections['cars']
        car_count = len(cars_detected)
        
        # Lógica mais realista para estimar vagas
        height, width = image.shape[:2]
        image_area = height * width
        
        # Estimar vagas baseado na área da imagem e carros detectados
        estimated_total_spots = self._estimate_parking_spots(car_count, image_area)
        occupied_spots = car_count
        free_spots = max(0, estimated_total_spots - occupied_spots)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'file_type': 'image',
            'image_dimensions': {
                'width': width,
                'height': height,
                'area_pixels': image_area
            },
            'parking_analysis': {
                'total_spots': estimated_total_spots,
                'occupied_spots': occupied_spots,
                'free_spots': free_spots,
                'occupancy_rate': round((occupied_spots / estimated_total_spots) * 100, 2)
            },
            'car_detections': cars_detected,
            'cars_detected_count': car_count,
            'detection_summary': self._get_detection_summary(cars_detected)
        }
    
    def _process_yolo_results(self, results, frame_number):
        """
        Processa resultados do YOLO para um frame específico
        
        Args:
            results: Resultados do YOLO
            frame_number (int): Número do frame
            
        Returns:
            dict: Detecções processadas do frame
        """
        cars_detected = []
        debug_info = {
            'total_detections': 0,
            'vehicle_detections': 0,
            'confident_detections': 0,
            'all_classes_found': [],
            'all_confidences': []
        }
        
        print(f"\nDEBUG Frame {frame_number}:")
        
        if results.boxes is not None and len(results.boxes) > 0:
            debug_info['total_detections'] = len(results.boxes)
            print(f"Total de detecções: {len(results.boxes)}")
            
            for i, box in enumerate(results.boxes):
                cls_id = int(box.cls[0].cpu().numpy())
                confidence = float(box.conf[0].cpu().numpy())
                bbox = box.xyxy[0].cpu().numpy()
                
                debug_info['all_classes_found'].append(cls_id)
                debug_info['all_confidences'].append(confidence)
                
                # Log de todas as detecções
                class_name = self._get_coco_class_name(cls_id)
                print(f"   Detecção {i+1}: Classe {cls_id} ({class_name}) - Confiança: {confidence:.3f}")
                
                # Verificar se é um veículo
                if cls_id in self.vehicle_classes:
                    debug_info['vehicle_detections'] += 1
                    print(f"   É veículo: {self.vehicle_classes[cls_id]}")
                    
                    # Só incluir detecções com confiança acima do threshold
                    if confidence > Config.CONFIDENCE_THRESHOLD:
                        debug_info['confident_detections'] += 1
                        car_info = {
                            'bbox': [float(x) for x in bbox],  # [x1, y1, x2, y2]
                            'confidence': confidence,
                            'class_id': cls_id,
                            'class_name': self.vehicle_classes[cls_id],
                            'frame': frame_number
                        }
                        cars_detected.append(car_info)
                        print(f"   ACEITO: Confiança {confidence:.3f} > {Config.CONFIDENCE_THRESHOLD}")
                    else:
                        print(f"   REJEITADO: Confiança {confidence:.3f} <= {Config.CONFIDENCE_THRESHOLD}")
                else:
                    print(f"   Não é veículo (classe {cls_id})")
        else:
            print(f"   Nenhuma detecção encontrada")
        
        print(f"   RESUMO: {debug_info['confident_detections']} veículos aceitos de {debug_info['total_detections']} detecções")
        
        return {
            'frame': frame_number,
            'cars': cars_detected,
            'car_count': len(cars_detected),
            'debug_info': debug_info
        }
    
    def _get_coco_class_name(self, class_id):
        """
        Retorna o nome da classe COCO baseado no ID
        """
        coco_classes = {
            0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
            5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
            10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
            14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow',
            20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack',
            25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee',
            30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat',
            35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket',
            39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife',
            44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich',
            49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza',
            54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant',
            59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop',
            64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave',
            69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book',
            74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier',
            79: 'toothbrush'
        }
        return coco_classes.get(class_id, f'unknown_{class_id}')
    
    def _consolidate_detections(self, detections_list):
        """
        Consolida detecções de múltiplos frames
        
        Args:
            detections_list (list): Lista de detecções por frame
            
        Returns:
            dict: Resultados consolidados
        """
        if not detections_list:
            return self._empty_video_result()
        
        total_cars = 0
        all_detections = []
        frame_counts = []
        
        for detection in detections_list:
            car_count = detection['car_count']
            total_cars += car_count
            frame_counts.append(car_count)
            all_detections.extend(detection['cars'])
        
        # Calcular estatísticas mais precisas
        avg_cars_per_frame = total_cars / len(detections_list)
        max_cars_in_frame = max(frame_counts) if frame_counts else 0
        min_cars_in_frame = min(frame_counts) if frame_counts else 0
        
        # Estimar vagas de forma mais inteligente baseado no padrão do vídeo
        estimated_total_spots = self._estimate_parking_spots_video(max_cars_in_frame)
        occupied_spots = int(round(avg_cars_per_frame))
        free_spots = max(0, estimated_total_spots - occupied_spots)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'file_type': 'video',
            'total_frames_analyzed': len(detections_list),
            'parking_analysis': {
                'total_spots': estimated_total_spots,
                'occupied_spots': occupied_spots,
                'free_spots': free_spots,
                'occupancy_rate': round((occupied_spots / estimated_total_spots) * 100, 2)
            },
            'car_detections': all_detections[:15],  # Primeiras 15 detecções
            'detection_statistics': {
                'average_cars_per_frame': round(avg_cars_per_frame, 2),
                'max_cars_in_frame': max_cars_in_frame,
                'min_cars_in_frame': min_cars_in_frame,
                'total_detections': len(all_detections)
            },
            'detection_summary': self._get_detection_summary(all_detections)
        }
    
    def _estimate_parking_spots(self, car_count, image_area):
        """
        Estima número total de vagas baseado na quantidade de carros e área da imagem
        Otimizado para imagens de drone de estacionamentos
        
        Args:
            car_count (int): Número de carros detectados
            image_area (int): Área da imagem em pixels
            
        Returns:
            int: Número estimado de vagas
        """
        if car_count == 0:
            return 15  # Padrão mais realista para estacionamento vazio
        elif car_count <= 3:
            return car_count + 5  # Pequeno estacionamento
        elif car_count <= 10:
            return int(car_count * 1.5)  # Pequeno/médio estacionamento
        elif car_count <= 25:
            return int(car_count * 1.3)  # Médio estacionamento  
        elif car_count <= 50:
            return int(car_count * 1.2)  # Grande estacionamento
        else:
            return int(car_count * 1.1)  # Estacionamento muito grande
    
    def _estimate_parking_spots_video(self, max_cars):
        """
        Estima número total de vagas para vídeo baseado no máximo de carros
        
        Args:
            max_cars (int): Máximo de carros detectados em um frame
            
        Returns:
            int: Número estimado de vagas
        """
        if max_cars == 0:
            return 15  # Padrão para estacionamento vazio
        elif max_cars <= 5:
            return max_cars + 5  # Pequeno estacionamento
        elif max_cars <= 20:
            return int(max_cars * 1.3)  # Médio estacionamento
        else:
            return int(max_cars * 1.15)  # Grande estacionamento
    
    def _get_detection_summary(self, detections):
        """
        Cria resumo das detecções por tipo de veículo
        
        Args:
            detections (list): Lista de detecções
            
        Returns:
            dict: Resumo por tipo de veículo
        """
        summary = {vehicle_type: 0 for vehicle_type in self.vehicle_classes.values()}
        
        for detection in detections:
            vehicle_type = detection.get('class_name', 'unknown')
            if vehicle_type in summary:
                summary[vehicle_type] += 1
        
        return summary
    
    def _empty_video_result(self):
        """
        Retorna resultado vazio para vídeo sem detecções
        
        Returns:
            dict: Resultado vazio
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'file_type': 'video',
            'total_frames_analyzed': 0,
            'parking_analysis': {
                'total_spots': 0,
                'occupied_spots': 0,
                'free_spots': 0,
                'occupancy_rate': 0
            },
            'car_detections': [],
            'detection_statistics': {
                'average_cars_per_frame': 0,
                'max_cars_in_frame': 0,
                'min_cars_in_frame': 0,
                'total_detections': 0
            },
            'detection_summary': {vehicle_type: 0 for vehicle_type in self.vehicle_classes.values()}
        }
