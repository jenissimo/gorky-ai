# workflow/user_interface.py

import logging
from db import save_artifact
import json

logger = logging.getLogger(__name__)

def get_user_preferences():
    """
    Получает предпочтения пользователя для генерации книги
    
    Returns:
        dict: Словарь с предпочтениями или None в случае ошибки
    """
    try:
        print("\nДобро пожаловать в генератор книг!")
        print("\nОтветьте на несколько вопросов о будущей книге:")
        
        # Базовые параметры
        concept = {
            'genre': input("\nЖанр(ы) (например, фэнтези, детектив): ").strip(),
            'target_audience': input("Целевая аудитория (например, подростки 12-16 лет): ").strip(),
            'themes': [x.strip() for x in input("Основные темы через запятую: ").split(',')],
            'tone': input("Тон повествования (например, мрачный, юмористический): ").strip(),
            'additional_notes': input("Дополнительные пожелания (или нажмите Enter, чтобы пропустить): ").strip()
        }

        # Значения по умолчанию
        preferences = {
            'llm_service': 'deepseek',  # Сервис LLM по умолчанию
            'book_size': 'short',  # Размер книги по умолчанию
            'language': 'ru',  # Язык по умолчанию
            'concept': concept  # Добавляем концепцию
        }
        
        # Спрашиваем размер книги
        print("\nВыберите размер книги:")
        print("1. Очень короткая (1 глава, 3 сцены: завязка, развитие, развязка)")
        print("2. Короткая (4 главы, ~12 сцен)")
        print("3. Средняя (8 глав, ~32 сцены)")
        print("4. Длинная (12 глав, ~60 сцен)")
        
        size_choice = input("Введите номер (1-4) [2]: ").strip() or "2"
        
        # Устанавливаем размер на основе выбора
        size_map = {
            "1": "very_short",
            "2": "short",
            "3": "medium",
            "4": "long"
        }
        
        if size_choice not in size_map:
            print("Неверный выбор, используем короткий размер")
            size_choice = "2"
        
        preferences['book_size'] = size_map[size_choice]
        print(f"Выбран размер книги: {preferences['book_size']}")
        
        # Спрашиваем сервис LLM
        print("\nВыберите LLM сервис:")
        print("1. DeepSeek (рекомендуется)")
        print("2. OpenAI")
        
        service_choice = input("Введите номер (1-2) [1]: ").strip() or "1"
        
        # Устанавливаем сервис на основе выбора
        service_map = {
            "1": "deepseek",
            "2": "openai"
        }
        
        if service_choice not in service_map:
            print("Неверный выбор, используем DeepSeek")
            service_choice = "1"
        
        preferences['llm_service'] = service_map[service_choice]
        
        # Сохраняем preferences
        preferences_json = json.dumps(preferences, ensure_ascii=False)
        save_artifact('preferences', preferences_json)
        logger.info(f"Сохранены preferences: {preferences_json}")
        
        return preferences
        
    except Exception as e:
        logger.error(f"Ошибка при получении предпочтений пользователя: {e}")
        return None
