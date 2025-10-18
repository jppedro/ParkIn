
from flask import Blueprint, request, jsonify, send_file
import os
import json
import glob
from datetime import datetime
from services.parking_detector import ParkingDetector
from config import Config

parking_bp = Blueprint('parking', __name__)

# Inicializar detector com modelo e coordenadas das vagas
try:
    detector = ParkingDetector(
        model_path="models/best.pt",
        slots_file="parking_slots.json"
    )
    print("✅ ParkingDetector inicializado com sucesso!")
except Exception as e:
    print(f"⚠️ Erro ao inicializar detector: {e}")
    detector = None

class ParkingRoutes:
    
    @staticmethod
    @parking_bp.route('/', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'Sistema ParkIn Online',
            'timestamp': datetime.now().isoformat(),
            'model_loaded': True,
            'version': '2.0.0'
        })

    @staticmethod
    @parking_bp.route('/upload-video', methods=['POST'])
    def upload_file():
        """
        Endpoint para upload de IMAGEM
        Detecta carros e calcula ocupação das vagas
        """
        try:
            # Verificar se detector foi inicializado
            if detector is None:
                return jsonify({
                    'error': 'Detector não inicializado. Verifique se parking_slots.json existe.'
                }), 500
            
            # Verificar se arquivo foi enviado
            file = None
            file_key = None
            
            for key in ['video', 'image', 'file']:
                if key in request.files:
                    file = request.files[key]
                    file_key = key
                    break
            
            if file is None:
                return jsonify({
                    'error': 'Nenhum arquivo enviado. Use "video", "image" ou "file" como chave'
                }), 400
            
            if file.filename == '':
                return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
            
            # Validar tipo de arquivo (apenas IMAGENS por enquanto)
            filename_lower = file.filename.lower()
            is_image = filename_lower.endswith(tuple(Config.ALLOWED_IMAGE_EXTENSIONS))
            
            if not is_image:
                return jsonify({
                    'error': 'Por enquanto apenas imagens são aceitas (.jpg, .jpeg, .png, .bmp)'
                }), 400
            
            # Salvar arquivo
            ext = filename_lower.split('.')[-1]
            filename = f"parking_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            print(f"\n📤 Imagem recebida: {filename}")
            
            # Processar imagem com novo detector
            results = detector.detect_cars_in_image(
                file_path, 
                save_result=True,  # Salvar imagem com detecções
                output_path=os.path.join(Config.RESULTS_FOLDER, f"detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            )
            
            # Salvar resultados em JSON
            results_filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            results_path = os.path.join(Config.RESULTS_FOLDER, results_filename)
            
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"✅ Resultados salvos em: {results_filename}")
            
            # Retornar resposta
            return jsonify({
                'success': True,
                'message': 'Imagem processada com sucesso',
                'file_type': 'image',
                'uploaded_file': filename,
                'results_file': results_filename,
                'analysis': {
                    'total_slots': results['total_slots'],
                    'occupied': results['occupied'],
                    'empty': results['empty'],
                    'occupancy_rate': results['occupancy_rate'],
                    'cars_detected': results['cars_detected'],
                    'timestamp': results['timestamp'],
                    'slots': results['slots']  # Detalhes de cada vaga
                }
            }), 200
            
        except FileNotFoundError as e:
            return jsonify({
                'error': f'Arquivo não encontrado: {str(e)}'
            }), 404
        except Exception as e:
            return jsonify({
                'error': f'Erro ao processar imagem: {str(e)}'
            }), 500

    @staticmethod
    @parking_bp.route('/parking-status', methods=['GET'])
    def get_parking_status():
        try:
            results_files = [f for f in os.listdir(Config.RESULTS_FOLDER) if f.endswith('.json')]
            
            if not results_files:
                return jsonify({
                    'error': 'Nenhuma análise disponível. Faça upload de um arquivo primeiro.'
                }), 404
            
            # Pegar o arquivo mais recente
            latest_file = max(results_files, key=lambda x: os.path.getctime(os.path.join(Config.RESULTS_FOLDER, x)))
            
            with open(os.path.join(Config.RESULTS_FOLDER, latest_file), 'r') as f:
                latest_results = json.load(f)
            
            return jsonify({
                'success': True,
                'data': latest_results,
                'last_updated': latest_results.get('timestamp'),
                'source_file': latest_file
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro ao buscar status: {str(e)}'}), 500

    @staticmethod
    @parking_bp.route('/parking-spots', methods=['GET'])
    def get_parking_spots():
        try:
            results_files = [f for f in os.listdir(Config.RESULTS_FOLDER) if f.endswith('.json')]
            
            if not results_files:
                return jsonify({
                    'total_spots': 0,
                    'occupied_spots': 0,
                    'free_spots': 0,
                    'occupancy_rate': 0,
                    'message': 'Nenhuma análise disponível'
                })
            
            latest_file = max(results_files, key=lambda x: os.path.getctime(os.path.join(Config.RESULTS_FOLDER, x)))
            
            with open(os.path.join(Config.RESULTS_FOLDER, latest_file), 'r') as f:
                results = json.load(f)
            
            parking_data = results.get('parking_analysis', results.get('image_analysis', {}))
            
            return jsonify({
                'total_spots': parking_data.get('total_spots', 0),
                'occupied_spots': parking_data.get('occupied_spots', 0),
                'free_spots': parking_data.get('free_spots', 0),
                'occupancy_rate': parking_data.get('occupancy_rate', 0),
                'last_updated': results.get('timestamp'),
                'file_type': results.get('file_type', 'unknown'),
                'detection_summary': results.get('detection_summary', {}),
                'status': 'success'
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro ao buscar vagas: {str(e)}'}), 500

    @staticmethod
    @parking_bp.route('/debug-last-detection', methods=['GET'])
    def debug_last_detection():
        """
        Endpoint de debug para ver detecções completas
        """
        try:
            results_files = [f for f in os.listdir(Config.RESULTS_FOLDER) if f.endswith('.json')]
            
            if not results_files:
                return jsonify({'error': 'Nenhuma análise disponível'}), 404
            
            latest_file = max(results_files, key=lambda x: os.path.getctime(os.path.join(Config.RESULTS_FOLDER, x)))
            
            with open(os.path.join(Config.RESULTS_FOLDER, latest_file), 'r') as f:
                results = json.load(f)
            
            return jsonify({
                'success': True,
                'file': latest_file,
                'full_results': results,
                'summary': {
                    'file_type': results.get('file_type'),
                    'timestamp': results.get('timestamp'),
                    'total_detections': len(results.get('car_detections', [])),
                    'parking_analysis': results.get('parking_analysis', results.get('image_analysis', {}))
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro no debug: {str(e)}'}), 500

    @staticmethod
    @parking_bp.route('/latest-image', methods=['GET'])
    def get_latest_image():
        """
        Endpoint para servir a última imagem enviada
        """
        try:
            
            # Obter caminho absoluto da pasta uploads
            upload_path = os.path.abspath(Config.UPLOAD_FOLDER)
            
            # Buscar todos os arquivos de imagem no diretório uploads
            image_patterns = [
                os.path.join(upload_path, '*.jpg'),
                os.path.join(upload_path, '*.jpeg'),
                os.path.join(upload_path, '*.png'),
                os.path.join(upload_path, '*.bmp')
            ]
            
            all_images = []
            for pattern in image_patterns:
                all_images.extend(glob.glob(pattern))
            
            if not all_images:
                return jsonify({
                    'error': 'Nenhuma imagem encontrada',
                    'upload_path': upload_path,
                    'searched_patterns': image_patterns
                }), 404
            
            # Pegar a imagem mais recente
            latest_image = max(all_images, key=os.path.getctime)
            
            # Verificar se o arquivo existe
            if not os.path.exists(latest_image):
                return jsonify({'error': f'Arquivo não encontrado: {latest_image}'}), 404
            
            return send_file(latest_image, as_attachment=False)
            
        except Exception as e:
            return jsonify({
                'error': f'Erro ao buscar imagem: {str(e)}',
                'upload_folder': Config.UPLOAD_FOLDER,
                'current_dir': os.getcwd()
            }), 500

    @staticmethod
    @parking_bp.route('/latest-image-info', methods=['GET'])
    def get_latest_image_info():
        """
        Endpoint para obter informações sobre a última imagem (sem servir o arquivo)
        """
        try:
            
            # Obter caminho absoluto da pasta uploads
            upload_path = os.path.abspath(Config.UPLOAD_FOLDER)
            
            # Buscar todos os arquivos de imagem no diretório uploads
            image_patterns = [
                os.path.join(upload_path, '*.jpg'),
                os.path.join(upload_path, '*.jpeg'),
                os.path.join(upload_path, '*.png'),
                os.path.join(upload_path, '*.bmp')
            ]
            
            all_images = []
            for pattern in image_patterns:
                all_images.extend(glob.glob(pattern))
            
            if not all_images:
                return jsonify({'error': 'Nenhuma imagem encontrada'}), 404
            
            # Pegar a imagem mais recente
            latest_image = max(all_images, key=os.path.getctime)
            filename = os.path.basename(latest_image)
            file_size = os.path.getsize(latest_image)
            modified_time = os.path.getctime(latest_image)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'file_size': file_size,
                'modified_time': datetime.fromtimestamp(modified_time).isoformat(),
                'image_url': '/latest-image',
                'full_path': latest_image
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro ao buscar informações da imagem: {str(e)}'}), 500

    @staticmethod
    @parking_bp.route('/test-detection', methods=['POST'])
    def test_detection():
        """
        Endpoint para testar detecção bruta do YOLO (com logs detalhados)
        """
        try:
            file = None
            for key in ['image', 'file']:
                if key in request.files:
                    file = request.files[key]
                    break
            
            if file is None:
                return jsonify({'error': 'Nenhum arquivo enviado'}), 400
                
            if file.filename == '':
                return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
            
            # Verificar se é imagem
            filename_lower = file.filename.lower()
            if not filename_lower.endswith(tuple(Config.ALLOWED_IMAGE_EXTENSIONS)):
                return jsonify({'error': 'Apenas imagens são aceitas para teste'}), 400
            
            # Salvar arquivo temporário
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                file.save(tmp_file.name)
                
                print(f"\nTESTE DE DETECÇÃO INICIADO")
                print(f"Arquivo: {file.filename}")
                print(f"Temp: {tmp_file.name}")
                
                # Testar detecção
                results = detector.detect_cars_in_image(tmp_file.name)
                
                # Remover arquivo temporário
                os.unlink(tmp_file.name)
                
                return jsonify({
                    'success': True,
                    'message': 'Teste de detecção realizado (veja logs no terminal)',
                    'filename': file.filename,
                    'results': results
                })
                
        except Exception as e:
            print(f"ERRO no teste: {str(e)}")
            return jsonify({'error': f'Erro no teste de detecção: {str(e)}'}), 500


def register_routes(app):
    app.register_blueprint(parking_bp)
