
from flask import Flask
from flask_cors import CORS
from config import Config


class ParkingAPI:
    
    def __init__(self):
        self.app = Flask(__name__)
        self._setup_cors()
        self._setup_folders()
        self._register_routes()
        
    def _setup_cors(self):
        CORS(self.app)
        
    def _setup_folders(self):
        Config.init_folders()
            
    def _register_routes(self):
        # Health check endpoint
        @self.app.route('/', methods=['GET'])
        def health_check():
            from flask import jsonify
            from datetime import datetime
            return jsonify({
                'status': 'Sistema ParkIn Online',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0.0 - Multi-Parking API'
            })
        
        # Registrar rotas multi-parking
        from routes.multi_parking_routes import multi_parking_bp
        self.app.register_blueprint(multi_parking_bp, url_prefix='/api/parking')
        
    def run(self, host=None, port=None, debug=None):
        if host is None:
            host = Config.HOST
        if port is None:
            port = Config.PORT
        if debug is None:
            debug = Config.DEBUG
            
        self._print_startup_info(host, port)
        self.app.run(host=host, port=port, debug=debug)
        
    def _print_startup_info(self, host, port):
        print("Sistema ParkIn - Gestão Inteligente de Estacionamento")
        print("=" * 80)
        print(f"Servidor iniciando em {host}:{port}...")
        print("\n🏥 HEALTH CHECK:")
        print("   GET    /                          - Status do sistema")
        print("\n🚗 ENDPOINTS MULTI-PARKING API:")
        print("   POST   /api/parking/setup         - Criar nova área de estacionamento")
        print("   POST   /api/parking/define-slots  - Definir vagas de uma área (via JSON)")
        print("   POST   /api/parking/detect        - Detectar ocupação em uma área (imagem)")
        print("   POST   /api/parking/detect-video  - Detectar ocupação em vídeo (atualiza a cada 10s)")
        print("   GET    /api/parking/status        - Status de uma área específica")
        print("   GET    /api/parking/list          - Listar todas as áreas")
        print("   DELETE /api/parking/delete        - Remover uma área")
        print("   GET    /api/parking/image/<id>    - Imagem de referência de uma área")
        print("\n💡 SCRIPTS CLI:")
        print("   python3 define_slots_for_parking.py <parking_id>  - Desenhar vagas manualmente")
        print("=" * 80)
        
    def get_app(self):
        return self.app
