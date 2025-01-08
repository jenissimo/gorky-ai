# workflow/creative_brief.py

import json
from utils import load_prompt
from db import save_artifact

# Параметры генерации для Creative Brief
TEMPERATURE = 1.2  # Средняя температура для баланса креативности и структуры
MAX_TOKENS = 4000  # Увеличено для более детальных описаний
JSON_MODE = True   # Структурированный вывод

def generate_creative_brief(llm, preferences):
    """
    Генерирует Creative Brief на основе предпочтений пользователя
    
    Args:
        llm: LLM API клиент
        preferences: словарь с предпочтениями пользователя:
            - concept: базовые параметры (жанр, ЦА, темы, тон)
            - book_size: параметры размера книги
            - llm_service: сервис LLM
        
    Returns:
        tuple: (creative_brief_json, artifact_id)
    """
    try:
        # Подготавливаем параметры для шаблона
        template_params = {
            'params': {
                'concept': preferences['concept'],
                'book_size': preferences['book_size']
            }
        }
        
        # Загружаем шаблон промпта
        prompt = load_prompt('creative_brief.jinja2', **template_params)
        
        # Генерируем Creative Brief
        creative_brief = llm.generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=JSON_MODE
        )
        
        if creative_brief:
            # Проверяем и дополняем структуру
            if isinstance(creative_brief, dict):
                # Убеждаемся, что размер книги соответствует предпочтениям
                creative_brief['book_size'] = preferences['book_size']
                # Сохраняем исходные предпочтения пользователя
                creative_brief['user_preferences'] = {
                    'concept': preferences['concept']
                }
                # Сериализуем в JSON
                creative_brief_str = json.dumps(creative_brief, ensure_ascii=False, indent=2)
            else:
                creative_brief_str = creative_brief
            
            # Сохраняем в базу данных
            artifact_id = save_artifact('creative_brief', creative_brief_str)
            return creative_brief_str, artifact_id
        
        return None, None
        
    except Exception as e:
        print(f"Ошибка при генерации Creative Brief: {str(e)}")
        return None, None
