import logging
import json
from typing import Tuple, Optional, Dict
from utils import load_prompt
from llm_api import get_llm_api
from db import save_artifact

# Параметры генерации
TEMPERATURE = 0.7  # Низкая для точной структуры
MAX_TOKENS = 8000  # Достаточно для детальной структуры
JSON_MODE = True   # Структурированный вывод

logger = logging.getLogger(__name__)

def generate_story_structure(llm, story_outline: str, book_size: str = 'short') -> Tuple[Optional[str], Optional[str]]:
    """
    Генерирует структуру истории на основе общего описания сюжета.
    
    Args:
        llm: LLM API клиент
        story_outline (str): Общее описание сюжета
        book_size (str): Размер книги (very_short/short/medium/long)
        
    Returns:
        Tuple[Optional[str], Optional[str]]: Структура истории и ID артефакта
    """
    try:
        # Получаем параметры структуры на основе размера
        structure_params = get_structure_params(book_size)
        
        # Загружаем промпт
        prompt = load_prompt(
            "story_structure.jinja2",
            story_outline=story_outline,
            structure_params=structure_params
        )
        if not prompt:
            logger.error("Не удалось загрузить промпт story_structure.jinja2")
            return None, None
            
        # Генерируем структуру
        structure = llm.generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=JSON_MODE
        )
        
        if not structure:
            logger.error("Не удалось сгенерировать структуру истории")
            return None, None
            
        # Преобразуем словарь в JSON строку
        if isinstance(structure, dict):
            structure = json.dumps(structure, ensure_ascii=False, indent=2)
            
        # Сохраняем артефакт
        structure_id = save_artifact(
            step="story_structure",
            content=structure
        )
        
        if not structure_id:
            logger.error("Не удалось сохранить структуру истории")
            return None, None
            
        return structure, structure_id
        
    except Exception as e:
        logger.error(f"Ошибка при генерации структуры истории: {e}")
        return None, None 

def get_structure_params(book_size):
    """
    Возвращает параметры структуры на основе размера книги
    """
    params = {
        'very_short': {
            'chapters': 1,
            'scenes_per_chapter': 3,
            'words_per_scene': 1200
        },
        'short': {
            'chapters': 4,
            'scenes_per_chapter': 3,
            'words_per_scene': 1500
        },
        'medium': {
            'chapters': 8,
            'scenes_per_chapter': 4,
            'words_per_scene': 2000
        },
        'long': {
            'chapters': 12,
            'scenes_per_chapter': 5,
            'words_per_scene': 2500
        }
    }
    return params.get(book_size, params['short']) 