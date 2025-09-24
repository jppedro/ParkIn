# 🚗 Sistema ParkIn - API de Gestão de Estacionamento

## 🚀 Como Executar

### **Comando Único:**
```bash
cd "/Users/joao.rodrigues/Documents/Faculdade/6º Semestre/PI/ParkIn/backend/ai-management" && source venv/bin/activate && python main.py
```

### **Passo a Passo:**
```bash
# 1. Navegar para o diretório
cd "/Users/joao.rodrigues/Documents/Faculdade/6º Semestre/PI/ParkIn/backend/ai-management"

# 2. Ativar ambiente virtual
source venv/bin/activate

# 3. Executar servidor
python main.py
```

## 📡 Servidor

- **URL:** http://localhost:5001
- **Status:** http://localhost:5001/

## 📤 Upload de Arquivo

```bash
# Upload de imagem
curl -X POST -F "image=@sua_imagem.jpg" http://localhost:5001/upload-video

# Upload de vídeo
curl -X POST -F "video=@seu_video.mp4" http://localhost:5001/upload-video
```

## 📊 Consultar Resultados

```bash
# Informações das vagas (para frontend)
curl http://localhost:5001/parking-spots

# Status completo
curl http://localhost:5001/parking-status

# Debug completo
curl http://localhost:5001/debug-last-detection
```

## ✨ Melhorias Implementadas

- **YOLOv8s**: Modelo maior e mais preciso
- **Threshold 0.25**: Detecta mais objetos (era 0.5)
- **Imagem 1280px**: Melhor resolução para detecção
- **Otimizado para drone**: Parâmetros específicos para imagens aéreas
- **Até 100 detecções**: Permite mais carros por imagem

## 🎯 Resultado Esperado

Agora deve detectar corretamente seus 20+ carros na imagem de drone!
