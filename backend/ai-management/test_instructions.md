# Sistema ParkIn - Guia de Uso

## Endpoints Disponíveis

### 1. **GET /** - Verificar se o sistema está funcionando
```bash
curl http://localhost:5001/
```
**Resposta esperada:**
```json
{
  "status": "Sistema ParkIn Online",
  "timestamp": "2024-01-15T10:30:00.123456",
  "model_loaded": true
}
```

---

### 2. **POST /upload-video** - Upload e análise de vídeo MP4
```bash
curl -X POST \
  -F "video=@seu_video.mp4" \
  http://localhost:5001/upload-video
```

**O que acontece:**
1. Upload do vídeo MP4
2. YOLOv8 detecta carros frame por frame
3. Calcula estatísticas de ocupação
4. Salva resultados em JSON
5. Retorna análise completa

**Resposta esperada:**
```json
{
  "success": true,
  "message": "Vídeo processado com sucesso",
  "video_file": "parking_video_20240115_103000.mp4",
  "results_file": "results_20240115_103000.json",
  "analysis": {
    "timestamp": "2024-01-15T10:30:00.123456",
    "total_frames_analyzed": 10,
    "parking_analysis": {
      "total_spots": 25,
      "occupied_spots": 18,
      "free_spots": 7,
      "occupancy_rate": 72.0
    },
    "car_detections": [...],
    "average_cars_per_frame": 18.5
  }
}
```

---

### 3. **GET /parking-spots** - Informações para o frontend
```bash
curl http://localhost:5001/parking-spots
```

**Resposta esperada:**
```json
{
  "total_spots": 25,
  "occupied_spots": 18,
  "free_spots": 7,
  "occupancy_rate": 72.0,
  "last_updated": "2024-01-15T10:30:00.123456",
  "status": "success"
}
```

---

### 4. **GET /parking-status** - Status completo
```bash
curl http://localhost:5001/parking-status
```

**Retorna:** Análise completa mais recente

---

## Como Funciona a Detecção

### **Processo de Análise:**

1. **Upload do Vídeo** → Sistema salva em `uploads/`
2. **Processamento** → YOLOv8 analisa frames
3. **Detecção** → Identifica carros (classe 2 do COCO)
4. **Cálculo** → Estima vagas baseado na quantidade de carros
5. **Resultados** → Salva em `results/` como JSON
6. **API** → Disponibiliza dados para frontend

### **Estrutura de Pastas:**
```
backend/ai-management/
├── parking-management.py    # Servidor principal
├── requirements.txt         # Dependências
├── venv/                   # Ambiente virtual
├── uploads/                # Vídeos enviados
├── results/                # Análises em JSON
└── yolov8n.pt             # Modelo baixado automaticamente
```

### **Exemplo de Detecção:**
```json
{
  "bbox": [100.5, 200.3, 150.7, 250.9],  // [x1, y1, x2, y2]
  "confidence": 0.85,                      // 85% de confiança
  "frame": 30                              // Frame número 30
}
```

---

## 🧪 Teste Rápido

Para testar com um vídeo de exemplo:

```bash
# 1. Verificar se o servidor está rodando
curl http://localhost:5001/

# 2. Fazer upload de um vídeo (substitua pelo seu arquivo)
curl -X POST -F "video=@/caminho/para/seu/video.mp4" http://localhost:5001/upload-video

# 3. Ver resultados
curl http://localhost:5001/parking-spots
```

---

## Integração com Frontend React

No seu frontend React, você pode fazer:

```javascript
// Verificar status das vagas
fetch('http://localhost:5001/parking-spots')
  .then(response => response.json())
  .then(data => {
    console.log('Vagas livres:', data.free_spots);
    console.log('Taxa de ocupação:', data.occupancy_rate + '%');
  });

// Upload de vídeo
const formData = new FormData();
formData.append('video', videoFile);

fetch('http://localhost:5001/upload-video', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log('Análise:', data.analysis));
```
