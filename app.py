import os
import platform
import subprocess
import bcrypt
import psutil
import mysql.connector
import shutil
import getpass
import socket
import docker
from flask import Flask, redirect, session, url_for, render_template, request, flash, send_from_directory
from werkzeug.utils import secure_filename
import dockers


# Configuration
UPLOAD_FOLDER = 'uploads/'  # Directory where files will be stored
NOT_ALLOWED_EXTENSIONS = {
    # Executables
    '.exe', '.bat', '.cmd', '.sh', '.bin', '.msi', '.com', '.scr',

    # Scripts and Code
    '.php', '.py', '.pl', '.cgi', '.js', '.asp', '.jsp', '.rb',

    # Documents with Macros
    '.docm', '.xlsm', '.pptm',

    # Libraries and Links
    '.dll', '.so', '.dylib', '.lnk',

    # Configuration and System Files
    '.ini', '.conf', '.sys', '.drv', '.inf',

    # Images with Embedded Code
    '.svg', '.ico'
}

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY')  # Ensure there's a fallback key for development
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

USER_DB = os.environ.get('USER_DB')
PASS_DB = os.environ.get('PASS_DB')
DB = os.environ.get('DB')

# Database Functions
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user=USER_DB,
        password=PASS_DB,
        database=DB
    )

def create_folder(folder_name):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def list_files_and_folders(path):
    """ List all files and folders in a directory. """
    try:
        if not os.path.exists(path):
            raise FileNotFoundError("The directory does not exist.")
        entries = os.listdir(path)
        files = [entry for entry in entries if os.path.isfile(os.path.join(path, entry))]
        folders = [entry for entry in entries if os.path.isdir(os.path.join(path, entry))]
        return files, folders
    except Exception as e:
        flash('Error retrieving files and folders: ' + str(e), 'danger')
        return [], []


def create_user(username, password):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("""
                INSERT INTO users (username, password) VALUES (%s, %s)
            """, (username, hashed_password.decode('utf-8')))
            connection.commit()
    finally:
        connection.close()

def get_users_by_name(username):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id, username FROM users WHERE username LIKE %s", ("%" + username + "%",))
            return cursor.fetchall()
    finally:
        connection.close()

def get_all_users():
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            return users if users else []
    finally:
        connection.close()

def delete_user(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            # Verifica o número total de usuários
            cursor.execute("SELECT COUNT(*) as total FROM users")
            result = cursor.fetchone()
            if result['total'] <= 1:
                raise Exception("Cannot delete the last remaining user.")

            # Exclui o usuário especificado
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
    finally:
        connection.close()

def update_user_password(user_id, new_password):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", 
                           (hashed_password.decode('utf-8'), user_id))
            connection.commit()
    finally:
        connection.close()

def apply_wallpaper_and_theme(user_id, wallpaper_path, theme):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO wallpapers_and_theme_for_user (user_id, wallpaper_path, theme) 
                VALUES (%s, %s, %s)
            """, (user_id, wallpaper_path, theme))
            connection.commit()
    finally:
        connection.close()

def get_last_applied_wallpaper_and_theme(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT * FROM wallpapers_and_theme_for_user 
                WHERE user_id = %s ORDER BY applied_at DESC LIMIT 1
            """, (user_id,))
            return cursor.fetchone()
    finally:
        connection.close()

