# workflow/character_sheet.py

import json
from utils import load_prompt
from db import save_artifact

# Параметры генерации для персонажей
TEMPERATURE = 1.0  # Средняя температура для баланса уникальности и последовательности
MAX_TOKENS = 8000  # Достаточно для детального описания персонажей
JSON_MODE = True   # Структурированный вывод для характеристик персонажей

def generate_character_sheets(llm, story_outline: str, story_structure: str) -> tuple:
    """
    Генерирует описания персонажей на основе структуры сюжета
    
    Args:
        llm: LLM API клиент
        story_outline (str): Общее описание сюжета
        story_structure (str): Детальная структура истории с главами и сценами
        
    Returns:
        tuple: (character_sheets_json, artifact_id)
    """
    
    # Загружаем шаблон промпта
    prompt = load_prompt(
        'character_sheet.jinja2',
        story_outline=story_outline,
        story_structure=story_structure
    )
    
    # Генерируем описания персонажей с заданными параметрами
    character_sheets = llm.generate(
        prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        json_mode=JSON_MODE
    )
    
    if character_sheets:
        # Преобразуем словарь в JSON строку
        if isinstance(character_sheets, dict):
            character_sheets = json.dumps(character_sheets, ensure_ascii=False, indent=2)
        # Сохраняем в базу данных
        artifact_id = save_artifact('character_sheets', character_sheets)
        return character_sheets, artifact_id
    
    return None, None
