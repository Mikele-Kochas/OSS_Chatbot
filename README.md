# Tytan AI Chatbot (Ollama + Streamlit)

This project provides a Dockerized setup to run a Chatbot UI powered by Ollama on an Ubuntu server equipped with NVIDIA GPUs (e.g., A100).

## Prerequisites

On your Ubuntu server, ensure you have the following installed:

1.  **Docker Engine**
2.  **NVIDIA Container Toolkit** (Required for GPU passthrough to Ollama)

### Install NVIDIA Container Toolkit (if not installed)

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

sudo systemctl restart docker
```

## How to Install (Detailed Steps)

1.  **Connect to your server via SSH**:
    ```bash
    ssh username@your-server-ip
    ```

2.  **Clone the repository** (This will automatically create a folder named `OSS_Chatbot`):
    ```bash
    git clone https://github.com/Mikele-Kochas/OSS_Chatbot.git
    ```

3.  **Enter the folder**:
    ```bash
    cd OSS_Chatbot
    ```

4.  **Start the Chatbot**:
    ```bash
    docker-compose up -d --build
    ```

5.  **Initialize the Model** (One-time setup):
    Wait for the containers to start, then run:
    ```bash
    docker exec -it ollama-backend ollama run gpt-oss:120b
    ```

## Access
Open your browser and go to: `http://<SERVER_IP>:8501`

3.  **Download the Model**:
    The container needs to download the `gpt-oss:120b` model. This might take a while (approx. 70-80GB depending on quantization).
    Run the following command *inside* the running ollama container:
    ```bash
    docker exec -it ollama-backend ollama run gpt-oss:120b
    ```
    *Note: The `run` command will pull the model if it's not missing, and then drop you into a chat prompt. You can exit the chat (Ctrl+D) once it starts, effectively ensuring the model is pulled and ready.*

4.  **Access the UI**:
    Open your browser and navigate to:
    `http://<SERVER_IP>:8501`

## Troubleshooting

-   **GPU Usage Check**:
    Run `nvidia-smi` on the host to see if the `ollama` process is using the GPU.
-   **Model Loading**:
    Large models (120B) take time to load into VRAM. The first request might timeout or be slow.
-   **Logs**:
    Check logs with `docker-compose logs -f`.
