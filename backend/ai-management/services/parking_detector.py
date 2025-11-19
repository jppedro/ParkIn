from ultralytics import YOLO
import cv2
import json
import numpy as np
import os
from pathlib import Path
from datetime import datetime

class ParkingDetector:
    
    def __init__(self, model_path="models/best.pt", slots_file="parking_slots.json"):
        # Carregar modelo YOLO
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
        
        self.model = YOLO(model_path)
        print(f"✅ Modelo YOLO carregado: {model_path}")
        print(f"   Classes: {self.model.names}")
        
        # Carregar coordenadas das vagas
        if not os.path.exists(slots_file):
            raise FileNotFoundError(f"Arquivo de vagas não encontrado: {slots_file}")
        
        with open(slots_file, 'r') as f:
            data = json.load(f)
        
        self.slots = data['slots']
        self.total_slots = len(self.slots)
        self.original_slots = [slot.copy() for slot in self.slots]  # Backup das coordenadas originais
        print(f"Coordenadas das vagas carregadas: {self.total_slots} vagas")
        
        # Configurações
        self.confidence_threshold = 0.25  # Confiança mínima para detectar carros (reduzido para detectar mais)
        self.overlap_threshold = 0.3      # 30% de sobreposição para considerar ocupada
        self.reference_dimensions = None  
    
    def _point_in_polygon(self, point, polygon):
        """Verifica se um ponto está dentro de um polígono"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _calculate_overlap_percentage(self, box, polygon):
        x1, y1, x2, y2 = box
        
        # Grid de pontos para testar sobreposição (7x7 = 49 pontos)
        test_points = []
        for i in range(7):
            for j in range(7):
                px = x1 + (x2 - x1) * i / 6
                py = y1 + (y2 - y1) * j / 6
                test_points.append((px, py))
        
        # Contar quantos pontos estão dentro do polígono
        points_inside = sum(1 for p in test_points if self._point_in_polygon(p, polygon))
        
        # Calcular porcentagem
        overlap_percentage = points_inside / len(test_points)
        
        return overlap_percentage
    
    def scale_coordinates(self, reference_width, reference_height, target_width, target_height):
        scale_x = target_width / reference_width
        scale_y = target_height / reference_height
        
        print(f"   📐 Escalando coordenadas:")
        print(f"      Referência: {reference_width}x{reference_height}")
        print(f"      Alvo: {target_width}x{target_height}")
        print(f"      Escala: X={scale_x:.3f}, Y={scale_y:.3f}")

        self.slots = [slot.copy() for slot in self.original_slots]
        
        # Escalar coordenadas de cada vaga
        for i, slot in enumerate(self.slots):
            scaled_coords = []
            for x, y in self.original_slots[i]['coordinates']:
                scaled_x = int(x * scale_x)
                scaled_y = int(y * scale_y)
                scaled_coords.append([scaled_x, scaled_y])
            
            self.slots[i]['coordinates'] = scaled_coords
    
    def detect_cars_in_image(self, image_path, save_result=False, output_path=None):
        print(f"\n🔍 Processando imagem: {image_path}")
        
        # Carregar imagem
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")
        
        img_height, img_width = image.shape[:2]
        print(f"   Dimensões: {img_width}x{img_height}")
        
        # Detectar carros
        results = self.model.predict(
            image_path, 
            conf=0.15,  # Reduzido para detectar mais carros (era 0.25)
            iou=0.4,    # Reduzido para permitir carros próximos (era 0.5)
            imgsz=1920, # Aumentado para melhor detecção (era 1280)
            max_det=300,
            verbose=False
        )
        
        # Extrair bounding boxes dos carros
        cars = []
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cars.append({
                    'box': (x1, y1, x2, y2),
                    'confidence': conf
                })
        
        print(f"   Carros detectados: {len(cars)}")
        
        # Verificar ocupação de cada vaga
        occupied = 0
        empty = 0
        slot_status = []
        
        for slot in self.slots:
            slot_id = slot['id']
            coords = slot['coordinates']
            
            # Verificar se algum carro está nesta vaga
            has_car = False
            max_overlap = 0.0
            
            for car in cars:
                overlap = self._calculate_overlap_percentage(car['box'], coords)
                if overlap > max_overlap:
                    max_overlap = overlap
                
                if overlap >= self.overlap_threshold:
                    has_car = True
                    break
            
            status = "occupied" if has_car else "empty"
            
            if has_car:
                occupied += 1
            else:
                empty += 1
            
            slot_status.append({
                'id': slot_id,
                'status': status,
                'has_car': has_car,
                'overlap': round(max_overlap * 100, 1),
                'coordinates': coords
            })
        
        # Calcular taxa de ocupação
        occupancy_rate = (occupied / self.total_slots * 100) if self.total_slots > 0 else 0
        
        # Preparar resultado
        result = {
            'total_slots': self.total_slots,
            'occupied': occupied,
            'empty': empty,
            'occupancy_rate': round(occupancy_rate, 1),
            'slots': slot_status,
            'cars_detected': len(cars),
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📊 Resultado:")
        print(f"   Total: {self.total_slots} vagas")
        print(f"   Ocupadas: {occupied} ({occupancy_rate:.1f}%)")
        print(f"   Vazias: {empty}")
        
        # Salvar imagem com detecções (opcional)
        if save_result:
            output_image = self._draw_detections(image, cars, slot_status)
            
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"results/detection_{timestamp}.jpg"
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            cv2.imwrite(output_path, output_image)
            result['output_image'] = output_path
            print(f"   Imagem salva: {output_path}")
        
        return result
    
    def _draw_detections(self, image, cars, slot_status):
        """Desenha detecções na imagem"""
        output = image.copy()
        
        # Desenhar carros detectados (azul)
        for car in cars:
            x1, y1, x2, y2 = car['box']
            cv2.rectangle(output, (int(x1), int(y1)), (int(x2), int(y2)), 
                         (255, 0, 0), 2)
            cv2.putText(output, f"{car['confidence']:.2f}", 
                       (int(x1), int(y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (255, 0, 0), 2)
        
        # Desenhar vagas
        for i, slot in enumerate(self.slots):
            coords = np.array(slot['coordinates'])
            has_car = slot_status[i]['has_car']
            
            # Cor: verde (vazia) ou vermelho (ocupada)
            color = (0, 0, 255) if has_car else (0, 255, 0)
            
            # Desenhar polígono preenchido (transparente)
            overlay = output.copy()
            cv2.fillPoly(overlay, [coords], color)
            cv2.addWeighted(overlay, 0.3, output, 0.7, 0, output)
            
            # Contorno do polígono
            cv2.polylines(output, [coords], True, color, 2)
            
            # ID da vaga no centro
            center_x = int(sum(p[0] for p in slot['coordinates']) / 4)
            center_y = int(sum(p[1] for p in slot['coordinates']) / 4)
            cv2.putText(output, f"#{slot['id']}", (center_x-15, center_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Adicionar legenda
        occupied_count = sum(1 for s in slot_status if s['has_car'])
        empty_count = len(slot_status) - occupied_count
        
        cv2.putText(output, f"Ocupadas: {occupied_count} | Vazias: {empty_count}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return output
    
    def get_parking_status(self, image_path):
        """
        Método simplificado para obter status das vagas
        (Compatível com API existente)
        
        Returns:
            dict: Status das vagas
        """
        return self.detect_cars_in_image(image_path, save_result=True)
