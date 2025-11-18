#!/usr/bin/env python3
"""
CLI para definir vagas de estacionamento para uma área específica
Uso: python3 define_slots_for_parking.py <parking_id>
"""

import sys
import os
import cv2
import json
import numpy as np
from pathlib import Path

class ParkingSlotDefiner:
    def __init__(self, parking_id, data_folder="parking_data"):
        self.parking_id = parking_id
        self.data_folder = data_folder
        self.parking_folder = os.path.join(data_folder, parking_id)
        
        # Verificar se área existe
        if not os.path.exists(self.parking_folder):
            raise ValueError(f"❌ Área não encontrada: {parking_id}")
        
        # Carregar metadados
        metadata_file = os.path.join(self.parking_folder, "metadata.json")
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)
        
        # Verificar imagem de referência
        reference_image = self.metadata.get('reference_image')
        if not reference_image or not os.path.exists(reference_image):
            raise ValueError(f"❌ Imagem de referência não encontrada para {parking_id}")
        
        self.image_path = reference_image
        self.image = cv2.imread(self.image_path)
        
        if self.image is None:
            raise ValueError(f"❌ Erro ao carregar imagem: {self.image_path}")
        
        self.display_image = self.image.copy()
        self.current_polygon = []
        self.slots = []
        self.window_name = f"Definir Vagas - {self.metadata['name']}"
        
        print(f"\nÁrea carregada: {self.metadata['name']}")
        print(f"   Parking ID: {parking_id}")
        print(f"   Imagem: {self.image_path}")
        print(f"   Dimensões: {self.image.shape[1]}x{self.image.shape[0]}")
    
    def mouse_callback(self, event, x, y, flags, param):
        """Callback para cliques do mouse"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Adicionar ponto ao polígono atual
            self.current_polygon.append([x, y])
            
            # Desenhar ponto
            cv2.circle(self.display_image, (x, y), 5, (0, 255, 0), -1)
            
            # Se temos mais de 1 ponto, desenhar linha
            if len(self.current_polygon) > 1:
                cv2.line(
                    self.display_image,
                    tuple(self.current_polygon[-2]),
                    tuple(self.current_polygon[-1]),
                    (0, 255, 0),
                    2
                )
            
            # Se completamos 4 pontos, fechar polígono
            if len(self.current_polygon) == 4:
                cv2.line(
                    self.display_image,
                    tuple(self.current_polygon[-1]),
                    tuple(self.current_polygon[0]),
                    (0, 255, 0),
                    2
                )
                
                # Adicionar slot
                slot_id = len(self.slots) + 1
                self.slots.append({
                    "id": slot_id,
                    "coordinates": self.current_polygon.copy()
                })
                
                # Desenhar número da vaga
                center_x = int(np.mean([p[0] for p in self.current_polygon]))
                center_y = int(np.mean([p[1] for p in self.current_polygon]))
                
                cv2.putText(
                    self.display_image,
                    f"#{slot_id}",
                    (center_x - 15, center_y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
                
                print(f"   ✅ Vaga #{slot_id} definida")
                
                # Resetar polígono atual
                self.current_polygon = []
            
            cv2.imshow(self.window_name, self.display_image)
    
    def run(self):
        """Executa o processo de definição de vagas"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("\n📝 Instruções:")
        print("   - Clique em 4 pontos para definir cada vaga (sentido horário)")
        print("   - Pressione 'r' para resetar vaga atual")
        print("   - Pressione 'u' para desfazer última vaga")
        print("   - Pressione 's' para salvar e sair")
        print("   - Pressione 'q' para sair sem salvar")
        print(f"\n🚗 Defina as vagas para: {self.metadata['name']}")
        print("=" * 60)
        
        cv2.imshow(self.window_name, self.display_image)
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            # Reset current polygon
            if key == ord('r'):
                if self.current_polygon:
                    print("   ⚠️  Resetando vaga atual...")
                    self.current_polygon = []
                    self.redraw()
            
            # Undo last slot
            elif key == ord('u'):
                if self.slots:
                    removed = self.slots.pop()
                    print(f"   ⚠️  Vaga #{removed['id']} removida")
                    self.redraw()
            
            # Save and quit
            elif key == ord('s'):
                if self.slots:
                    self.save_slots()
                    break
                else:
                    print("   ⚠️  Defina pelo menos uma vaga antes de salvar!")
            
            # Quit without saving
            elif key == ord('q'):
                print("\n❌ Saindo sem salvar...")
                break
        
        cv2.destroyAllWindows()
    
    def redraw(self):
        """Redesenha a imagem com todas as vagas"""
        self.display_image = self.image.copy()
        
        # Desenhar todos os slots salvos
        for slot in self.slots:
            coords = slot['coordinates']
            
            # Desenhar polígono
            for i in range(len(coords)):
                cv2.line(
                    self.display_image,
                    tuple(coords[i]),
                    tuple(coords[(i + 1) % len(coords)]),
                    (0, 255, 0),
                    2
                )
            
            # Desenhar número
            center_x = int(np.mean([p[0] for p in coords]))
            center_y = int(np.mean([p[1] for p in coords]))
            
            cv2.putText(
                self.display_image,
                f"#{slot['id']}",
                (center_x - 15, center_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        # Desenhar polígono atual (se houver)
        for i, point in enumerate(self.current_polygon):
            cv2.circle(self.display_image, tuple(point), 5, (0, 255, 0), -1)
            if i > 0:
                cv2.line(
                    self.display_image,
                    tuple(self.current_polygon[i - 1]),
                    tuple(point),
                    (0, 255, 0),
                    2
                )
        
        cv2.imshow(self.window_name, self.display_image)
    
    def save_slots(self):
        """Salva as vagas definidas"""
        slots_file = os.path.join(self.parking_folder, "parking_slots.json")
        
        slots_data = {
            "parking_id": self.parking_id,
            "total_slots": len(self.slots),
            "defined_at": __import__('datetime').datetime.now().isoformat(),
            "slots": self.slots
        }
        
        with open(slots_file, 'w') as f:
            json.dump(slots_data, f, indent=2)
        
        # Atualizar metadados
        metadata_file = os.path.join(self.parking_folder, "metadata.json")
        self.metadata["slots_defined"] = True
        self.metadata["total_slots"] = len(self.slots)
        self.metadata["slots_file"] = slots_file
        
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Salvar imagem marcada na pasta do parking
        marked_image_parking = os.path.join(self.parking_folder, "parking_slots_marked.jpg")
        cv2.imwrite(marked_image_parking, self.display_image)
        
        # Salvar também em uploads/ (para fácil acesso via API)
        import shutil
        uploads_folder = "uploads"
        os.makedirs(uploads_folder, exist_ok=True)
        marked_image_uploads = os.path.join(uploads_folder, f"parking_slots_{self.parking_id}.jpg")
        shutil.copy(marked_image_parking, marked_image_uploads)
        
        print(f"\n✅ {len(self.slots)} vagas salvas com sucesso!")
        print(f"   JSON: {slots_file}")
        print(f"   Imagem (parking_data): {marked_image_parking}")
        print(f"   Imagem (uploads): {marked_image_uploads}")


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python3 define_slots_for_parking.py <parking_id>")
        print("\nPara listar áreas disponíveis:")
        print("   curl http://localhost:5001/api/parking/list")
        sys.exit(1)
    
    parking_id = sys.argv[1]
    
    try:
        definer = ParkingSlotDefiner(parking_id)
        definer.run()
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
