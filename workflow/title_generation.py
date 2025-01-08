# workflow/title_generation.py

import json
from db import save_artifact
from utils import load_prompt

# Параметры генерации для названия
TEMPERATURE = 1.5  # Высокая температура для креативности
MAX_TOKENS = 200   # Достаточно для короткого названия и объяснения
JSON_MODE = True   # Структурированный вывод с объяснением

def generate_title(llm, creative_brief):
    """Генерирует название книги на основе Creative Brief"""
    
    # Загружаем шаблон промпта
    prompt = load_prompt('title_generation.jinja2', creative_brief=creative_brief)
    
    # Генерируем название с заданными параметрами
    title_data = llm.generate(
        prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        json_mode=JSON_MODE
    )
    
    if title_data and isinstance(title_data, dict):
        title = title_data.get('title', '').strip()
        if title:
            # Сохраняем полные данные о названии
            title_json = json.dumps(title_data, ensure_ascii=False, indent=2)
            artifact_id = save_artifact('title', title_json)
            return title, artifact_id
    
    return None, None
