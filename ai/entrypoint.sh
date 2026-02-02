#!/bin/bash
set -e

echo "=========================================="
echo "Starting Data Ingestion Pipeline"
echo "=========================================="

# Wait for Qdrant to be ready
echo "Waiting for Qdrant..."
until curl -sf http://${QDRANT_HOST:-localhost}:6333/ > /dev/null 2>&1; do
    echo "Qdrant not ready, waiting..."
    sleep 2
done
echo "✓ Qdrant is ready"

# Wait for Triton to be ready (optional - skip if SKIP_TRITON_CHECK=true)
# Note: WSL2 has networking issues with host.docker.internal, so skip by default
if [ "${SKIP_TRITON_CHECK:-true}" != "true" ]; then
    TRITON_PORT=${TRITON_PORT:-8003}
    echo "Waiting for Triton at ${TRITON_HOST:-triton-gpu}:${TRITON_PORT}..."
    until curl -sf http://${TRITON_HOST:-triton-gpu}:${TRITON_PORT}/v2/health/ready > /dev/null 2>&1; do
        echo "Triton not ready, waiting..."
        sleep 2
    done
    echo "✓ Triton is ready"
else
    echo "⏭ Skipping Triton check (SKIP_TRITON_CHECK=true)"
fi

# Run ingestion
echo "Starting ingestion..."
python knowledge/vector_db/ingest.py \
    --qdrant-host ${QDRANT_HOST:-localhost} \
    --triton-host ${TRITON_HOST:-localhost} \
    --batch-size ${BATCH_SIZE:-8}

echo "=========================================="
echo "✅ Ingestion Complete"
echo "=========================================="
