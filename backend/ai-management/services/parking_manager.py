"""
ParkingManager - Gerencia múltiplas áreas de estacionamento
Cada área tem:
- parking_id: identificador único
- reference_image: imagem de referência do fragmento
- slots_file: coordenadas das vagas (parking_slots_{parking_id}.json)
- metadata: nome, descrição, etc.
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from services.parking_detector import ParkingDetector


class ParkingManager:
    
    def __init__(self, data_folder="parking_data"):
        """
        Inicializa o gerenciador de múltiplas áreas de estacionamento
        
        Args:
            data_folder: Pasta onde ficam os dados de cada parking_id
        """

        current_dir = os.path.dirname(os.path.abspath(__file__))
        ai_management_dir = os.path.dirname(current_dir)
        self.data_folder = os.path.join(ai_management_dir, data_folder)
        self.index_file = os.path.join(self.data_folder, "parking_index.json")
        
        print(f"🔍 ParkingManager inicializado")
        print(f"   Data folder: {self.data_folder}")
        
        # Criar estrutura de pastas
        os.makedirs(self.data_folder, exist_ok=True)
        
        # Carregar ou criar índice
        self._load_index()
    
    def _load_index(self):
        """Carrega índice de estacionamentos"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {"parkings": []}
            self._save_index()
    
    def _save_index(self):
        """Salva índice de estacionamentos"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def create_parking_area(self, name: str, description: str = "", reference_image_path: str = None) -> str:
        """
        Cria uma nova área de estacionamento
        
        Args:
            name: Nome da área (ex: "Fragmento A", "Zona Norte")
            description: Descrição opcional
            reference_image_path: Caminho da imagem de referência (opcional)
        
        Returns:
            parking_id: UUID da nova área criada
        """
        parking_id = str(uuid.uuid4())
        
        # Criar pasta para este estacionamento
        parking_folder = os.path.join(self.data_folder, parking_id)
        os.makedirs(parking_folder, exist_ok=True)
        
        # Criar metadados
        metadata = {
            "parking_id": parking_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "reference_image": None,
            "slots_defined": False,
            "total_slots": 0
        }
        
        # Copiar imagem de referência se fornecida
        if reference_image_path and os.path.exists(reference_image_path):
            ext = os.path.splitext(reference_image_path)[1]
            new_image_path = os.path.join(parking_folder, f"reference{ext}")
            
            import shutil
            shutil.copy(reference_image_path, new_image_path)
            # Salvar caminho ABSOLUTO para evitar problemas com cwd
            metadata["reference_image"] = os.path.abspath(new_image_path)
        
        # Salvar metadados
        metadata_file = os.path.join(parking_folder, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Adicionar ao índice
        self.index["parkings"].append({
            "parking_id": parking_id,
            "name": name,
            "created_at": metadata["created_at"]
        })
        self._save_index()
        
        print(f"✅ Área de estacionamento criada: {parking_id} ({name})")
        return parking_id
    
    def define_slots(self, parking_id: str, slots: List[Dict]) -> bool:
        """
        Define as vagas para uma área de estacionamento
        
        Args:
            parking_id: ID da área
            slots: Lista de vagas [{"id": 1, "coordinates": [[x1,y1], [x2,y2], ...]}, ...]
        
        Returns:
            bool: True se sucesso
        """
        parking_folder = self._get_parking_folder(parking_id)
        if not parking_folder:
            raise ValueError(f"Área de estacionamento não encontrada: {parking_id}")
        
        # Salvar coordenadas das vagas
        slots_file = os.path.join(parking_folder, "parking_slots.json")
        slots_data = {
            "parking_id": parking_id,
            "total_slots": len(slots),
            "defined_at": datetime.now().isoformat(),
            "slots": slots
        }
        
        with open(slots_file, 'w') as f:
            json.dump(slots_data, f, indent=2)
        
        # Atualizar metadados
        metadata_file = os.path.join(parking_folder, "metadata.json")
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        metadata["slots_defined"] = True
        metadata["total_slots"] = len(slots)
        metadata["slots_file"] = slots_file
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ {len(slots)} vagas definidas para {parking_id}")
        return True
    
    def get_parking_metadata(self, parking_id: str) -> Optional[Dict]:
        """Retorna metadados de uma área"""
        parking_folder = self._get_parking_folder(parking_id)
        if not parking_folder:
            return None
        
        metadata_file = os.path.join(parking_folder, "metadata.json")
        if not os.path.exists(metadata_file):
            return None
        
        with open(metadata_file, 'r') as f:
            return json.load(f)
    
    def list_parking_areas(self) -> List[Dict]:
        """Lista todas as áreas de estacionamento"""
        result = []
        
        for parking_info in self.index["parkings"]:
            parking_id = parking_info["parking_id"]
            metadata = self.get_parking_metadata(parking_id)
            
            if metadata:
                result.append({
                    "parking_id": parking_id,
                    "name": metadata["name"],
                    "description": metadata.get("description", ""),
                    "created_at": metadata["created_at"],
                    "slots_defined": metadata["slots_defined"],
                    "total_slots": metadata["total_slots"]
                })
        
        return result
    
    def detect_occupancy(self, parking_id: str, image_path: str, model_path: str = "models/best.pt") -> Dict:
        """
        Detecta ocupação de vagas em uma área específica
        
        Args:
            parking_id: ID da área
            image_path: Caminho da imagem para análise
            model_path: Caminho do modelo YOLO
        
        Returns:
            Dict com resultados da detecção
        """
        parking_folder = self._get_parking_folder(parking_id)
        if not parking_folder:
            raise ValueError(f"Área de estacionamento não encontrada: {parking_id}")
        
        # Verificar se vagas foram definidas
        metadata = self.get_parking_metadata(parking_id)
        if not metadata or not metadata["slots_defined"]:
            raise ValueError(f"Vagas não definidas para {parking_id}. Use /define-slots primeiro.")
        
        # Carregar detector para esta área específica
        slots_file = os.path.join(parking_folder, "parking_slots.json")
        detector = ParkingDetector(model_path=model_path, slots_file=slots_file)
        
        # Detectar ocupação
        results_folder = os.path.join(parking_folder, "results")
        os.makedirs(results_folder, exist_ok=True)
        
        # Sempre salvar como detection.jpg (sobrescreve a anterior)
        output_image = os.path.join(results_folder, "detection.jpg")
        
        results = detector.detect_cars_in_image(
            image_path,
            save_result=True,
            output_path=output_image
        )
        
        # Adicionar informações da área
        results["parking_id"] = parking_id
        results["parking_name"] = metadata["name"]
        results["annotated_image"] = output_image
        
        # Salvar histórico (sempre sobrescreve o mesmo arquivo)
        history_file = os.path.join(results_folder, "history.json")
        with open(history_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def delete_parking_area(self, parking_id: str) -> bool:
        """Remove uma área de estacionamento"""
        parking_folder = self._get_parking_folder(parking_id)
        if not parking_folder:
            return False
        
        # Remover pasta
        import shutil
        shutil.rmtree(parking_folder)
        
        # Remover do índice
        self.index["parkings"] = [p for p in self.index["parkings"] if p["parking_id"] != parking_id]
        self._save_index()
        
        print(f"✅ Área de estacionamento removida: {parking_id}")
        return True
    
    def _get_parking_folder(self, parking_id: str) -> Optional[str]:
        """Retorna o caminho da pasta de uma área"""
        parking_folder = os.path.join(self.data_folder, parking_id)
        if os.path.exists(parking_folder):
            return parking_folder
        return None
