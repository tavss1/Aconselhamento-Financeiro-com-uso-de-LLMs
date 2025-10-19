-- Script de inicialização do banco de dados
-- Este arquivo será executado automaticamente na primeira inicialização do MySQL

-- Criar o banco de dados se não existir
CREATE DATABASE IF NOT EXISTS aconselhamento_financeiro 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Usar o banco de dados
USE aconselhamento_financeiro;

-- Criar usuário da aplicação com permissões adequadas
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'kiwi';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX ON aconselhamento_financeiro.* TO 'root'@'%';

-- Flush privileges para aplicar as mudanças
FLUSH PRIVILEGES;

-- Definir charset padrão para novas conexões
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Log de inicialização
SELECT 'Database initialization completed successfully' AS status;
