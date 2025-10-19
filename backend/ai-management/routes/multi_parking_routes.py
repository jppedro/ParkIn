from flask import Blueprint, request, jsonify, send_file
import os
import json
import cv2
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from services.parking_manager import ParkingManager
from config import Config

multi_parking_bp = Blueprint('multi_parking', __name__)

# Inicializar gerenciador
parking_manager = ParkingManager(data_folder="parking_data")

class MultiParkingRoutes:
    
    @staticmethod
    @multi_parking_bp.route('/setup', methods=['POST'])
    def setup_parking_area():
        """
        POST /api/parking/setup
        
        Cria uma nova área de estacionamento e faz upload da imagem de referência
        
        Body (form-data):
        - name: Nome da área (ex: "Fragmento A")
        - description: Descrição (opcional)
        - reference_image: Arquivo de imagem (opcional)
        
        Returns:
        {
            "success": true,
            "parking_id": "uuid-xxx-xxx",
            "message": "Área criada com sucesso",
            "next_step": "Use /define-slots para definir as vagas"
        }
        """
        try:
            # Obter dados do formulário
            name = request.form.get('name')
            description = request.form.get('description', '')
            
            if not name:
                return jsonify({'error': 'Campo "name" é obrigatório'}), 400
            
            # Processar imagem de referência (se enviada)
            reference_image_path = None
            if 'reference_image' in request.files:
                file = request.files['reference_image']
                
                if file.filename != '':
                    # Validar extensão
                    filename_lower = file.filename.lower()
                    is_image = filename_lower.endswith(tuple(Config.ALLOWED_IMAGE_EXTENSIONS))
                    
                    if not is_image:
                        return jsonify({
                            'error': 'Formato de imagem inválido. Use: .jpg, .jpeg, .png, .bmp'
                        }), 400
                    
                    # Salvar temporariamente
                    ext = filename_lower.split('.')[-1]
                    temp_filename = f"temp_ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    reference_image_path = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
                    file.save(reference_image_path)
            
            # Criar área de estacionamento
            parking_id = parking_manager.create_parking_area(
                name=name,
                description=description,
                reference_image_path=reference_image_path
            )
            
            return jsonify({
                'success': True,
                'parking_id': parking_id,
                'name': name,
                'message': 'Área de estacionamento criada com sucesso',
                'next_step': f'Use POST /api/parking/define-slots com parking_id={parking_id} para definir as vagas'
            }), 201
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/define-slots', methods=['POST'])
    def define_slots():
        """
        POST /api/parking/define-slots
        
        Define as coordenadas das vagas para uma área
        
        Body (JSON):
        {
            "parking_id": "uuid-xxx-xxx",
            "slots": [
                {
                    "id": 1,
                    "coordinates": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                },
                ...
            ]
        }
        
        Returns:
        {
            "success": true,
            "parking_id": "uuid-xxx-xxx",
            "total_slots": 10,
            "message": "Vagas definidas com sucesso"
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Body JSON é obrigatório'}), 400
            
            parking_id = data.get('parking_id')
            slots = data.get('slots')
            
            if not parking_id:
                return jsonify({'error': 'Campo "parking_id" é obrigatório'}), 400
            
            if not slots or not isinstance(slots, list):
                return jsonify({'error': 'Campo "slots" deve ser uma lista'}), 400
            
            # Validar estrutura das vagas
            for slot in slots:
                if 'id' not in slot or 'coordinates' not in slot:
                    return jsonify({
                        'error': 'Cada vaga deve ter "id" e "coordinates"'
                    }), 400
                
                if not isinstance(slot['coordinates'], list) or len(slot['coordinates']) < 3:
                    return jsonify({
                        'error': 'coordinates deve ser uma lista com pelo menos 3 pontos [[x1,y1], [x2,y2], ...]'
                    }), 400
            
            # Definir vagas
            success = parking_manager.define_slots(parking_id, slots)
            
            if success:
                # Gerar imagem marcada e salvar em uploads/
                metadata = parking_manager.get_parking_metadata(parking_id)
                reference_image = metadata.get('reference_image')
                
                if reference_image and os.path.exists(reference_image):
                    # Carregar imagem
                    img = cv2.imread(reference_image)
                    
                    if img is not None:
                        # Desenhar vagas
                        for slot in slots:
                            coords = slot['coordinates']
                            
                            # Converter coordenadas para array numpy
                            pts = np.array(coords, np.int32)
                            pts = pts.reshape((-1, 1, 2))
                            
                            # Desenhar polígono verde
                            cv2.polylines(img, [pts], True, (0, 255, 0), 3)
                            
                            # Desenhar número da vaga
                            center_x = int(np.mean([p[0] for p in coords]))
                            center_y = int(np.mean([p[1] for p in coords]))
                            
                            cv2.putText(
                                img,
                                f"#{slot['id']}",
                                (center_x - 20, center_y + 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (255, 255, 255),
                                2
                            )
                        
                        # Salvar em uploads/
                        marked_filename = f"parking_slots_{parking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        marked_path = os.path.join(Config.UPLOAD_FOLDER, marked_filename)
                        cv2.imwrite(marked_path, img)
                        
                        print(f"✅ Imagem marcada salva em: {marked_path}")
                
                return jsonify({
                    'success': True,
                    'parking_id': parking_id,
                    'total_slots': len(slots),
                    'message': f'{len(slots)} vagas definidas com sucesso',
                    'marked_image': f'uploads/{marked_filename}' if reference_image and os.path.exists(reference_image) else None,
                    'next_step': f'Use POST /api/parking/detect com parking_id={parking_id} para detectar ocupação'
                }), 200
            else:
                return jsonify({'error': 'Erro ao definir vagas'}), 500
        
        except ValueError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/detect', methods=['POST'])
    def detect_occupancy():
        """
        POST /api/parking/detect
        
        Detecta ocupação das vagas em uma área específica
        
        Body (form-data):
        - parking_id: UUID da área
        - image: Arquivo de imagem para análise
        
        Returns:
        {
            "success": true,
            "parking_id": "uuid-xxx-xxx",
            "parking_name": "Fragmento A",
            "total_slots": 10,
            "occupied": 7,
            "empty": 3,
            "occupancy_rate": 0.7,
            "cars_detected": 7,
            "slots": [...],
            "timestamp": "2024-01-15T10:30:00",
            "annotated_image": "/path/to/image.jpg"
        }
        """
        try:
            # Obter parking_id
            parking_id = request.form.get('parking_id')
            
            if not parking_id:
                return jsonify({'error': 'Campo "parking_id" é obrigatório'}), 400
            
            # Verificar se imagem foi enviada
            if 'image' not in request.files:
                return jsonify({'error': 'Campo "image" é obrigatório'}), 400
            
            file = request.files['image']
            
            if file.filename == '':
                return jsonify({'error': 'Nenhuma imagem selecionada'}), 400
            
            # Validar extensão
            filename_lower = file.filename.lower()
            is_image = filename_lower.endswith(tuple(Config.ALLOWED_IMAGE_EXTENSIONS))
            
            if not is_image:
                return jsonify({
                    'error': 'Formato de imagem inválido. Use: .jpg, .jpeg, .png, .bmp'
                }), 400
            
            # Salvar imagem temporariamente
            ext = filename_lower.split('.')[-1]
            temp_filename = f"detect_{parking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            image_path = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
            file.save(image_path)
            
            # Detectar ocupação
            results = parking_manager.detect_occupancy(
                parking_id=parking_id,
                image_path=image_path,
                model_path="models/best.pt"
            )
            
            return jsonify({
                'success': True,
                **results
            }), 200
        
        except ValueError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/status', methods=['GET'])
    def get_status():
        """
        GET /api/parking/status?parking_id=xxx
        
        Retorna o status atual de uma área (último resultado salvo)
        
        Query params:
        - parking_id: UUID da área
        
        Returns:
        {
            "success": true,
            "parking_id": "uuid-xxx-xxx",
            "name": "Fragmento A",
            "last_detection": {...}  // Último resultado ou null
        }
        """
        try:
            parking_id = request.args.get('parking_id')
            
            if not parking_id:
                return jsonify({'error': 'Query param "parking_id" é obrigatório'}), 400
            
            # Obter metadados
            metadata = parking_manager.get_parking_metadata(parking_id)
            
            if not metadata:
                return jsonify({'error': f'Área não encontrada: {parking_id}'}), 404
            
            # Buscar último resultado (se existir)
            parking_folder = os.path.join(parking_manager.data_folder, parking_id)
            results_folder = os.path.join(parking_folder, "results")
            
            last_detection = None
            if os.path.exists(results_folder):
                # Buscar arquivo mais recente
                history_files = sorted(
                    [f for f in os.listdir(results_folder) if f.startswith('history_')],
                    reverse=True
                )
                
                if history_files:
                    with open(os.path.join(results_folder, history_files[0]), 'r') as f:
                        last_detection = json.load(f)
            
            return jsonify({
                'success': True,
                'parking_id': parking_id,
                'name': metadata['name'],
                'description': metadata.get('description', ''),
                'total_slots': metadata['total_slots'],
                'slots_defined': metadata['slots_defined'],
                'created_at': metadata['created_at'],
                'last_detection': last_detection
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/list', methods=['GET'])
    def list_parkings():
        """
        GET /api/parking/list
        
        Lista todas as áreas de estacionamento cadastradas
        
        Returns:
        {
            "success": true,
            "total": 3,
            "parkings": [
                {
                    "parking_id": "uuid-xxx-xxx",
                    "name": "Fragmento A",
                    "description": "Zona Norte",
                    "created_at": "2024-01-15T10:00:00",
                    "slots_defined": true,
                    "total_slots": 10
                },
                ...
            ]
        }
        """
        try:
            parkings = parking_manager.list_parking_areas()
            
            return jsonify({
                'success': True,
                'total': len(parkings),
                'parkings': parkings
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/delete', methods=['DELETE'])
    def delete_parking():
        """
        DELETE /api/parking/delete
        
        Remove uma área de estacionamento
        
        Body (JSON):
        {
            "parking_id": "uuid-xxx-xxx"
        }
        
        Returns:
        {
            "success": true,
            "message": "Área removida com sucesso"
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Body JSON é obrigatório'}), 400
            
            parking_id = data.get('parking_id')
            
            if not parking_id:
                return jsonify({'error': 'Campo "parking_id" é obrigatório'}), 400
            
            success = parking_manager.delete_parking_area(parking_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Área {parking_id} removida com sucesso'
                }), 200
            else:
                return jsonify({'error': 'Área não encontrada'}), 404
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @multi_parking_bp.route('/image/<parking_id>', methods=['GET'])
    def get_parking_image(parking_id):
        """
        GET /api/parking/image/<parking_id>
        
        Retorna a imagem de referência de uma área
        """
        try:
            metadata = parking_manager.get_parking_metadata(parking_id)
            
            if not metadata:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            reference_image = metadata.get('reference_image')
            
            if not reference_image or not os.path.exists(reference_image):
                return jsonify({'error': 'Imagem de referência não encontrada'}), 404
            
            return send_file(reference_image, mimetype='image/jpeg')
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
