# NVIDIA-locked base image — the #1 blocker RocmPilot flags.
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

# Assumes NVIDIA container runtime.
CMD ["python3", "app.py"]
