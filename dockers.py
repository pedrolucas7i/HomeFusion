import subprocess
from pathlib import Path
import platform

def run_command(command):
    """Executa um comando no shell e imprime o resultado ou erro."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o comando: {e.stderr}")

def create_directory(path):
    """
    Cria diretórios e subdiretórios especificados no caminho.
    
    Args:
        path (str): O caminho do diretório a ser criado.
    """
    directory = Path(path).expanduser()  # Expande ~ para o diretório home do usuário
    directory.mkdir(parents=True, exist_ok=True)
    print(f"Diretório criado: {directory}")

def install_docker_linux():
    """Instala Docker em sistemas Linux."""
    print("Instalando Docker no Linux...")
    run_command("sudo apt-get update")
    run_command("sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common")
    run_command("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -")
    run_command('sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"')
    run_command("sudo apt-get update")
    run_command("sudo apt-get install -y docker-ce")

def install_docker_windows():
    """Instala Docker no Windows usando winget."""
    print("Instalando Docker no Windows...")
    run_command("winget install -e --id Docker.DockerDesktop")

def start_docker_service_linux():
    """Inicia o serviço Docker em sistemas Linux."""
    print("Iniciando o serviço Docker no Linux...")
    run_command("sudo systemctl start docker")
    run_command("sudo systemctl enable docker")

def run_ollama_container():
    """Executa o container ollama."""
    print("Rodando o container ollama...")
    command = "docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"
    run_command(command)
    command = "docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main"

def run_pihole_container(password):
    """Executa o container Pi-hole."""
    print("Criando diretórios para o Pi-hole...")
    create_directory("~/docker/pihole/config")
    create_directory("~/docker/pihole/dnsmasq.d")
    print("Rodando o container Pi-hole...")
    command = (
        f"docker run -d "
        f"--name pihole "
        f"-p 53:53/tcp "
        f"-p 53:53/udp "
        f"-p 8090:80 "
        f"-p 8453:443 "
        f"-e TZ='America/New_York' "
        f"-e WEBPASSWORD='{password}' "
        f"-v ~/docker/pihole/config:/etc/pihole "
        f"-v ~/docker/pihole/dnsmasq.d:/etc/dnsmasq.d "
        f"--dns=127.0.0.1 "
        f"--dns=1.1.1.1 "
        f"--restart=unless-stopped "
        f"pihole/pihole"
    )
    run_command(command)