def get_selected_wallpaper_and_theme(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT wallpaper_path, theme 
                FROM wallpapers_and_theme_for_user 
                WHERE user_id = %s 
                ORDER BY applied_at DESC LIMIT 1
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                selected_wallpaper_path = "static/wallpapers/" + result['wallpaper_path']
                selected_theme = result['theme']
            else:
                selected_wallpaper_path = ""
                selected_theme = ""
    finally:
        connection.close()
    return selected_wallpaper_path, selected_theme

def log_user_access(user_id, access_level):
    ip_address, os_name, user_agent = get_device_info()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO access (user_id, access_level, ip_address, os_name, user_agent, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (user_id, access_level, ip_address, os_name, user_agent))
            connection.commit()
    finally:
        connection.close()

# Utility Functions
def allowed_file(filename):
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext not in NOT_ALLOWED_EXTENSIONS

def find_available_port(start_port=1024, end_port=65535, excluded_ports={3000, 8090, 8453, 80, 443}):
    """ Encontra uma porta disponível entre start_port e end_port, excluindo portas na lista excluded_ports. """
    for port in range(start_port, end_port + 1):
        if port not in excluded_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', port))
                if result != 0:
                    return port
    raise RuntimeError("No available ports found.")

def check_docker_installed():
    try:
        result = subprocess.run(['docker', '--version'], shell=True, capture_output=True, text=True, check=True)
        # Se o comando for bem-sucedido, o Docker está instalado
        print("Docker está instalado:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Docker não está instalado. Detalhes:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        # Se o comando não for encontrado, o Docker não está instalado
        print("Docker não está instalado. O comando 'docker' não foi encontrado.")
        return False

def get_cpu_usage():
    try:
        if platform.system() == "Windows":
            load1, load5, load15 = psutil.getloadavg()
            cpu_usage = (load15 / os.cpu_count()) * 100
            return cpu_usage
        else:
            load = os.getloadavg()[0]
            cpu_usage = load * 100
            return round(cpu_usage, 2)
    except Exception as e:
        return "Error: " + str(e)

def get_ram_usage():
    try:
        if platform.system() == "Windows":
            ram_usage = psutil.virtual_memory()[2]
            return ram_usage
        else:
            output = subprocess.getoutput("free -m | grep Mem")
            tokens = output.split()
            ram_total = int(tokens[1])
            ram_used = int(tokens[2])
            ram_usage = (ram_used / ram_total) * 100
            return round(ram_usage, 2)
    except Exception as e:
        return "Error: " + str(e)

def get_wifi_signal():
    try:
        if platform.system() == "Windows":
            output = subprocess.getoutput("netsh wlan show interfaces")
            for line in output.splitlines():
                if "Signal" in line:
                    signal_level = line.split(":")[1].strip().replace("%", "")
                    return int(signal_level)
        else:
            output = subprocess.getoutput("nmcli dev wifi")
            for line in output.splitlines():
                if "*" in line:
                    parts = line.split()
                    signal_level = parts[6].replace('%', '')
                    return int(signal_level)
    except Exception as e:
        return "Error: " + str(e)

def get_device_info():
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    os_name = platform.system()
    return ip_address, os_name, user_agent

# Routes
@app.route('/')
def dashboard():
    user_id = session.get('user_id', None)
    if not user_id:
        return redirect(url_for('login'))

    wallpaper, theme = get_selected_wallpaper_and_theme(user_id)
    cpu_usage = get_cpu_usage()
    ram_usage = get_ram_usage()
    wifi_signal = get_wifi_signal()

    return render_template('dashboard.html',
                           wallpaper=wallpaper,
                           theme=theme,
                           cpu_usage=cpu_usage,
                           ram_usage=ram_usage,
                           wifi_signal=wifi_signal)

@app.route('/files/', defaults={'folder': 'root'})
@app.route('/files/<path:folder>', methods=['GET', 'POST'])
def files(folder):
    # Caminho completo para a pasta atual
    current_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)

    # Garantir que a pasta existe
    if not os.path.exists(current_folder):
        os.makedirs(current_folder)

    if request.method == 'POST':
        # Upload de arquivo
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_folder, filename)
                file.save(file_path)
                flash('File uploaded successfully', 'success')
            else:
                flash('File type not allowed', 'danger')

        # Criação de nova pasta
        elif 'new_folder' in request.form:
            new_folder = request.form['new_folder'].strip()
            if new_folder and new_folder.lower() != 'uploads':  # Impedir criação de pasta chamada "uploads"
                new_folder_path = os.path.join(current_folder, new_folder)
                if not os.path.exists(new_folder_path):
                    os.makedirs(new_folder_path)
                    flash('Folder created successfully', 'success')
                else:
                    flash('Folder already exists', 'danger')
            else:
                flash('Invalid folder name.', 'danger')

        return redirect(url_for('files', folder=folder))

    # Obtenha arquivos e pastas na pasta atual
    files, folders = list_files_and_folders(current_folder)

    # Diretório pai
    parent_folder = None if folder == "" else os.path.dirname(folder)

    return render_template('files.html',
                           current_folder=folder,
                           files=files,
                           folders=folders,
                           parent_folder=parent_folder)

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    folder = request.args.get('folder', '')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(os.path.dirname(file_path), filename, as_attachment=True)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('files', folder=folder))


