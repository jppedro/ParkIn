
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
        from routes.parking_routes import register_routes
        register_routes(self.app)
        
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
        print("=" * 60)
        print(f"Servidor iniciando em {host}:{port}...")
        print("Endpoints disponíveis:")
        print("   GET  /                     - Status do sistema")
        print("   POST /upload-video         - Upload e análise (vídeo/imagem)")
        print("   GET  /parking-status       - Status completo das vagas")
        print("   GET  /parking-spots        - Informações das vagas (para frontend)")
        print("   GET  /debug-last-detection - Debug da última detecção")
        print("   POST /test-detection       - Teste de detecção com logs detalhados")
        print("=" * 60)
        
    def get_app(self):
        return self.app
