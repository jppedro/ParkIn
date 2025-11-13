from flask import Blueprint, request, jsonify, send_file
import os
import json
import cv2
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from services.parking_manager import ParkingManager
from services.video_processor import VideoProcessor
from services.parking_detector import ParkingDetector
from config import Config

multi_parking_bp = Blueprint('multi_parking', __name__)

# Inicializar gerenciador
parking_manager = ParkingManager(data_folder="parking_data")

class MultiParkingRoutes:

    @staticmethod
    @multi_parking_bp.route('/setup', methods=['POST'])
    def setup_parking_area():
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
    def _build_dynamic_layout(parking_id, last_detection_slots):
        """
        Lógica dinâmica para ler as coordenadas e agrupar em fileiras.
        """
        try:
            parking_folder = parking_manager._get_parking_folder(parking_id)
            if not parking_folder:
                return []

            slots_file_path = os.path.join(parking_folder, "parking_slots.json")
            if not os.path.exists(slots_file_path):
                return []

            with open(slots_file_path, 'r') as f:
                layout_data = json.load(f)

            layout_slots = layout_data.get('slots', [])

            status_map = {s['id']: s['status'] for s in last_detection_slots}

            full_slot_data = []
            for slot in layout_slots:
                slot_id = slot['id']
                status = status_map.get(slot_id, 'unknown')

                coords = slot['coordinates']
                center_x = np.mean([p[0] for p in coords])
                center_y = np.mean([p[1] for p in coords])

                full_slot_data.append({
                    'id': slot_id,
                    'status': status,
                    'coordinates': coords,
                    'center_x': center_x,
                    'center_y': center_y
                })

            CLUSTER_THRESHOLD = 60

            if not full_slot_data:
                return []

            sorted_slots = sorted(full_slot_data, key=lambda s: s['center_x'])

            groups = []
            current_group = [sorted_slots[0]]
            last_x = sorted_slots[0]['center_x']

            for slot in sorted_slots[1:]:
                if abs(slot['center_x'] - last_x) < CLUSTER_THRESHOLD:
                    current_group.append(slot)
                else:
                    groups.append(current_group)
                    current_group = [slot]

                last_x = np.mean([s['center_x'] for s in current_group])

            groups.append(current_group)

            for group in groups:
                group.sort(key=lambda s: s['center_y'])

            print(f"✅ Layout dinâmico gerado: {len(groups)} fileiras encontradas.")
            return groups

        except Exception as e:
            print(f"❌ Erro ao construir layout dinâmico: {e}")
            return []

    @staticmethod
    @multi_parking_bp.route('/define-slots', methods=['POST'])
    def define_slots():
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

            marked_filename = None

            if success:
                metadata = parking_manager.get_parking_metadata(parking_id)
                reference_image = metadata.get('reference_image')

                if reference_image and os.path.exists(reference_image):
                    img = cv2.imread(reference_image)

                    if img is not None:
                        for slot in slots:
                            coords = slot['coordinates']

                            pts = np.array(coords, np.int32)
                            pts = pts.reshape((-1, 1, 2))

                            cv2.polylines(img, [pts], True, (0, 255, 0), 3)

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
                    'marked_image': f'uploads/{marked_filename}' if marked_filename else None,
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
    @multi_parking_bp.route('/detect-video', methods=['POST'])
    def detect_video():
        """
        POST /api/parking/detect-video
        
        Processa vídeo de drone e atualiza parking_slots.json a cada 10 segundos
        """
        try:
            # Obter parking_id
            parking_id = request.form.get('parking_id')
            
            if not parking_id:
                return jsonify({'error': 'Campo "parking_id" é obrigatório'}), 400
            
            # Obter intervalo personalizado (opcional, padrão 10 segundos)
            frame_interval = request.form.get('frame_interval', '10')
            try:
                frame_interval = int(frame_interval)
                if frame_interval <= 0:
                    frame_interval = 10
            except ValueError:
                frame_interval = 10
            
            # Verificar se vídeo foi enviado
            if 'video' not in request.files:
                return jsonify({'error': 'Campo "video" é obrigatório'}), 400
            
            file = request.files['video']
            
            if file.filename == '':
                return jsonify({'error': 'Nenhum vídeo selecionado'}), 400
            
            # Validar extensão
            filename_lower = file.filename.lower()
            is_video = filename_lower.endswith(tuple(Config.ALLOWED_VIDEO_EXTENSIONS))
            
            if not is_video:
                return jsonify({
                    'error': f'Formato de vídeo inválido. Use: {", ".join(Config.ALLOWED_VIDEO_EXTENSIONS)}'
                }), 400
            
            # Verificar se área existe e tem vagas definidas
            metadata = parking_manager.get_parking_metadata(parking_id)
            if not metadata:
                return jsonify({'error': f'Área não encontrada: {parking_id}'}), 404
            
            if not metadata.get('slots_defined'):
                return jsonify({
                    'error': f'Vagas não definidas para {parking_id}. Use /define-slots primeiro.'
                }), 400
            
            # Salvar vídeo temporariamente
            ext = filename_lower.split('.')[-1]
            temp_filename = f"video_{parking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            video_path = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
            file.save(video_path)
            
            print(f"✅ Vídeo salvo: {video_path}")
            
            # Obter informações do vídeo
            video_processor = VideoProcessor(frame_interval_seconds=frame_interval)
            video_info = VideoProcessor.get_video_info(video_path)
            
            print(f"📹 Informações do vídeo:")
            print(f"   Duração: {video_info['duration_formatted']}")
            print(f"   FPS: {video_info['fps']:.2f}")
            print(f"   Resolução: {video_info['width']}x{video_info['height']}")
            
            # Carregar detector para esta área
            parking_folder = parking_manager._get_parking_folder(parking_id)
            slots_file = os.path.join(parking_folder, "parking_slots.json")
            
            print(f"📂 Carregando vagas de: {slots_file}")
            if not os.path.exists(slots_file):
                return jsonify({
                    'error': f'Arquivo parking_slots.json não encontrado em: {slots_file}'
                }), 404
            
            detector = ParkingDetector(model_path="models/best.pt", slots_file=slots_file)
            
            # Obter dimensões da imagem de referência
            reference_image_path = metadata.get('reference_image')
            reference_dimensions = None
            if reference_image_path and os.path.exists(reference_image_path):
                import cv2
                ref_img = cv2.imread(reference_image_path)
                if ref_img is not None:
                    ref_height, ref_width = ref_img.shape[:2]
                    reference_dimensions = (ref_width, ref_height)
                    print(f"📏 Imagem de referência: {ref_width}x{ref_height}")
            
            # Processar vídeo
            summary = video_processor.process_video(
                video_path=video_path,
                parking_id=parking_id,
                parking_name=metadata['name'],
                detector=detector,
                parking_folder=parking_folder,
                reference_dimensions=reference_dimensions
            )
            
            # Adicionar informações do vídeo ao resumo
            summary['video_info'] = video_info
            
            return jsonify({
                'success': True,
                'message': 'Vídeo processado com sucesso',
                **summary
            }), 200
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            import traceback
            print(f"❌ Erro ao processar vídeo: {e}")
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    @staticmethod
    @multi_parking_bp.route('/status', methods=['GET'])
    def get_status():
        """
        GET /api/parking/status?parking_id=xxx

        Retorna o status atual E o layout dinâmico das fileiras
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
            history_file = os.path.join(results_folder, "history.json")

            last_detection = None
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    last_detection = json.load(f)

            layout_groups = MultiParkingRoutes._build_dynamic_layout(
                parking_id,
                last_detection.get('slots', []) if last_detection else []
            )

            return jsonify({
                'success': True,
                'parking_id': parking_id,
                'name': metadata['name'],
                'description': metadata.get('description', ''),
                'total_slots': metadata['total_slots'],
                'slots_defined': metadata['slots_defined'],
                'created_at': metadata['created_at'],
                'last_detection': last_detection,
                'layout_groups': layout_groups
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    @multi_parking_bp.route('/list', methods=['GET'])
    def list_parkings():
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
        try:
            metadata = parking_manager.get_parking_metadata(parking_id)

            if not metadata:
                return jsonify({'error': 'Área não encontrada'}), 404

            # Obter tipo de imagem solicitado
            image_type = request.args.get('type', 'reference')

            image_path = None

            if image_type == 'detection':
                # Buscar última imagem de detecção
                results_folder = os.path.join(
                    parking_manager.data_folder,
                    parking_id,
                    'results'
                )

                if not os.path.exists(results_folder):
                    return jsonify({'error': 'Nenhuma detecção disponível'}), 404

                # Listar arquivos de detecção (ordenar por data)
                detection_files = [
                    f for f in os.listdir(results_folder)
                    if f.startswith('detection_') and f.endswith(('.jpg', '.jpeg', '.png'))
                ]

                if not detection_files:
                    return jsonify({'error': 'Nenhuma imagem de detecção disponível'}), 404

                # Pegar a mais recente
                detection_files.sort(reverse=True)
                image_path = os.path.join(results_folder, detection_files[0])

            else:
                image_path_from_json = metadata.get('reference_image')

                parking_folder_abs = parking_manager._get_parking_folder(parking_id)
                if not parking_folder_abs:
                     return jsonify({'error': 'Pasta da área não encontrada'}), 404

                if not image_path_from_json:
                     return jsonify({'error': 'Caminho da imagem não definido no metadata.json'}), 404
                image_filename = os.path.basename(image_path_from_json)

                correct_image_path = os.path.join(parking_folder_abs, image_filename)

                if not os.path.exists(correct_image_path):
                    return jsonify({
                        'error': f'Imagem não encontrada (check: {correct_image_path})'
                    }), 404

                image_path = correct_image_path

            return send_file(image_path, mimetype='image/jpeg')

        except Exception as e:
            return jsonify({'error': str(e)}), 500