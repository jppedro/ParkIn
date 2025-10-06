from ultralytics import YOLO

model = YOLO('yolov8s.pt')

results = model.train(
    data='data.yaml',
    epochs=50,          # numero de epocas
    imgsz=640,          # tamanho das imagens
    batch=8,
    name='yolo_parking_detector'
)

print("Treinamento concluído!")
