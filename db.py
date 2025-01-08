# db.py

import sqlite3
from config import DATABASE
import json

def get_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица для хранения артефактов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step TEXT NOT NULL,
            content TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для хранения DIFF
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER,
            diff TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_artifact(step, content, version=None):
    """
    Сохраняет артефакт в базу данных
    
    Args:
        step: Идентификатор шага/сцены
        content: Содержимое артефакта
        version: Номер версии (если None, будет автоинкремент)
    
    Returns:
        int: ID сохраненного артефакта
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if version is None:
        # Получаем текущую версию
        cursor.execute('SELECT MAX(version) FROM artifacts WHERE step = ?', (step,))
        result = cursor.fetchone()
        current_version = result[0] if result[0] else 0
        version = current_version + 1
    
    cursor.execute('INSERT INTO artifacts (step, content, version) VALUES (?, ?, ?)', 
                  (step, content, version))
    artifact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return artifact_id

def save_diff(artifact_id, diff_data):
    """Сохраняет DIFF для артефакта"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем текущую версию для артефакта
    cursor.execute('SELECT MAX(version) FROM diffs WHERE artifact_id = ?', (artifact_id,))
    result = cursor.fetchone()
    current_version = result[0] if result[0] else 0
    new_version = current_version + 1
    
    # Сохраняем DIFF с версией
    cursor.execute('INSERT INTO diffs (artifact_id, diff, version) VALUES (?, ?, ?)',
                  (artifact_id, json.dumps(diff_data, ensure_ascii=False), new_version))
    diff_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return diff_id

def get_latest_artifact(step):
    """Получает последнюю версию артефакта по имени шага"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT content 
        FROM artifacts 
        WHERE step = ? 
        ORDER BY version DESC 
        LIMIT 1
    ''', (step,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return None

def get_artifact_versions(step):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT version, content FROM artifacts WHERE step = ? ORDER BY version ASC', (step,))
    results = cursor.fetchall()
    conn.close()
    return results

def list_artifacts():
    """
    Возвращает список всех артефактов в базе данных
    
    Returns:
        list: Список словарей с информацией об артефактах
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, step, content, created_at FROM artifacts ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    artifacts = []
    for row in rows:
        artifacts.append({
            'id': row[0],
            'step': row[1],
            'content': row[2][:100] + '...' if len(row[2]) > 100 else row[2],  # Показываем только начало контента
            'created_at': row[3]
        })
    
    conn.close()
    return artifacts
