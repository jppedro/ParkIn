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

        # Tentar carregar o modelo principal
        if not os.path.exists(model_path):
            # Tentar fallback
            if hasattr(Config, 'YOLO_MODEL_PATH_FALLBACK') and os.path.exists(Config.YOLO_MODEL_PATH_FALLBACK):
                print(f"AVISO: Modelo principal não encontrado em '{model_path}'.")
                print(f"       Usando modelo fallback: '{Config.YOLO_MODEL_PATH_FALLBACK}'")
                model_path = Config.YOLO_MODEL_PATH_FALLBACK
            else:
                print(f"AVISO: Nenhum modelo customizado encontrado. Carregando 'yolov8s.pt' padrão.")
                self.model = YOLO('yolov8s.pt')
                self.class_names = self.model.names
                print(f"Classes detectáveis: {self.class_names}")
                return
        
        self.model = YOLO(model_path)
        print(f"✅ Modelo YOLO carregado de '{model_path}'.")
        
        self.class_names = self.model.names
        print(f"📊 Classes detectáveis: {self.class_names}")

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
        try:
            results = self.model(image_path, verbose=False, conf=0.15)[0]  # Reduzir threshold para 15%
            detected_spots, detected_cars = [], []

            # Verificar se há detecções
            if results.boxes is None or len(results.boxes) == 0:
                print(f"Nenhuma detecção encontrada na imagem: {image_path}")
                return {
                    'timestamp': datetime.now().isoformat(), 
                    'error': 'Nenhuma vaga detectada.',
                    'parking_analysis': {
                        'total_spots': 0, 
                        'occupied_spots': 0, 
                        'free_spots': 0, 
                        'occupancy_rate': 0, 
                        'spots': []
                    }
                }

            for box in results.boxes:
                class_id = int(box.cls[0])
                class_name = self.class_names.get(class_id)
                confidence = float(box.conf[0])
                
                # Suporte para diferentes nomenclaturas de classes
                # Modelo aerial: 'enpty', 'not_enpty'
                # Modelo antigo: 'empty_spot', 'occupied_spot'
                if class_name in ['empty_spot', 'enpty']:
                    detected_spots.append({
                        'box': box.xyxy[0].tolist(), 
                        'status': 'free',
                        'confidence': confidence
                    })
                elif class_name in ['occupied_spot', 'not_enpty']:
                    detected_spots.append({
                        'box': box.xyxy[0].tolist(), 
                        'status': 'occupied',
                        'confidence': confidence
                    })

            if not detected_spots:
                print(f"⚠️ Detecções encontradas mas nenhuma vaga reconhecida")
                return {
                    'timestamp': datetime.now().isoformat(), 
                    'error': 'Nenhuma vaga detectada.',
                    'parking_analysis': {
                        'total_spots': 0, 
                        'occupied_spots': 0, 
                        'free_spots': 0, 
                        'occupancy_rate': 0, 
                        'spots': []
                    }
                }
        except Exception as e:
            print(f"❌ Erro ao detectar em imagem: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(), 
                'error': f'Erro na detecção: {str(e)}',
                'parking_analysis': {
                    'total_spots': 0, 
                    'occupied_spots': 0, 
                    'free_spots': 0, 
                    'occupancy_rate': 0, 
                    'spots': []
                }
            }

        occupied_count = 0
        spot_statuses = []
        for i, spot_data in enumerate(detected_spots):
            status = spot_data['status']
            spot_box = spot_data['box']
            if status == 'occupied': 
                occupied_count += 1
            spot_statuses.append({'spot_id': i + 1, 'box': spot_box, 'status': status})

        total_spots = len(detected_spots)
        return {'timestamp': datetime.now().isoformat(), 'parking_analysis': {'total_spots': total_spots, 'occupied_spots': occupied_count, 'free_spots': total_spots - occupied_count, 'occupancy_rate': round((occupied_count / total_spots * 100), 2), 'spots': spot_statuses}}

    def detect_cars_in_video(self, video_path):
        """
        Analisa vídeo frame a frame para detectar vagas de estacionamento
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened(): 
            raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, total_frames // Config.VIDEO_FRAME_ANALYSIS_COUNT)
        frame_analyses = []
        frame_count = 0
        frames_with_detections = 0

        print(f"🎬 Analisando vídeo: {total_frames} frames, intervalo: {frame_interval}")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break
                
            if frame_count % frame_interval == 0:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                    cv2.imwrite(tmp_file.name, frame)
                    try:
                        analysis = self.detect_cars_in_image(tmp_file.name)
                        
                        # Só adicionar se não teve erro
                        if 'error' not in analysis:
                            frame_analyses.append(analysis['parking_analysis'])
                            frames_with_detections += 1
                            print(f"✅ Frame {frame_count}: {analysis['parking_analysis']['total_spots']} vagas detectadas")
                        else:
                            print(f"⚠️ Frame {frame_count}: {analysis['error']}")
                    except Exception as e:
                        print(f"❌ Erro ao processar frame {frame_count}: {str(e)}")
                    finally:
                        try:
                            os.unlink(tmp_file.name)
                        except:
                            pass
                            
            frame_count += 1
            
        cap.release()

        if not frame_analyses:
            print("❌ Nenhum frame do vídeo pôde ser analisado com sucesso")
            return {
                'timestamp': datetime.now().isoformat(), 
                'error': 'Nenhum frame do vídeo pôde ser analisado. Verifique se o vídeo contém imagens aéreas de estacionamento.',
                'parking_analysis': {
                    'total_spots': 0,
                    'occupied_spots': 0,
                    'free_spots': 0,
                    'occupancy_rate': 0,
                    'frames_analyzed': 0,
                    'frames_with_detections': 0
                }
            }

        print(f"✅ Análise completa: {frames_with_detections} frames com detecções")
        return self._consolidate_video_results(frame_analyses)

    def _consolidate_video_results(self, frame_analyses):
        """
        Consolida resultados de múltiplos frames em uma análise final
        """
        if not frame_analyses:
            return {
                'timestamp': datetime.now().isoformat(),
                'file_type': 'video',
                'frames_analyzed': 0,
                'parking_analysis': {
                    'total_spots': 0,
                    'occupied_spots': 0,
                    'free_spots': 0,
                    'occupancy_rate': 0,
                    'description': 'Nenhum frame analisado com sucesso.'
                }
            }
        
        # Pegar o frame com mais vagas detectadas
        max_spots_frame = max(frame_analyses, key=lambda x: x.get('total_spots', 0))
        total_spots = max_spots_frame.get('total_spots', 0)
        
        if total_spots == 0:
            return {
                'timestamp': datetime.now().isoformat(),
                'file_type': 'video',
                'frames_analyzed': len(frame_analyses),
                'parking_analysis': {
                    'total_spots': 0,
                    'occupied_spots': 0,
                    'free_spots': 0,
                    'occupancy_rate': 0,
                    'description': 'Nenhuma vaga detectada nos frames analisados.'
                }
            }
        
        # Calcular média de vagas ocupadas
        avg_occupied = round(sum(a.get('occupied_spots', 0) for a in frame_analyses) / len(frame_analyses))
        avg_free = total_spots - avg_occupied
        
        return {
            'timestamp': datetime.now().isoformat(), 
            'file_type': 'video', 
            'frames_analyzed': len(frame_analyses), 
            'parking_analysis': {
                'total_spots': total_spots, 
                'occupied_spots': avg_occupied, 
                'free_spots': avg_free, 
                'occupancy_rate': round((avg_occupied / total_spots * 100), 2), 
                'description': f'Resultados baseados na ocupação média de {len(frame_analyses)} frames analisados.'
            }
        }

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