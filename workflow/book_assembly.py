import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, List
from utils import load_prompt
from db import get_latest_artifact
from .chapter_assembly import assemble_chapter

logger = logging.getLogger(__name__)

def assemble_book(title_json, story_structure, scenes_data):
    """
    Собирает всю книгу в единый markdown файл с оглавлением и главами
    
    Args:
        title_json (str): JSON с названием книги или строка с названием
        story_structure (str|dict): Структура книги в формате JSON строки или словаря
        scenes_data (dict): Словарь с текстами сцен, где ключи в формате chapter{N}_scene{M}
    
    Returns:
        str: Путь к собранному файлу книги
    """
    try:
        # Пытаемся получить название из JSON
        if isinstance(title_json, str):
            try:
                title_data = json.loads(title_json)
                title = title_data.get('title', title_json)  # Если не получилось распарсить, используем как есть
            except json.JSONDecodeError:
                title = title_json  # Если это не JSON, используем строку как название
        else:
            title = title_json.get('title', 'Без названия')
    except:
        logger.error("Ошибка при получении названия книги", exc_info=True)
        title = 'Без названия'
    
    # Преобразуем story_structure в словарь, если это JSON строка
    if isinstance(story_structure, str):
        try:
            story_structure = json.loads(story_structure)
        except json.JSONDecodeError:
            logger.error("Ошибка при парсинге story_structure", exc_info=True)
            return None
    
    logger.info(f"Сборка книги: {title}")
    
    # Создаем директорию для книги, если её нет
    book_dir = os.path.join('output', 'book')
    os.makedirs(book_dir, exist_ok=True)
    
    # Генерируем имя файла с текущей датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    book_file = os.path.join(book_dir, f'book_{timestamp}.md')
    
    try:
        # Начинаем сборку книги
        with open(book_file, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write(f'# {title}\n\n')
            
            # Оглавление
            f.write('## Оглавление\n\n')
            for chapter in story_structure['chapters']:
                f.write(f"- [Глава {chapter['number']}. {chapter['title']}](#глава-{chapter['number']}-{chapter['title'].lower().replace(' ', '-')})\n")
            f.write('\n---\n\n')
            
            # Собираем каждую главу
            for chapter in story_structure['chapters']:
                chapter_title = chapter['title']
                chapter_number = chapter['number']
                
                # Собираем сцены для главы
                chapter_scenes = []
                for scene in chapter['scenes']:
                    scene_key = f"chapter{chapter_number}_scene{scene['number']}"
                    if scene_key in scenes_data:
                        chapter_scenes.append(scenes_data[scene_key])
                
                if chapter_scenes:
                    # Записываем главу
                    f.write(f'\n## Глава {chapter_number}. {chapter_title}\n\n')
                    f.write('\n\n'.join(chapter_scenes))
                    # Добавляем разделитель только между главами, не в конце
                    if chapter != story_structure['chapters'][-1]:
                        f.write('\n---\n\n')
        
        return book_file
        
    except Exception as e:
        logger.error(f"Ошибка при сборке книги: {e}", exc_info=True)
        return None

def _escape_yaml(text):
    """
    Экранирует специальные символы для YAML
    """
    if not text:
        return ''
    # Оборачиваем в кавычки, если есть специальные символы
    if any(c in text for c in '{}[]!?:,&*#|>'):
        # Экранируем кавычки внутри текста
        text = text.replace('"', '\\"')
        return f'"{text}"'
    return text

def convert_to_html(markdown_file):
    """
    Конвертирует markdown файл в HTML с добавлением метаданных и стилей
    """
    if not os.path.exists(markdown_file):
        logger.error(f"Файл {markdown_file} не найден")
        return None
    
    # Проверяем наличие шаблона
    template_path = os.path.join('templates', 'default.html5')
    if not os.path.exists(template_path):
        logger.error(f"Шаблон {template_path} не найден")
        return None
    
    # Получаем метаданные
    title_json = get_latest_artifact('title')
    try:
        if isinstance(title_json, str):
            title_data = json.loads(title_json)
            title = title_data.get('title', 'Без названия')
        else:
            title = title_json.get('title', 'Без названия')
    except:
        title = 'Без названия'
    
    try:
        # Создаем временный файл с метаданными
        metadata_file = markdown_file.replace('.md', '_metadata.yaml')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"""---
title: {_escape_yaml(title)}
author: AI Author
date: {datetime.now().strftime("%Y-%m-%d")}
lang: ru
---""")
        
        # Генерируем имя для HTML файла
        html_file = markdown_file.replace('.md', '.html')
        
        # Конвертируем в HTML с помощью pandoc
        result = os.system(f'pandoc "{metadata_file}" "{markdown_file}" -f markdown -t html -s --template="{template_path}" -o "{html_file}"')
        
        # Удаляем временный файл с метаданными
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        if result != 0:
            logger.error("Ошибка при конвертации в HTML")
            return None
            
        return html_file
        
    except Exception as e:
        logger.error(f"Ошибка при конвертации в HTML: {e}", exc_info=True)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        return None

def convert_to_fb2(markdown_file):
    """
    Конвертирует markdown файл в формат FB2
    Требует установки pandoc: pip install pandoc
    """
    if not os.path.exists(markdown_file):
        logger.error(f"Файл {markdown_file} не найден")
        return None
    
    try:
        # Получаем метаданные
        title_json = get_latest_artifact('title')
        story_outline = get_latest_artifact('story_outline')
        
        try:
            if isinstance(title_json, str):
                title_data = json.loads(title_json)
                title = title_data.get('title', 'Без названия')
            else:
                title = title_json.get('title', 'Без названия')
        except:
            title = 'Без названия'
            
        try:
            outline_data = json.loads(story_outline) if story_outline else {}
            description = outline_data.get('synopsis', '').split('.')[0] + '.'
        except:
            description = 'Описание отсутствует.'
        
        # Создаем временный файл с метаданными
        metadata_file = markdown_file.replace('.md', '_metadata.yaml')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"""---
title: {_escape_yaml(title)}
author: AI Author
date: {datetime.now().strftime("%Y-%m-%d")}
lang: ru
description: |
    {_escape_yaml(description)}
keywords:
    - художественная литература
    - русская литература
    - AI Author
publisher: AI Book Generator
rights: © {datetime.now().year} AI Author
---""")
        
        # Генерируем имя для FB2 файла
        fb2_file = markdown_file.replace('.md', '.fb2')
        
        # Конвертируем в FB2 с помощью pandoc
        result = os.system(f'pandoc "{metadata_file}" "{markdown_file}" -f markdown -t fb2 -s -o "{fb2_file}"')
        
        # Удаляем временный файл с метаданными
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        if result != 0:
            logger.error("Ошибка при конвертации в FB2")
            return None
            
        return fb2_file
        
    except Exception as e:
        logger.error(f"Ошибка при конвертации в FB2: {e}", exc_info=True)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        return None 