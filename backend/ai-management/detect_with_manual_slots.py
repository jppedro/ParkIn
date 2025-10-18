#!/usr/bin/env python3
"""
Detecção de vagas usando:
- Modelo github.pt (detecta carros)
- Coordenadas manuais das vagas (parking_slots.json)
"""

from ultralytics import YOLO
import cv2
import json
import numpy as np
from pathlib import Path

# Configuração
MODEL_PATH = "models/best.pt"
SLOTS_FILE = "parking_slots.json"
CONFIDENCE_THRESHOLD = 0.3

def load_parking_slots(file_path):
    """Carrega coordenadas das vagas do JSON"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data['slots']

def point_in_polygon(point, polygon):
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

def calculate_overlap_percentage(box, polygon):
    """
    Calcula % de sobreposição entre bounding box do carro e polígono da vaga
    Retorna valor entre 0.0 (sem sobreposição) e 1.0 (100% sobreposto)
    """
    x1, y1, x2, y2 = box
    
    # Grid de pontos para testar sobreposição (7x7 = 49 pontos)
    # Mais pontos = detecção mais precisa
    test_points = []
    for i in range(7):
        for j in range(7):
            px = x1 + (x2 - x1) * i / 6
            py = y1 + (y2 - y1) * j / 6
            test_points.append((px, py))
    
    # Contar quantos pontos estão dentro do polígono
    points_inside = sum(1 for p in test_points if point_in_polygon(p, polygon))
    
    # Calcular porcentagem
    overlap_percentage = points_inside / len(test_points)
    
    return overlap_percentage

def box_intersects_polygon(box, polygon, threshold=0.3):
    """
    Verifica se bounding box do carro está sobreposto à vaga
    threshold: % mínima de sobreposição (padrão 30% - mais sensível)
    """
    overlap = calculate_overlap_percentage(box, polygon)
    return overlap >= threshold

def detect_parking_occupancy(image_path, output_path=None):
    """
    Detecta ocupação das vagas
    
    Returns:
        dict: {
            'total_slots': int,
            'occupied': int,
            'empty': int,
            'slots': [{id, status, has_car}]
        }
    """
    print("=" * 70)
    print("🚗 DETECÇÃO DE OCUPAÇÃO DE VAGAS")
    print("=" * 70)
    
    # Carregar modelo
    print(f"\n📦 Carregando modelo: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print(f"   Classes: {model.names}")
    
    # Carregar vagas
    print(f"\n📍 Carregando coordenadas das vagas: {SLOTS_FILE}")
    slots = load_parking_slots(SLOTS_FILE)
    print(f"   Total de vagas: {len(slots)}")
    
    # Carregar imagem
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")
    
    print(f"\n📷 Processando: {image_path}")
    print(f"   Dimensões: {image.shape[1]}x{image.shape[0]}")
    
    # Detectar carros
    print(f"\n🔍 Detectando carros (confiança >= {CONFIDENCE_THRESHOLD})...")
    results = model.predict(image_path, conf=CONFIDENCE_THRESHOLD, verbose=False)
    
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
    print(f"\n⚙️  Verificando ocupação das vagas...")
    
    occupied = 0
    empty = 0
    slot_status = []
    
    for slot in slots:
        slot_id = slot['id']
        coords = slot['coordinates']
        
        # Verificar se algum carro está nesta vaga
        has_car = False
        max_overlap = 0.0
        
        for car in cars:
            overlap = calculate_overlap_percentage(car['box'], coords)
            if overlap > max_overlap:
                max_overlap = overlap
            
            if overlap >= 0.3:  # 30% de sobreposição (mais sensível)
                has_car = True
                break
        
        status = "ocupada" if has_car else "vazia"
        
        if has_car:
            occupied += 1
        else:
            empty += 1
        
        slot_status.append({
            'id': slot_id,
            'status': status,
            'has_car': has_car
        })
        
        print(f"   Vaga #{slot_id}: {status} (overlap máx: {max_overlap*100:.1f}%)")
    
    # Desenhar resultado na imagem
    output_image = image.copy()
    
    # Desenhar carros detectados (boxes originais, sem redução)
    for car in cars:
        x1, y1, x2, y2 = car['box']
        
        # Desenhar box do carro (azul) - SEM redução
        cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), 
                     (255, 0, 0), 2)
        
        # Confiança
        cv2.putText(output_image, f"{car['confidence']:.2f}", 
                   (int(x1), int(y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 0, 0), 2)
    
    # Desenhar vagas
    for i, slot in enumerate(slots):
        coords = np.array(slot['coordinates'])
        has_car = slot_status[i]['has_car']
        
        # Cor: verde (vazia) ou vermelho (ocupada)
        color = (0, 0, 255) if has_car else (0, 255, 0)
        
        # Desenhar polígono
        overlay = output_image.copy()
        cv2.fillPoly(overlay, [coords], color)
        cv2.addWeighted(overlay, 0.3, output_image, 0.7, 0, output_image)
        cv2.polylines(output_image, [coords], True, color, 2)
        
        # ID da vaga
        center_x = int(sum(p[0] for p in slot['coordinates']) / 4)
        center_y = int(sum(p[1] for p in slot['coordinates']) / 4)
        cv2.putText(output_image, f"#{slot['id']}", (center_x-15, center_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Adicionar legenda
    cv2.putText(output_image, f"Ocupadas: {occupied} | Vazias: {empty}", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Salvar imagem
    if output_path is None:
        output_path = f"detection_result_{Path(image_path).stem}.jpg"
    
    cv2.imwrite(output_path, output_image)
    print(f"\n✅ Resultado salvo em: {output_path}")
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    print(f"Total de vagas: {len(slots)}")
    print(f"Ocupadas: {occupied} ({occupied/len(slots)*100:.1f}%)")
    print(f"Vazias: {empty} ({empty/len(slots)*100:.1f}%)")
    print(f"Carros detectados: {len(cars)}")
    print("=" * 70)
    
    # Retornar dados
    return {
        'total_slots': len(slots),
        'occupied': occupied,
        'empty': empty,
        'slots': slot_status,
        'cars_detected': len(cars),
        'output_image': output_path
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python detect_with_manual_slots.py <imagem>")
        print("\nExemplo:")
        print("  python detect_with_manual_slots.py uploads/estacionamento.jpeg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = detect_parking_occupancy(image_path, output_path)
    except FileNotFoundError as e:
        print(f"\n❌ Erro: {e}")
        print("\n💡 Certifique-se de:")
        print("   1. Criar parking_slots.json com: python define_parking_slots.py")
        print("   2. Ter o modelo github.pt em models/")
        sys.exit(1)