@app.route('/delete/<path:filename>', methods=['POST'])
def delete_file(filename):
    folder = request.form['folder']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)
        flash('File deleted successfully', 'success')
    else:
        flash('File not found', 'danger')
    return redirect(url_for('files', folder=folder))

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder_to_delete = request.form['folder']
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_to_delete)
    if os.path.isdir(folder_path):
        try:
            shutil.rmtree(folder_path)  # Remove a pasta e seu conteúdo
            flash('Folder deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting folder: {str(e)}', 'danger')
    else:
        flash('Folder not found', 'danger')
    return redirect(url_for('files'))

@app.route('/create_folder', methods=['POST'])
def create_folder_route():
    folder = request.form['folder']
    new_folder = request.form['new_folder']
    new_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, new_folder)
    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)
        flash('Folder created successfully', 'success')
    else:
        flash('Folder already exists', 'danger')
    return redirect(url_for('files', folder=folder))

@app.errorhandler(405)
def method_not_allowed(e):
    user_id = session.get('user_id', None)
    if not user_id:
        return redirect(url_for('login'))
    
    # Verificar se o erro 405 ocorreu na rota /files/
    if request.path.startswith('/files'):
        flash('It is not allowed to create files in the root directory.', 'danger')
        return redirect(url_for('files'))
    # Caso contrário, delegar ao manipulador global ou retornar uma resposta padrão
    return "Method Not Allowed", 405
    
@app.route('/setwt', methods=['GET', 'POST'])
def set_wallpaper_and_theme():
    if request.method == 'POST':
        wallpaper_path = request.form.get('wallpaper')
        theme = request.form.get('theme')
        user_id = session['user_id']

        apply_wallpaper_and_theme(user_id, wallpaper_path, theme)
        flash('Wallpaper and theme updated successfully!', 'success')
    availble_wallpapers = os.listdir("static/wallpapers/")
    selected_wallpaper_path, selected_theme = get_selected_wallpaper_and_theme(session['user_id'])
    return render_template('setwt.html', 
                           availble_wallpapers=availble_wallpapers,
                           selected_wallpaper_path=selected_wallpaper_path, 
                           selected_theme=selected_theme)
    
