# workflow/scene_generation.py

import json
import logging
from utils import load_prompt
from db import save_artifact, get_latest_artifact

# Настройка логгера
logger = logging.getLogger(__name__)

# Параметры генерации для сцен
TEMPERATURE = 1.5  # Высокая температура для креативного повествования
MAX_TOKENS = 8000  # Максимальный размер для детальных сцен
JSON_MODE = False  # Обычный текстовый режим для художественного текста

# Параметры размера сцен
TARGET_WORD_COUNT = 1500  # Целевое количество слов в сцене

def get_scene_info(story_structure, chapter_title, scene_title):
    """
    Извлекает информацию о сцене из story_structure
    
    Returns:
        tuple: (chapter_id, scene_id, scene_info)
    """
    try:
        structure = json.loads(story_structure) if isinstance(story_structure, str) else story_structure
        
        for chapter in structure['chapters']:
            if chapter['title'] == chapter_title:
                for scene in chapter['scenes']:
                    if scene['title'] == scene_title:
                        scene_info = {
                            'description': scene['description'],
                            'characters': scene['characters'],
                            'location': scene['location'],
                            'time': scene['time'],
                            'dramatic_info': scene['dramatic_info']
                        }
                        return (
                            chapter['number'],
                            scene['number'],
                            scene_info
                        )
        raise ValueError(f"Сцена {scene_title} не найдена в главе {chapter_title}")
    except Exception as e:
        logger.error(f"Ошибка при извлечении информации о сцене: {str(e)}")
        logger.error(f"Тип story_structure: {type(story_structure)}")
        return None, None, None

def get_previous_scene(story_structure, chapter_number, scene_number):
    """
    Получает текст предыдущей сцены из базы данных
    
    Args:
        story_structure: Структура истории
        chapter_number: Номер текущей главы
        scene_number: Номер текущей сцены
        
    Returns:
        tuple: (текст предыдущей сцены, информация о предыдущей сцене)
    """
    try:
        structure = json.loads(story_structure) if isinstance(story_structure, str) else story_structure
        
        # Если это первая сцена первой главы
        if chapter_number == 1 and scene_number == 1:
            return None, None
            
        # Если это первая сцена главы
        if scene_number == 1:
            prev_chapter = next(
                (ch for ch in structure['chapters'] if ch['number'] == chapter_number - 1),
                None
            )
            if prev_chapter:
                prev_scene = prev_chapter['scenes'][-1]  # Последняя сцена предыдущей главы
                scene_key = f"chapter{chapter_number-1}_scene{prev_scene['number']}"
        else:
            current_chapter = next(
                (ch for ch in structure['chapters'] if ch['number'] == chapter_number),
                None
            )
            if current_chapter:
                prev_scene = next(
                    (sc for sc in current_chapter['scenes'] if sc['number'] == scene_number - 1),
                    None
                )
                scene_key = f"chapter{chapter_number}_scene{scene_number-1}"
                
        if prev_scene:
            prev_scene_text = get_latest_artifact(scene_key)
            prev_scene_info = {
                'title': prev_scene['title'],
                'description': prev_scene['description'],
                'characters': prev_scene['characters'],
                'location': prev_scene['location'],
                'time': prev_scene['time'],
                'dramatic_info': prev_scene['dramatic_info']
            }
            return prev_scene_text, prev_scene_info
            
    except Exception as e:
        logger.error(f"Ошибка при получении предыдущей сцены: {e}")
    
    return None, None

def generate_scene(llm, chapter_title, scene_title, story_outline, character_sheets):
    """
    Генерирует сцену на основе структуры истории и описания персонажей
    
    Args:
        llm: LLM API клиент
        chapter_title: Название главы
        scene_title: Название сцены
        story_outline: Story Outline в формате JSON
        character_sheets: Character Sheets в формате JSON
    
    Returns:
        tuple: (текст сцены, ID сцены)
    """
    try:
        # Получаем информацию о сцене
        chapter_id, scene_id, scene_info = get_scene_info(
            story_outline, chapter_title, scene_title
        )
        
        if not all([chapter_id, scene_id, scene_info]):
            logger.error("Не удалось получить информацию о сцене")
            return None, None
            
        # Получаем предыдущую сцену для контекста
        prev_scene_text, prev_scene_info = get_previous_scene(
            story_outline, chapter_id, scene_id
        )
        
        # Загружаем шаблон промпта
        prompt = load_prompt(
            'scene_generation.jinja2',
            chapter_title=chapter_title,
            scene_title=scene_title,
            story_outline=story_outline,
            character_sheets=character_sheets,
            scene_info=scene_info,
            prev_scene_text=prev_scene_text,
            prev_scene_info=prev_scene_info,
            target_word_count=TARGET_WORD_COUNT
        )
        
        # Генерируем сцену
        scene_text = llm.generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=JSON_MODE
        )
        
        if scene_text:
            # Формируем ключ сцены
            scene_key = f"chapter{chapter_id}_scene{scene_id}"
            
            # Сохраняем сцену
            artifact_id = save_artifact(scene_key, scene_text)
            
            return scene_text, scene_key
        
        return None, None
        
    except Exception as e:
        logger.error(f"Ошибка при генерации сцены: {e}")
        return None, None
