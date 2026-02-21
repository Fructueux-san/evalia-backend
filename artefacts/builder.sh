#!/bin/bash

# --- Configuration ---
EVAL_DIR="evaluator"
IMAGE_PREFIX="evaluator"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}    EVALIA - Build depuis le dossier artefacts         ${NC}"
echo -e "${BLUE}=======================================================${NC}"

build_and_tag() {
    local framework=$1
    local dockerfile=$2
    local tag="${IMAGE_PREFIX}-${framework}:latest"

    echo -e "\n[+] Building ${GREEN}${tag}${NC}..."
    
    # On définit le contexte de build sur le dossier 'evaluator'
    # pour que Docker trouve les scripts evaluate_*.py
    docker build -t "$tag" -f "${EVAL_DIR}/${dockerfile}" "${EVAL_DIR}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}--> Succès !${NC}"
    else
        echo -e "${RED}--> Échec du build pour ${framework}${NC}"
        exit 1
    fi
}

# Vérification de l'existence du dossier evaluator
if [ ! -d "$EVAL_DIR" ]; then
    echo -e "${RED}Erreur : Le dossier '${EVAL_DIR}' est introuvable depuis $(pwd)${NC}"
    exit 1
fi

# Lancement des builds
build_and_tag "sklearn" "Dockerfile.sklearn"
build_and_tag "tensorflow" "Dockerfile.tensorflow"
build_and_tag "pytorch" "Dockerfile.pytorch"
build_and_tag "onnx" "Dockerfile.onnx"

# Nettoyage des couches inutilisées
echo -e "\n[+] Nettoyage des images intermédiaires..."
docker image prune -f

echo -e "\n${GREEN}Terminé ! Les images sont prêtes sur l'hôte.${NC}"
docker images | grep "${IMAGE_PREFIX}"
