
CREATE DATABASE ludro;


USE ludro;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);


CREATE TABLE access (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    access_level VARCHAR(50),
    ip_address VARCHAR(45),
    os_name VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE wallpapers_and_theme_for_user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    wallpaper_path VARCHAR(255),
    theme VARCHAR(50),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE docker_containers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    icon VARCHAR(255) NULL
);

INSERT INTO docker_containers (name, port, is_default, icon) VALUES ('ollama', 3000, TRUE, '/static/icons/ollama.png');
INSERT INTO docker_containers (name, port, is_default, icon) VALUES ('pihole', 8090, TRUE, '/static/icons/pihole.png');
