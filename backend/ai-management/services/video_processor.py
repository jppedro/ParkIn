"""
VideoProcessor - Processa vídeos de drone e atualiza parking_slots.json periodicamente
"""

import cv2
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path


class VideoProcessor:
    
    def __init__(self, frame_interval_seconds: int = 10):
        """
        Inicializa o processador de vídeo
        
        Args:
            frame_interval_seconds: Intervalo em segundos entre cada análise de frame
        """
        self.frame_interval_seconds = frame_interval_seconds
        
    def process_video(
        self,
        video_path: str,
        parking_id: str,
        parking_name: str,
        detector,
        parking_folder: str,
        reference_dimensions: Optional[tuple] = None,
        on_frame_processed: Optional[Callable] = None
    ) -> Dict:
        """
        Processa vídeo frame-by-frame e atualiza history.json periodicamente
        
        Args:
            video_path: Caminho do vídeo
            parking_id: ID da área de estacionamento
            parking_name: Nome da área de estacionamento
            detector: Instância do ParkingDetector
            parking_folder: Pasta da área de estacionamento
            on_frame_processed: Callback opcional chamado após cada frame processado
        
        Returns:
            Dict com resumo do processamento
        """
        print(f"\n🎥 Iniciando processamento de vídeo: {video_path}")
        print(f"   Intervalo de análise: {self.frame_interval_seconds} segundos")
        
        # Abrir vídeo
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")
        
        # Obter informações do vídeo
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps if fps > 0 else 0
        
        print(f"   FPS: {fps:.2f}")
        print(f"   Total de frames: {total_frames}")
        print(f"   Duração: {duration_seconds:.2f} segundos")
        
        # Calcular intervalo de frames
        frame_interval = int(fps * self.frame_interval_seconds)
        
        if frame_interval == 0:
            frame_interval = 1
        
        print(f"   Analisando 1 frame a cada {frame_interval} frames")
        
        # Criar pasta para frames extraídos
        frames_folder = os.path.join(parking_folder, "video_frames")
        os.makedirs(frames_folder, exist_ok=True)
        
        # Criar pasta para resultados
        results_folder = os.path.join(parking_folder, "results")
        os.makedirs(results_folder, exist_ok=True)
        
        # Processar frames
        frame_count = 0
        processed_count = 0
        detections_history = []
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Processar apenas frames no intervalo especificado
            if frame_count % frame_interval == 0:
                current_time_seconds = frame_count / fps if fps > 0 else 0
                
                print(f"\n⏱️  Processando frame {frame_count} (tempo: {current_time_seconds:.1f}s)")
                
                # Salvar frame temporariamente
                frame_filename = f"frame_{processed_count:04d}_t{int(current_time_seconds)}s.jpg"
                frame_path = os.path.join(frames_folder, frame_filename)
                cv2.imwrite(frame_path, frame)
                
                # Detectar ocupação neste frame
                try:
                    output_image = os.path.join(
                        results_folder,
                        f"detection_video_frame{processed_count:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    )
                    
                    print(f"   🔍 Detectando com {detector.total_slots} vagas pré-definidas...")
                    
                    results = detector.detect_cars_in_image(
                        frame_path,
                        save_result=True,
                        output_path=output_image,
                        reference_dimensions=reference_dimensions
                    )
                    
                    # Adicionar informações extras
                    results['frame_number'] = frame_count
                    results['time_seconds'] = current_time_seconds
                    results['frame_path'] = frame_path
                    
                    # Atualizar history.json (arquivo único)
                    self._update_history_json(
                        parking_folder=parking_folder,
                        parking_id=parking_id,
                        parking_name=parking_name,
                        detection_results=results,
                        frame_number=frame_count,
                        time_seconds=current_time_seconds
                    )
                    
                    detections_history.append({
                        'frame_number': frame_count,
                        'time_seconds': current_time_seconds,
                        'occupied': results['occupied'],
                        'empty': results['empty'],
                        'occupancy_rate': results['occupancy_rate']
                    })
                    
                    print(f"   ✅ Detecção concluída: {results['occupied']}/{results['total_slots']} ocupadas")
                    
                    # Callback opcional
                    if on_frame_processed:
                        on_frame_processed(results)
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar frame {frame_count}: {e}")
            
            frame_count += 1
        
        cap.release()
        
        # Resumo final
        summary = {
            'video_path': video_path,
            'parking_id': parking_id,
            'total_frames': total_frames,
            'frames_processed': processed_count,
            'duration_seconds': duration_seconds,
            'fps': fps,
            'frame_interval_seconds': self.frame_interval_seconds,
            'detections_history': detections_history,
            'frames_folder': frames_folder,
            'results_folder': results_folder,
            'processed_at': datetime.now().isoformat()
        }
        
        # Salvar resumo
        summary_file = os.path.join(
            results_folder,
            f"video_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Processamento concluído!")
        print(f"   Total de frames analisados: {processed_count}")
        print(f"   Resumo salvo em: {summary_file}")
        
        return summary
    
    def _update_history_json(
        self,
        parking_folder: str,
        parking_id: str,
        parking_name: str,
        detection_results: Dict,
        frame_number: int,
        time_seconds: float
    ):
        """
        Atualiza o history.json (arquivo único) com o status atual das vagas
        
        Args:
            parking_folder: Pasta da área de estacionamento
            parking_id: ID da área
            parking_name: Nome da área
            detection_results: Resultados da detecção
            frame_number: Número do frame
            time_seconds: Tempo em segundos no vídeo
        """
        results_folder = os.path.join(parking_folder, "results")
        os.makedirs(results_folder, exist_ok=True)
        
        history_file = os.path.join(results_folder, "history.json")
        
        # Criar estrutura do history.json (sempre sobrescreve)
        history_data = {
            "total_slots": detection_results['total_slots'],
            "occupied": detection_results['occupied'],
            "empty": detection_results['empty'],
            "occupancy_rate": detection_results['occupancy_rate'],
            "slots": [
                {
                    "id": slot['id'],
                    "status": slot['status'],
                    "has_car": slot['has_car'],
                    "overlap": slot.get('overlap', 0)
                }
                for slot in detection_results['slots']
            ],
            "cars_detected": detection_results.get('cars_detected', 0),
            "timestamp": datetime.now().isoformat(),
            "output_image": detection_results.get('output_image', ''),
            "parking_id": parking_id,
            "parking_name": parking_name,
            "annotated_image": detection_results.get('output_image', ''),
            "video_processing": {
                "frame_number": frame_number,
                "time_seconds": time_seconds
            }
        }
        
        # Salvar/sobrescrever history.json
        with open(history_file, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        print(f"   📝 history.json atualizado (frame {frame_number}, {time_seconds:.1f}s)")
    
    @staticmethod
    def get_video_info(video_path: str) -> Dict:
        """
        Obtém informações sobre um vídeo sem processá-lo
        
        Args:
            video_path: Caminho do vídeo
        
        Returns:
            Dict com informações do vídeo
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_seconds = total_frames / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration_seconds': duration_seconds,
            'duration_formatted': f"{int(duration_seconds // 60)}:{int(duration_seconds % 60):02d}"
        }
