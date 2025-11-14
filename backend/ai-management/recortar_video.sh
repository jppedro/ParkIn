#!/bin/bash

# Script para recortar trechos de vídeo
# Uso: ./recortar_video.sh input.mp4 inicio duracao output.mp4
# Exemplo: ./recortar_video.sh video.mp4 00:00:30 00:01:00 trecho.mp4

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🎬 Recortar Trecho de Vídeo${NC}"
echo "=================================="
echo ""

# Verificar se ffmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}❌ ffmpeg não está instalado${NC}"
    echo ""
    echo "Para instalar no macOS:"
    echo "  brew install ffmpeg"
    echo ""
    echo "Para instalar no Ubuntu/Debian:"
    echo "  sudo apt-get install ffmpeg"
    exit 1
fi

# Função para uso
show_usage() {
    echo "Uso:"
    echo "  $0 <video_entrada> <inicio> <duracao> <video_saida>"
    echo ""
    echo "Parâmetros:"
    echo "  video_entrada : Arquivo de vídeo de entrada (.mp4, .avi, .mov, .mkv)"
    echo "  inicio        : Tempo de início (formato: HH:MM:SS ou MM:SS ou SS)"
    echo "  duracao       : Duração do trecho (formato: HH:MM:SS ou MM:SS ou SS)"
    echo "  video_saida   : Arquivo de vídeo de saída"
    echo ""
    echo "Exemplos:"
    echo "  $0 video.mp4 00:00:30 00:01:00 trecho.mp4    # Do 30s até 1min30s"
    echo "  $0 video.mp4 30 60 trecho.mp4                # Do 30s por 60s (1min)"
    echo "  $0 video.mp4 0 60 primeiro_minuto.mp4        # Primeiro minuto"
    echo ""
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}📋 Modo Interativo${NC}"
    echo ""
    
    # Pedir arquivo de entrada
    echo "Digite o caminho do vídeo de entrada:"
    read -r INPUT_VIDEO
    
    if [ ! -f "$INPUT_VIDEO" ]; then
        echo -e "${RED}❌ Arquivo não encontrado: ${INPUT_VIDEO}${NC}"
        exit 1
    fi
    
    # Mostrar informações do vídeo
    echo ""
    echo -e "${GREEN}📹 Informações do vídeo:${NC}"
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_VIDEO" | \
        awk '{printf "   Duração: %.0f segundos (%.0f minutos)\n", $1, $1/60}'
    
    echo ""
    echo "Digite o tempo de início (em segundos ou HH:MM:SS):"
    echo "  Exemplos: 0, 30, 01:30, 00:01:30"
    read -r START_TIME
    
    echo ""
    echo "Digite a duração do trecho (em segundos ou HH:MM:SS):"
    echo "  Exemplos: 60 (1 minuto), 120 (2 minutos), 00:01:00"
    read -r DURATION
    
    echo ""
    echo "Digite o nome do arquivo de saída:"
    echo "  Exemplo: trecho.mp4"
    read -r OUTPUT_VIDEO
    
elif [ $# -ne 4 ]; then
    show_usage
    exit 1
else
    INPUT_VIDEO=$1
    START_TIME=$2
    DURATION=$3
    OUTPUT_VIDEO=$4
    
    if [ ! -f "$INPUT_VIDEO" ]; then
        echo -e "${RED}❌ Arquivo não encontrado: ${INPUT_VIDEO}${NC}"
        exit 1
    fi
fi

# Recortar vídeo
echo ""
echo -e "${GREEN}✂️  Recortando vídeo...${NC}"
echo "   Entrada: ${INPUT_VIDEO}"
echo "   Início: ${START_TIME}"
echo "   Duração: ${DURATION}"
echo "   Saída: ${OUTPUT_VIDEO}"
echo ""

ffmpeg -i "$INPUT_VIDEO" -ss "$START_TIME" -t "$DURATION" -c copy "$OUTPUT_VIDEO" -y

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Vídeo recortado com sucesso!${NC}"
    echo "   Arquivo salvo: ${OUTPUT_VIDEO}"
    
    # Mostrar tamanho do arquivo
    FILE_SIZE=$(ls -lh "$OUTPUT_VIDEO" | awk '{print $5}')
    echo "   Tamanho: ${FILE_SIZE}"
    
    echo ""
    echo -e "${YELLOW}💡 Próximo passo:${NC}"
    echo "   Processar vídeo na API:"
    echo "   curl -X POST http://localhost:5001/api/parking/detect-video \\"
    echo "     -F \"parking_id=<seu_parking_id>\" \\"
    echo "     -F \"video=@${OUTPUT_VIDEO}\""
else
    echo ""
    echo -e "${RED}❌ Erro ao recortar vídeo${NC}"
    exit 1
fi
