from fastapi import APIRouter, HTTPException, BackgroundTasks
from utils import *
from schemas import StartDockerRequest, ShutdownDockerRequest, DeleteDockerRequest
import subprocess
import os
import asyncio
import httpx

router = APIRouter(
    prefix="/orchester",
    tags=["orchester"]
)

PUBLIC_IP = os.getenv("PUBLIC_IP")

async def internal_stop_container(container_id: str):
    """Executa a paragem e remoção física do container."""
    # Stop
    subprocess.run(["docker", "stop", container_id], capture_output=True)
    # Remove
    subprocess.run(["docker", "rm", container_id], capture_output=True)

async def delayed_shutdown(container_id: str, time_alive: int, callback_url: str = None):
    """Tarefa em background que aguarda o tempo de vida e encerra o container."""
    await asyncio.sleep(time_alive)
    
    print(f"INFO: Tempo expirado para o container {container_id}. Encerrando...")
    await internal_stop_container(container_id)
    
    # Notifica o Backend (Interpreter) que o container foi removido
    if callback_url:
        try:
            async with httpx.AsyncClient() as client:
                # O status 'expired' avisa o backend para limpar o banco de dados
                await client.post(callback_url, json={
                    "container_id": container_id, 
                    "status": "expired"
                })
        except Exception as e:
            print(f"ERROR: Falha ao enviar callback para {callback_url}: {e}")

@router.get("")
async def root_func():
    return {"message": "Orchester Microservice is running!"}

@router.get("/status/{container_id}")
async def get_container_status(container_id: str):
    """
    Verifica se o container ainda está em execução no Docker.
    Essencial para a sincronização (Pruning) do Backend.
    """
    try:
        cmd = ["docker", "inspect", "--format={{.State.Running}}", container_id]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"status": "not_found", "running": False}
        
        is_running = result.stdout.strip() == "true"
        return {
            "status": "success", 
            "container_id": container_id, 
            "running": is_running
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_docker(request: StartDockerRequest, background_tasks: BackgroundTasks):
    """
    Inicia um container e agenda o seu encerramento automático.
    """
    try:
        container_name = sanitize_container_name(request.exercise_name)
        time_alive = validate_time_alive(request.time_alive)

        # 1. Pull da imagem
        subprocess.run(["docker", "pull", request.image_link], check=True)

        # 2. Detecta a porta interna via Label
        inspect_cmd = [
            "docker", "inspect", 
            "--format", '{{index .Config.Labels "lycosidae.port"}}', 
            request.image_link
        ]
        label_res = subprocess.run(inspect_cmd, capture_output=True, text=True)
        try:
            container_port = int(label_res.stdout.strip())
        except:
            container_port = 80

        # 3. Aloca porta no host
        host_port = find_free_port(50000, 60000)

        # 4. Inicia o container
        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{host_port}:{container_port}",
            request.image_link
        ]
        result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        container_id = result.stdout.strip()

        # 5. Agenda o encerramento se time_alive > 0
        if time_alive > 0:
            background_tasks.add_task(
                delayed_shutdown, 
                container_id, 
                time_alive, 
                request.callback_url # Opcional: URL para avisar o backend
            )

        return {
            "status": "success",
            "container_id": container_id,
            "host_port": host_port,
            "service_url": f"http://{PUBLIC_IP}:{host_port}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shutdown")
async def shutdown_docker(request: ShutdownDockerRequest):
    """Interrompe um container manualmente via API."""
    try:
        await internal_stop_container(request.container_id)
        return {"status": "success", "container_id": request.container_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete")
async def delete_docker(request: DeleteDockerRequest):
    """Remove container e imagem associada."""
    try:
        # Tenta descobrir a imagem antes de deletar o container
        inspect_cmd = ["docker", "inspect", "--format={{.Image}}", request.container_id]
        img_res = subprocess.run(inspect_cmd, capture_output=True, text=True)
        image_id = img_res.stdout.strip()

        await internal_stop_container(request.container_id)

        if image_id:
            subprocess.run(["docker", "rmi", "-f", image_id])

        return {"status": "success", "container_id": request.container_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))