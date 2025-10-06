from ultralytics import YOLO
import cv2
import os

MODEL_PATH = 'yolov8s.pt'

#  Após treinar, comente a linha acima e descomente a linha abaixo.
# MODEL_PATH = 'runs/detect/parking_detector/weights/best.pt'

# precisa colocar uma imagem de teste
IMAGE_PATH = '../uploads/parking_image_test.jpg'

script_dir = os.path.dirname(__file__)
model_path_abs = os.path.join(script_dir, MODEL_PATH) if not os.path.isabs(MODEL_PATH) else MODEL_PATH
image_path_abs = os.path.join(script_dir, IMAGE_PATH)

if not os.path.exists(model_path_abs):
    print(f"ERRO: Modelo não encontrado em '{model_path_abs}'")
    print("Verifique se o nome está correto ou se o treinamento foi concluído.")
elif not os.path.exists(image_path_abs):
    print(f"ERRO: Imagem de teste não encontrada em '{image_path_abs}'")
    print("Por favor, coloque uma imagem de teste na pasta 'uploads'.")
else:
    try:
        model = YOLO(model_path_abs)
        print(f"A analisar a imagem: {image_path_abs}...")
        results = model(image_path_abs)
        annotated_frame = results[0].plot()

        cv2.imshow("YOLOv8 Detecção", annotated_frame)
        print("-> Deteção concluída. Uma janela com a imagem deve aparecer.")
        print("-> Pressione qualquer tecla na janela da imagem para fechar.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
