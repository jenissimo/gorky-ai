# workflow/story_outline.py

import json
from utils import load_prompt
from db import save_artifact

# Параметры генерации для структуры сюжета
TEMPERATURE = 1.2  # Средне-высокая температура для баланса креативности и структуры
MAX_TOKENS = 8000  # Достаточно для детального описания сюжета
JSON_MODE = True   # Структурированный вывод для глав и сцен

def generate_story_outline(llm, creative_brief, title):
    """Генерирует структуру сюжета на основе Creative Brief и названия"""
    
    # Загружаем шаблон промпта
    prompt = load_prompt('story_outline.jinja2', creative_brief=creative_brief, title=title)
    
    # Генерируем структуру сюжета с заданными параметрами
    story_outline = llm.generate(
        prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        json_mode=JSON_MODE
    )
    
    if story_outline:
        # Преобразуем словарь в JSON строку
        if isinstance(story_outline, dict):
            story_outline = json.dumps(story_outline, ensure_ascii=False, indent=2)
        # Сохраняем в базу данных
        artifact_id = save_artifact('story_outline', story_outline)
        return story_outline, artifact_id
    
    return None, None
