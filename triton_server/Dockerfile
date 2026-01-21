# Triton Inference Server with BGE-M3 Embedding Model
FROM nvcr.io/nvidia/tritonserver:24.08-py3

# Set working directory
WORKDIR /models

# Copy model repository
COPY model_repository/ /models/

# Expose Triton ports
# 8000: HTTP inference
# 8001: gRPC inference  
# 8002: Metrics
EXPOSE 8000 8001 8002

# Start Triton server
CMD ["tritonserver", "--model-repository=/models", "--exit-on-error=false"]
