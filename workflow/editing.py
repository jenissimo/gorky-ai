# workflow/editing.py

import json
import os
from datetime import datetime
from utils import load_prompt
from db import save_artifact, save_diff, get_latest_artifact
from config import MAX_EDIT_ITERATIONS
import logging
from typing import Optional
from llm_api import get_llm_api

logger = logging.getLogger(__name__)

# Параметры генерации для редактирования
TEMPERATURE = 1.5  # Низкая температура для консервативных правок
MAX_TOKENS = 8000  # Максимальный размер для работы с большими текстами
JSON_MODE = False

def extract_edited_text(response):
    """
    Извлекает отредактированный текст из ответа модели, отделяя его от списка изменений
    
    Args:
        response: Полный ответ от модели
        
    Returns:
        tuple: (список изменений, отредактированный текст)
    """
    if not response:
        return None, None
        
    # Ищем разделители
    changes_start = response.find("===== ИЗМЕНЕНИЯ =====")
    changes_end = response.find("====================")
    
    if changes_start == -1 or changes_end == -1:
        return None, response.strip()
    
    # Извлекаем список изменений
    changes = response[changes_start:changes_end].strip()
    
    # Извлекаем отредактированный текст (всё после разделителя)
    edited_text = response[changes_end + 20:].strip()
    
    return changes, edited_text

def save_iteration_to_md(scene_id, iteration, original_text, edited_text, changes=None, context=None):
    """
    Сохраняет итерацию редактирования в MD файл
    
    Args:
        scene_id: ID сцены
        iteration: Номер итерации
        original_text: Исходный текст
        edited_text: Отредактированный текст
        changes: Список изменений (опционально)
        context: Словарь с контекстом сцены (название, story outline, character sheets)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/iterations/scene_{scene_id}_iteration_{iteration}_{timestamp}.md"
    
    # Создаем директорию, если её нет
    os.makedirs("output/iterations", exist_ok=True)
    
    content = []
    
    # Добавляем заголовок
    content.append(f"# Итерация редактирования {iteration}")
    content.append(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Добавляем контекст, если он есть
    if context and iteration == 0:  # Сохраняем контекст только для первой итерации
        content.append("## Контекст сцены")
        if 'chapter_title' in context:
            content.append(f"\n### Глава\n{context['chapter_title']}")
        if 'scene_title' in context:
            content.append(f"\n### Сцена\n{context['scene_title']}")
        if 'story_outline' in context:
            content.append("\n### Story Outline\n```json\n" + context['story_outline'] + "\n```")
        if 'character_sheets' in context:
            content.append("\n### Character Sheets\n```json\n" + context['character_sheets'] + "\n```")
        content.append("\n---\n")
    
    # Добавляем список изменений, если есть
    if changes:
        content.append("## Внесенные изменения")
        content.append("```")
        content.append(changes)
        content.append("```\n")
    
    # Добавляем тексты
    content.append("## Оригинальный текст")
    content.append("```")
    content.append(original_text)
    content.append("```\n")
    
    if edited_text != original_text:
        content.append("## Отредактированный текст")
        content.append("```")
        content.append(edited_text)
        content.append("```")
    
    # Записываем в файл с явным указанием кодировки UTF-8
    with open(filename, "w", encoding="utf-8", newline='\n') as f:
        f.write("\n".join(content))
    
    return filename

def iterative_editing(llm, text, scene_key, chapter_title=None, scene_title=None, max_iterations=MAX_EDIT_ITERATIONS):
    """
    Итеративно улучшает текст через несколько проходов редактирования
    
    Args:
        llm: LLM API клиент
        text: Исходный текст
        scene_key: Ключ сцены в формате chapter{N}_scene{M}
        chapter_title: Название главы
        scene_title: Название сцены
        max_iterations: Максимальное количество итераций (по умолчанию из конфига)
    
    Returns:
        tuple: (отредактированный текст, ключ сцены)
    """
    current_text = text
    
    # Получаем последние артефакты для контекста
    story_outline = get_latest_artifact('story_outline')
    character_sheets = get_latest_artifact('character_sheets')
    
    # Создаем контекст для редактирования
    context = {
        'chapter_title': chapter_title,
        'scene_title': scene_title,
        'story_outline': story_outline,
        'character_sheets': character_sheets
    }
    
    # Сохраняем оригинальную версию в MD файл
    save_iteration_to_md(scene_key, 0, text, text, context=context)
    print(f"Сохранена оригинальная версия текста")
    
    for i in range(max_iterations):
        print(f"\nИтерация редактирования {i+1}/{max_iterations}")
        
        # Загружаем шаблон промпта с контекстом
        prompt = load_prompt('editing.jinja2',
                           text=current_text,
                           iteration=i+1,
                           chapter_title=chapter_title,
                           scene_title=scene_title,
                           story_outline=story_outline,
                           character_sheets=character_sheets)
        
        print("Генерация улучшенной версии...")
        # Генерируем улучшенную версию
        response = llm.generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=JSON_MODE
        )
        
        # Извлекаем изменения и отредактированный текст
        changes, edited_text = extract_edited_text(response)
        
        if edited_text and edited_text != current_text:
            print("✓ Получена улучшенная версия")
            
            # Сохраняем результат итерации в MD
            save_iteration_to_md(scene_key, i+1, current_text, edited_text, changes, context)
            print(f"✓ Сохранена итерация {i+1}")
            
            # Сохраняем diff
            diff = generate_diff(current_text, edited_text)
            save_diff(scene_key, diff)
            
            # Сохраняем новую версию сцены
            save_artifact(scene_key, edited_text, version=i+1)
            
            # Обновляем текущий текст
            current_text = edited_text
        else:
            print("ℹ Текст больше не требует улучшений")
            break
    
    return current_text, scene_key

def generate_diff(original_text, edited_text):
    """
    Генерирует diff между оригинальным и отредактированным текстом.
    В будущем можно реализовать более сложную логику diff.
    """
    return {
        'original': original_text,
        'edited': edited_text
    }

def edit_scene(llm, scene_text, chapter_title, scene_title, story_outline, character_sheets):
    """
    Редактирует текст сцены для улучшения качества
    
    Args:
        llm: LLM API клиент
        scene_text (str): Исходный текст сцены
        chapter_title (str): Название главы
        scene_title (str): Название сцены
        story_outline (str): Story Outline в формате JSON
        character_sheets (str): Character Sheets в формате JSON
        
    Returns:
        str: Отредактированный текст сцены или None в случае ошибки
    """
    try:
        # Загружаем шаблон промпта
        prompt = load_prompt(
            'editing.jinja2',
            text=scene_text,
            chapter_title=chapter_title,
            scene_title=scene_title,
            story_outline=story_outline,
            character_sheets=character_sheets,
            iteration=1
        )
        
        # Редактируем сцену
        edited_text = llm.generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=JSON_MODE
        )
        
        if not edited_text:
            logger.error("Не удалось отредактировать сцену")
            return None
            
        return edited_text
        
    except Exception as e:
        logger.error(f"Ошибка при редактировании сцены: {e}")
        return None
