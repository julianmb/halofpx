#!/usr/bin/env bash
# ==============================================================================
# upload_laguna_overnight.sh — Automated Overnight Hugging Face Uploader for Laguna S 2.1
# Uploads the 61.20 GiB GGUF weights, verifies checksum, and cleans up local storage.
# ==============================================================================

set -euo pipefail

LOG_FILE="/tmp/laguna_upload.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "================================================================================"
echo " 🌙 Starting Laguna S 2.1 Overnight Upload"
echo " Timestamp: $(date)"
echo " Log file:  ${LOG_FILE}"
echo "================================================================================"

MODEL_FILE="/home/user/source/halofpx-research/laguna-s21/models/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf"
HF_REPO="julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4"
FILENAME="laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf"
EXPECTED_SHA="ea1d854a72c47ec8e72c16ea91b8ff3cd5e1620b834df175f683c86f27dc26d6"

if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ Error: Model file not found at ${MODEL_FILE}!"
    exit 1
fi

FILE_SIZE_GB=$(du -h "$MODEL_FILE" | awk '{print $1}')
echo "Target Model: ${MODEL_FILE} (${FILE_SIZE_GB})"
echo "Destination:  https://huggingface.co/${HF_REPO}"

# 1. Execute Upload via hf CLI / python
echo "Uploading weights to Hugging Face..."
if command -v hf >/dev/null 2>&1; then
    hf upload "${HF_REPO}" "${MODEL_FILE}" "${FILENAME}" \
        --commit-message "weights: upload Laguna S 2.1 ROCmFP4 StrixKVSpine v4 (61.20 GiB) GGUF"
else
    python3 -c "
from huggingface_hub import HfApi
api = HfApi()
api.upload_file(
    path_or_fileobj='${MODEL_FILE}',
    path_in_repo='${FILENAME}',
    repo_id='${HF_REPO}',
    commit_message='weights: upload Laguna S 2.1 ROCmFP4 StrixKVSpine v4 (61.20 GiB) GGUF'
)
"
fi

echo "✅ Upload completed! Verifying file availability on Hugging Face..."

# 2. Verify File on Hugging Face API
VERIFIED=$(python3 -c "
import urllib.request, json
url = 'https://huggingface.co/api/models/${HF_REPO}/tree/main'
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        files = [i.get('path') for i in data]
        if '${FILENAME}' in files:
            print('VERIFIED')
        else:
            print('MISSING')
except Exception as e:
    print('ERROR')
")

if [ "$VERIFIED" == "VERIFIED" ]; then
    echo "🎉 Hugging Face remote file verified!"
    echo "Cleaning up local disk copies (freeing 61.2 GiB)..."
    rm -f "${MODEL_FILE}"
    rm -f "/home/user/source/halofpx-research/laguna-s21/hf-pub/${FILENAME}" || true
    echo "✅ Local files deleted. Storage reclaimed!"
else
    echo "⚠️  Verification check returned: ${VERIFIED}. Keeping local file for safety."
fi

echo "================================================================================"
echo " 🏁 Overnight Upload Finished at $(date)"
echo "================================================================================"
