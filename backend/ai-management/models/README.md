# 📦 Pasta de Modelos YOLO Treinados

Esta pasta contém os modelos YOLO treinados para o sistema ParkIn.

## 📋 Modelos Disponíveis

### **parkin_aerial_best.pt** (Modelo Principal)
- **Tipo**: YOLOv8 Medium (yolov8m)
- **Dataset**: Imagens aéreas de estacionamento
- **Classes**: 
  - `enpty` (ID: 0): Vaga vazia
  - `not_enpty` (ID: 1): Vaga ocupada
- **Uso**: Detecção de vagas em imagens de drone/aéreas
- **Treinado em**: Google Colab com GPU T4
- **Epochs**: 100 (com early stopping)
- **Otimizador**: AdamW
- **Learning Rate**: 0.001 → 0.01

## 📥 Como Adicionar um Modelo

1. **Treine o modelo** (no Colab ou localmente)
2. **Baixe o best.pt** do treinamento
3. **Renomeie** para um nome descritivo (ex: `parkin_aerial_v2.pt`)
4. **Copie** para esta pasta:
   ```bash
   cp /caminho/para/best.pt models/parkin_aerial_best.pt
   ```
5. **Atualize** o `config.py`:
   ```python
   YOLO_MODEL_PATH = 'models/parkin_aerial_best.pt'
   ```

## 🧪 Como Testar um Modelo

```bash
# Teste básico de carregamento
python3 -c "from ultralytics import YOLO; model = YOLO('models/parkin_aerial_best.pt'); print(model.names)"

# Teste com imagem
python3 yolo/test_aerial_model.py models/parkin_aerial_best.pt uploads/test_image.jpg

# Teste na API
curl -X POST http://localhost:5001/detect -F "file=@uploads/test_image.jpg"
```

## 📊 Versionamento de Modelos

Recomendamos versionar seus modelos:

```
models/
├── parkin_aerial_v1_20251015.pt   # Primeira versão
├── parkin_aerial_v2_20251020.pt   # Versão melhorada
├── parkin_aerial_best.pt          # Link para melhor versão (atual)
└── README.md
```

```bash
# Criar nova versão
cp models/parkin_aerial_best.pt models/parkin_aerial_v1_20251015.pt

# Atualizar para nova versão
cp novo_best.pt models/parkin_aerial_best.pt
```

## 📈 Métricas dos Modelos

| Modelo | mAP50 | mAP50-95 | Precision | Recall | Tamanho |
|--------|-------|----------|-----------|--------|---------|
| v1     | TBD   | TBD      | TBD       | TBD    | ~50MB   |

*Atualize esta tabela com as métricas de cada versão*

## 🔧 Conversão de Formatos

### Exportar para ONNX (inferência mais rápida):
```python
from ultralytics import YOLO
model = YOLO('models/parkin_aerial_best.pt')
model.export(format='onnx')
```

### Exportar para TensorFlow:
```python
model.export(format='saved_model')
```

## ⚠️ Importante

- **Não commite modelos grandes** no Git (use Git LFS ou armazene externamente)
- **Sempre teste** um modelo antes de usar em produção
- **Documente** as mudanças entre versões
- **Faça backup** dos modelos importantes no Google Drive

## 📝 Template de Documentação

Ao adicionar um novo modelo, crie um arquivo `parkin_aerial_vX_info.txt`:

```
Modelo: parkin_aerial_v1.pt
Data: 2025-10-15
Treinado por: João Rodrigues

Dataset:
- Source: Roboflow parking-aerial
- Train images: 1500
- Val images: 300
- Classes: enpty, not_enpty

Training:
- Model: yolov8m.pt
- Epochs: 100
- Batch: 16
- Optimizer: AdamW
- LR: 0.001

Metrics:
- mAP50: 0.85
- mAP50-95: 0.72
- Precision: 0.88
- Recall: 0.82

Notes:
- Funciona bem em condições de boa iluminação
- Pode ter dificuldade com sombras fortes
- Otimizado para visão aérea entre 10-50m de altura
```

---

**💡 Dica**: Use o script `yolo/train_aerial_yolo.py` para treinar novos modelos!
