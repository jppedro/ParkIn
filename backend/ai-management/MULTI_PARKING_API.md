# Multi-Parking API - Guia de Uso

Sistema ParkIn com suporte a **múltiplas áreas de estacionamento** para monitoramento simultâneo no dashboard admin.

---

## 🏗️ Arquitetura

Cada área de estacionamento possui:
- **parking_id**: UUID único
- **reference_image**: Imagem de referência do fragmento
- **parking_slots.json**: Coordenadas das vagas
- **metadata.json**: Informações gerais
- **results/**: Histórico de detecções

```
parking_data/
├── parking_index.json
├── <parking_id_1>/
│   ├── metadata.json
│   ├── reference.jpg
│   ├── parking_slots.json
│   ├── parking_slots_marked.jpg
│   └── results/
│       ├── detection_*.jpg
│       └── history_*.json
├── <parking_id_2>/
│   └── ...
```

---

## 🚀 Workflow Completo

### 📋 Listar Áreas Existentes (Opcional)

```bash
python3 list_parking_areas.py
```

Mostra todas as áreas cadastradas com seus IDs e status.

---

### 1️⃣ Criar Nova Área de Estacionamento

```bash
curl -X POST http://localhost:5001/api/parking/setup \
  -F "name=Fragmento A" \
  -F "description=Zona Norte do Estacionamento" \
  -F "reference_image=@/path/to/image.jpg"
```

**Resposta:**
```json
{
  "success": true,
  "parking_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Fragmento A",
  "message": "Área de estacionamento criada com sucesso",
  "next_step": "Use POST /api/parking/define-slots com parking_id=... para definir as vagas"
}
```

---

### 2️⃣ Definir Vagas Manualmente (Interface Gráfica)

#### **🎨 Via Script CLI (Desenhar Vagas - RECOMENDADO)**

```bash
python3 define_slots_for_parking.py 550e8400-e29b-41d4-a716-446655440000
```

**Instruções:**
- ✅ Abre a imagem de referência em uma janela
- ✅ Clique em 4 pontos (sentido horário) para cada vaga
- ✅ Visualize as vagas em tempo real
- ✅ Pressione `r` para resetar vaga atual
- ✅ Pressione `u` para desfazer última vaga
- ✅ Pressione `s` para salvar e sair
- ✅ Pressione `q` para sair sem salvar

**O que acontece ao salvar:**
1. Coordenadas salvas em `parking_data/{parking_id}/parking_slots.json`
2. Imagem marcada salva em `parking_data/{parking_id}/parking_slots_marked.jpg`
3. Cópia da imagem marcada em `uploads/parking_slots_{parking_id}.jpg`
4. Metadados atualizados automaticamente

---

#### **⚙️ Via API (Apenas para integração programática)**

⚠️ **Atenção:** Esta opção requer que você já tenha as coordenadas calculadas. Para uso normal, use o script CLI acima.

```bash
curl -X POST http://localhost:5001/api/parking/define-slots \
  -H "Content-Type: application/json" \
  -d '{
    "parking_id": "550e8400-e29b-41d4-a716-446655440000",
    "slots": [
      {
        "id": 1,
        "coordinates": [[100, 100], [200, 100], [200, 200], [100, 200]]
      },
      {
        "id": 2,
        "coordinates": [[220, 100], [320, 100], [320, 200], [220, 200]]
      }
    ]
  }'
```

**Resposta:**
```json
{
  "success": true,
  "parking_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_slots": 2,
  "message": "2 vagas definidas com sucesso",
  "marked_image": "uploads/parking_slots_550e8400-e29b-41d4-a716-446655440000_20241019_103000.jpg",
  "next_step": "Use POST /api/parking/detect com parking_id=... para detectar ocupação"
}
```

---

### 3️⃣ Detectar Ocupação

```bash
curl -X POST http://localhost:5001/api/parking/detect \
  -F "parking_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "image=@/path/to/current_image.jpg"
```

**Resposta:**
```json
{
  "success": true,
  "parking_id": "550e8400-e29b-41d4-a716-446655440000",
  "parking_name": "Fragmento A",
  "total_slots": 10,
  "occupied": 7,
  "empty": 3,
  "occupancy_rate": 0.7,
  "cars_detected": 7,
  "slots": [
    {
      "id": 1,
      "status": "occupied",
      "confidence": 0.85
    },
    {
      "id": 2,
      "status": "empty"
    }
  ],
  "timestamp": "2024-01-15T10:30:00",
  "annotated_image": "/path/to/annotated.jpg"
}
```

---

### 4️⃣ Listar Todas as Áreas

```bash
curl http://localhost:5001/api/parking/list
```

**Resposta:**
```json
{
  "success": true,
  "total": 3,
  "parkings": [
    {
      "parking_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Fragmento A",
      "description": "Zona Norte",
      "created_at": "2024-01-15T10:00:00",
      "slots_defined": true,
      "total_slots": 10
    },
    {
      "parking_id": "660f9511-f30c-52e5-b827-557766551111",
      "name": "Fragmento B",
      "description": "Zona Sul",
      "created_at": "2024-01-15T11:00:00",
      "slots_defined": true,
      "total_slots": 15
    }
  ]
}
```

---

### 5️⃣ Consultar Status de Uma Área

```bash
curl "http://localhost:5001/api/parking/status?parking_id=550e8400-e29b-41d4-a716-446655440000"
```

**Resposta:**
```json
{
  "success": true,
  "parking_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Fragmento A",
  "description": "Zona Norte",
  "total_slots": 10,
  "slots_defined": true,
  "created_at": "2024-01-15T10:00:00",
  "last_detection": {
    "timestamp": "2024-01-15T14:30:00",
    "occupied": 7,
    "empty": 3,
    "occupancy_rate": 0.7
  }
}
```

---

### 6️⃣ Obter Imagem de Referência

```bash
curl http://localhost:5001/api/parking/image/550e8400-e29b-41d4-a716-446655440000 \
  --output reference_image.jpg
```

---

### 7️⃣ Remover Área

```bash
curl -X DELETE http://localhost:5001/api/parking/delete \
  -H "Content-Type: application/json" \
  -d '{"parking_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Resposta:**
```json
{
  "success": true,
  "message": "Área 550e8400-e29b-41d4-a716-446655440000 removida com sucesso"
}
```

---

## 📊 Dashboard Admin - Exemplo de Integração

### Cenário: Monitorar 3 Fragmentos Simultaneamente

```javascript
// 1. Listar todas as áreas
const response = await fetch('http://localhost:5001/api/parking/list');
const { parkings } = await response.json();

// 2. Para cada área, obter status atual
for (const parking of parkings) {
  const statusResponse = await fetch(
    `http://localhost:5001/api/parking/status?parking_id=${parking.parking_id}`
  );
  const status = await statusResponse.json();
  
  console.log(`${status.name}: ${status.last_detection?.occupied}/${status.total_slots} vagas ocupadas`);
}

// 3. Detectar ocupação em tempo real (enviar imagem do drone/câmera)
const formData = new FormData();
formData.append('parking_id', '550e8400-e29b-41d4-a716-446655440000');
formData.append('image', imageFile);

const detectResponse = await fetch('http://localhost:5001/api/parking/detect', {
  method: 'POST',
  body: formData
});

const results = await detectResponse.json();
console.log(`Taxa de ocupação: ${results.occupancy_rate * 100}%`);
```

---

## 🎥 Processamento de Vídeo (Futuro)

Para processar vídeos frame-by-frame:

```bash
curl -X POST http://localhost:5001/api/parking/detect-video \
  -F "parking_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "video=@/path/to/video.mp4" \
  -F "frame_interval=10"  # Analisar a cada 10 segundos
```

---

## 🔧 Comandos Úteis

### Verificar status do sistema
```bash
curl http://localhost:5001/
```

### Listar arquivos de uma área
```bash
ls -la parking_data/550e8400-e29b-41d4-a716-446655440000/
```

### Ver último resultado
```bash
cat parking_data/550e8400-e29b-41d4-a716-446655440000/results/history_*.json | tail -n 50
```

---

## 📝 Notas Importantes

1. **IDs persistentes**: Os `parking_id` são UUIDs permanentes
2. **Imagens de referência**: Recomendado usar imagens de alta resolução
3. **Coordenadas**: Definidas em pixels absolutos da imagem de referência
4. **Detecção**: Usa modelo YOLO para detectar carros + cálculo de sobreposição (30%)
5. **Histórico**: Todas as detecções são salvas em `results/history_*.json`

---

## 🚨 Troubleshooting

### Erro: "Área não encontrada"
```bash
# Verificar áreas existentes
curl http://localhost:5001/api/parking/list
```

### Erro: "Vagas não definidas"
```bash
# Definir vagas via CLI
python3 define_slots_for_parking.py <parking_id>
```

### Erro: "Imagem de referência não encontrada"
```bash
# Recriar área com nova imagem
curl -X POST http://localhost:5001/api/parking/setup \
  -F "name=Nova Área" \
  -F "reference_image=@image.jpg"
```

---

## 📚 Estrutura de Dados

### parking_index.json
```json
{
  "parkings": [
    {
      "parking_id": "uuid",
      "name": "Fragmento A",
      "created_at": "2024-01-15T10:00:00"
    }
  ]
}
```

### metadata.json
```json
{
  "parking_id": "uuid",
  "name": "Fragmento A",
  "description": "Zona Norte",
  "created_at": "2024-01-15T10:00:00",
  "reference_image": "/path/to/reference.jpg",
  "slots_defined": true,
  "total_slots": 10,
  "slots_file": "/path/to/parking_slots.json"
}
```

### parking_slots.json
```json
{
  "parking_id": "uuid",
  "total_slots": 10,
  "defined_at": "2024-01-15T10:30:00",
  "slots": [
    {
      "id": 1,
      "coordinates": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    }
  ]
}
```

---

## ✅ Status da Implementação

1. ✅ API Multi-Parking implementada
2. ✅ Script CLI para definir vagas (`define_slots_for_parking.py`)
3. ✅ Script CLI para listar áreas (`list_parking_areas.py`)
4. ✅ Endpoints legacy removidos - apenas Multi-Parking API
5. ✅ Caminhos absolutos (sem problemas de `cwd`)
6. ✅ Collection do Postman atualizada
7. ⏳ Integração com dashboard frontend
8. ⏳ Processamento de vídeo frame-by-frame
9. ⏳ WebSocket para updates em tempo real
10. ⏳ Sistema de autenticação/permissões
