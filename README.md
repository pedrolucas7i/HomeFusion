# HomeFusion
 A Home Server with many features
 
![HomeFusion](screenshots/dashboard.png)
## Project Setup

### Install MySQL Server:
```sh
sudo apt install mysql-server -y
```

### Config MySQL Server:

Enter in mysql prompt:
```sh
sudo mysql -u root
```

Change the password (change the 'mynewpassword' for your password):
```sh
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'mynewpassword';
```

```sh
FLUSH PRIVILEGES;
```

Create database in MySQL prompt:
```sh
CREATE DATABASE ludro;
```

Exit MySQL prompt:
```sh
quit
```

Import MySQL database:
```sh
mysqldump -uroot -pPASSWORD ludro < db.sql
```

### Config App

Create venv (necessary):
```sh
python -m venv server
```

Activate venv (necessary):
```sh
source server/bin/activate
```

Install dependencies:
```sh
pip3 install -r requirements.txt
```

Copy the `.env` file:
```sh
cp .env.example .env
```

Change the .env to your configuration

## Login

Create the user and password for login:
```sh
python3 create_user_password.py
```

## Start Server Application

Run:
```sh
python3 app.py
```

## Result
### Files
![HomeFusion in files](screenshots/files.png)

### Prompt
![HomeFusion in prompt](screenshots/prompt.png)

### Ollama (AI)
![HomeFusion in prompt](screenshots/ollama.png)

