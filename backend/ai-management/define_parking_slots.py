#!/usr/bin/env python3
"""
Define coordenadas das vagas de estacionamento manualmente
Clique nos 4 cantos de cada vaga (sentido horário)
"""

import cv2
import numpy as np
import json
from pathlib import Path

# Configuração
IMAGE_PATH = "uploads/foto_estacionamento.png"  # Ajuste conforme necessário
OUTPUT_FILE = "parking_slots.json"

image = cv2.imread(IMAGE_PATH)
if image is None:
    print(f"❌ Erro: Imagem não encontrada em {IMAGE_PATH}")
    exit(1)

# Clone para restaurar
original_image = image.copy()

parking_slots = []
points = []
slot_id = 1

def click_and_get_coordinates(event, x, y, flags, param):
    global points, image, slot_id
    
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Ponto {len(points)}: ({x}, {y})")
        
        # Desenhar ponto
        cv2.circle(image, (x, y), 5, (0, 0, 255), -1)
        
        # Desenhar linha conectando pontos
        if len(points) > 1:
            cv2.line(image, points[-2], points[-1], (255, 0, 0), 2)
        
        cv2.imshow("Definir Vagas - Clique nos 4 cantos", image)
        
        # Quando completar 4 pontos
        if len(points) == 4:
            # Fechar polígono
            cv2.line(image, points[-1], points[0], (255, 0, 0), 2)
            
            # Adicionar vaga
            parking_slots.append({
                'id': slot_id,
                'coordinates': points.copy()
            })
            
            # Desenhar polígono preenchido semi-transparente
            overlay = image.copy()
            cv2.fillPoly(overlay, [np.array(points)], (0, 255, 0))
            cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
            
            # Adicionar ID da vaga
            center_x = int(sum(p[0] for p in points) / 4)
            center_y = int(sum(p[1] for p in points) / 4)
            cv2.putText(image, f"#{slot_id}", (center_x-15, center_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            print(f"✅ Vaga #{slot_id} adicionada!")
            print(f"   Coordenadas: {points}")
            
            points = []
            slot_id += 1
            cv2.imshow("Definir Vagas - Clique nos 4 cantos", image)

print("=" * 70)
print("📍 DEFINIÇÃO DE VAGAS DE ESTACIONAMENTO")
print("=" * 70)
print(f"\nImagem: {IMAGE_PATH}")
print(f"Dimensões: {image.shape[1]}x{image.shape[0]}")
print("\n📝 INSTRUÇÕES:")
print("   1. Clique nos 4 cantos de cada vaga (sentido horário)")
print("   2. Pressione 'r' para resetar a vaga atual")
print("   3. Pressione 'u' para desfazer última vaga")
print("   4. Pressione 's' para salvar e sair")
print("   5. Pressione 'q' para sair sem salvar")
print("=" * 70)

cv2.namedWindow("Definir Vagas - Clique nos 4 cantos")
cv2.setMouseCallback("Definir Vagas - Clique nos 4 cantos", click_and_get_coordinates)
cv2.imshow("Definir Vagas - Clique nos 4 cantos", image)

while True:
    key = cv2.waitKey(1) & 0xFF
    
    # 'r' - Reset pontos atuais
    if key == ord('r'):
        if points:
            print("🔄 Resetando pontos atuais...")
            points = []
            image = original_image.copy()
            
            # Redesenhar vagas já salvas
            for slot in parking_slots:
                pts = np.array(slot['coordinates'])
                overlay = image.copy()
                cv2.fillPoly(overlay, [pts], (0, 255, 0))
                cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
                cv2.polylines(image, [pts], True, (255, 0, 0), 2)
                
                center_x = int(sum(p[0] for p in slot['coordinates']) / 4)
                center_y = int(sum(p[1] for p in slot['coordinates']) / 4)
                cv2.putText(image, f"#{slot['id']}", (center_x-15, center_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Definir Vagas - Clique nos 4 cantos", image)
    
    # 'u' - Undo última vaga
    elif key == ord('u'):
        if parking_slots:
            removed = parking_slots.pop()
            slot_id -= 1
            print(f"⬅️  Vaga #{removed['id']} removida")
            
            # Redesenhar tudo
            image = original_image.copy()
            for slot in parking_slots:
                pts = np.array(slot['coordinates'])
                overlay = image.copy()
                cv2.fillPoly(overlay, [pts], (0, 255, 0))
                cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
                cv2.polylines(image, [pts], True, (255, 0, 0), 2)
                
                center_x = int(sum(p[0] for p in slot['coordinates']) / 4)
                center_y = int(sum(p[1] for p in slot['coordinates']) / 4)
                cv2.putText(image, f"#{slot['id']}", (center_x-15, center_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Definir Vagas - Clique nos 4 cantos", image)
    
    # 's' - Salvar
    elif key == ord('s'):
        if parking_slots:
            # Salvar JSON
            data = {
                'image': IMAGE_PATH,
                'image_width': image.shape[1],
                'image_height': image.shape[0],
                'total_slots': len(parking_slots),
                'slots': parking_slots
            }
            
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\n✅ {len(parking_slots)} vagas salvas em: {OUTPUT_FILE}")
            
            # Salvar imagem com vagas marcadas
            output_image = OUTPUT_FILE.replace('.json', '_marked.jpg')
            cv2.imwrite(output_image, image)
            print(f"✅ Imagem salva em: {output_image}")
            break
        else:
            print("⚠️  Nenhuma vaga definida!")
    
    # 'q' - Sair sem salvar
    elif key == ord('q'):
        print("\n❌ Saindo sem salvar...")
        break

cv2.destroyAllWindows()

if parking_slots:
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    print(f"Total de vagas definidas: {len(parking_slots)}")
    print(f"\nArquivo JSON: {OUTPUT_FILE}")
    print(f"Imagem marcada: {OUTPUT_FILE.replace('.json', '_marked.jpg')}")
    print("\n💡 Próximo passo:")
    print(f"   python detect_with_manual_slots.py {IMAGE_PATH}")
    print("=" * 70)