@app.route('/upload_wallpaper', methods=['GET', 'POST'])
def upload_wallpaper():
    if request.method == 'POST':
        if 'wallpaper' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['wallpaper']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and (os.path.splitext(file.filename)[1].lower() in ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            file_path = os.path.join("static/wallpapers/", filename)
            file.save(file_path)
            
            flash('Wallpaper successfully uploaded', 'success')
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    return render_template('setwt.html')

@app.route('/user_management', methods=['GET', 'POST'])
def user_management():
    users = get_all_users()
    if users is None:
        users = []
    return render_template('user_management.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    try:
        delete_user(user_id)
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('user_management'))

@app.route('/update_password/<int:user_id>', methods=['POST'])
def update_password_route(user_id):
    new_password = request.form['new_password']
    update_user_password(user_id, new_password)
    flash('Password updated successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/create_user', methods=['POST'])
def create_user_route():
    username = request.form['username']
    password = request.form['password']
    create_user(username, password)
    flash('User created successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get('user_id', None)
    if not user_id:
        return redirect(url_for('login'))

    wallpaper, theme = get_selected_wallpaper_and_theme(user_id)
    return render_template('settings.html',
                           theme=theme)

@app.route('/prompt', methods=['GET', 'POST'])
def prompt():
    user_id = session.get('user_id', None)
    if not user_id:
        return redirect(url_for('login'))
    if platform.system() == "Windows":
        userhostfile = os.getcwd() + " $ "
    else:
        userhostfile = getpass.getuser() + "@" + socket.gethostname() + ":/" + os.path.basename(os.getcwd()) + "$ "
    if request.method == 'POST':
        command = request.form['command']
        try:
            result = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode("utf-8") + result.stderr.decode("utf-8")
        except Exception as e:
            output = str(e)

        return render_template('prompt.html',
                               userhostfile=userhostfile,
                               output=output)
    return render_template('prompt.html',
                           userhostfile=userhostfile,
                           output="")

@app.route('/install_docker', methods=['GET', 'POST'])
def install_docker():
    if request.method == 'POST':
        system = platform.system().lower()
        if system == "linux":
            dockers.install_docker_linux()
        elif system == "windows":
            return render_template('indisponivel.html')
        else:
            return render_template('indisponivel.html')
        flash('Docker instalado com sucesso!', 'success')
    return render_template('install_docker.html')

@app.route('/uninstall_docker', methods=['POST'])
def uninstall_docker():
    system = platform.system().lower()
    if system == "linux":
        dockers.run_command("sudo apt-get remove --purge -y docker-ce")
        dockers.run_command("sudo apt-get autoremove -y")
    elif system == "windows":
        return render_template('indisponivel.html')
    else:
        return render_template('indisponivel.html')
    flash('Docker desinstalado com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/install_custom_container', methods=['GET', 'POST'])
def install_custom_container():
    if request.method == 'POST':
        system = platform.system().lower()
        if system == "linux":
            container_name = request.form['container_name']
            container_image = request.form['container_image']

            # Encontrar uma porta disponível
            port = find_available_port()

            # Comando Docker com mapeamento de porta
            container_command = f"docker run -d --name {container_name} -p {port}:80 {container_image}"
            dockers.run_command(container_command)

            flash(f'Container {container_name} instalado com sucesso na porta {port}!', 'success')
        elif system == "windows":
            return render_template('indisponivel.html')
        else:
            return render_template('indisponivel.html')
        
    return render_template('install_custom_container.html')


@app.route('/uninstall_container', methods=['POST'])
def uninstall_container():
    system = platform.system().lower()
    if system == "linux":
        container_name = request.form['container_name']
        dockers.run_command(f"docker stop {container_name}")
        dockers.run_command(f"docker rm {container_name}")
        flash(f'Container {container_name} desinstalado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    elif system == "windows":
        return render_template('indisponivel.html')
    else:
        return render_template('indisponivel.html')


@app.route('/docker_apps')
def docker_apps():
    system = platform.system().lower()
    if system == "windows":
        return render_template('indisponivel.html')
    elif system == "linux":
        if check_docker_installed():
            try:
                # Executar o comando `docker ps` para obter a lista de containers em execução com detalhes formatados
                result = subprocess.run(
                    ['docker', 'ps', '--format', '{{.Names}} {{.Image}} {{.Status}}'], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    check=True
                )
                
                container_info_lines = result.stdout.strip().split('\n')
                apps = []

                for line in container_info_lines:
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        app_info = {
                            'name': parts[0],
                            'image': parts[1],
                            'status': parts[2],
                            'icon': 'static/icons/application.png'  # Substitua com ícones reais ou específicos
                        }
                        apps.append(app_info)

                return render_template('applications.html', apps=apps)
            except subprocess.CalledProcessError as e:
                flash(f'Erro ao obter aplicações Docker: {str(e)}', 'danger')
                print(f'Erro ao obter aplicações Docker: {str(e)}')
        else:
            return redirect(url_for('install_docker'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_db_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    session['logged_in'] = True
                    session['user_id'] = user['id']

                    log_user_access(user['id'], 'Login Successful')
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error=True)
        finally:
            connection.close()

    return render_template('login.html')

@app.before_request
def check_login():
    public_endpoints = ['login']
    if 'logged_in' not in session and request.endpoint not in public_endpoints:
        return redirect(url_for('login'))

# Application Entry Point
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
