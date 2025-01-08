# main.py

import logging
import json
import argparse
from workflow.creative_brief import generate_creative_brief
from workflow.title_generation import generate_title
from workflow.story_outline import generate_story_outline
from workflow.story_structure import generate_story_structure
from workflow.character_sheet import generate_character_sheets
from workflow.scene_generation import generate_scene
from workflow.editing import edit_scene, iterative_editing
from workflow.book_assembly import assemble_book, convert_to_fb2, convert_to_html
from workflow.user_interface import get_user_preferences
from llm_api import get_llm_api
from utils import setup_logging
from db import initialize_db, get_latest_artifact
import os

# Настройка логирования
logger = logging.getLogger(__name__)

def stage_preferences():
    """Этап 1: Получение предпочтений пользователя"""
    print(f"\n{'='*50}")
    print("Этап 1: Получение предпочтений пользователя")
    print(f"{'='*50}")
    
    preferences = get_user_preferences()
    if not preferences:
        logger.error("Не удалось получить предпочтения пользователя")
        return None
    
    print("✓ Предпочтения пользователя получены")
    return preferences

def stage_creative_brief(llm, preferences=None):
    """Этап 2: Генерация Creative Brief"""
    print(f"\n{'='*50}")
    print("Этап 2: Генерация Creative Brief")
    print(f"{'='*50}")
    
    if not preferences:
        print("Загрузка сохраненных предпочтений...")
        preferences = get_latest_artifact('preferences')
        if not preferences:
            logger.error("Не найдены предпочтения пользователя")
            return None
        preferences = json.loads(preferences)
    
    print("Генерация Creative Brief...")
    creative_brief, creative_brief_id = generate_creative_brief(llm, preferences)
    if not creative_brief:
        logger.error("Не удалось сгенерировать Creative Brief")
        return None
    
    print("✓ Creative Brief сгенерирован")
    return creative_brief

def stage_title(llm, creative_brief=None):
    """Этап 3: Генерация названия"""
    print(f"\n{'='*50}")
    print("Этап 3: Генерация названия книги")
    print(f"{'='*50}")
    
    if not creative_brief:
        print("Загрузка сохраненного Creative Brief...")
        creative_brief = get_latest_artifact('creative_brief')
        if not creative_brief:
            logger.error("Не найден Creative Brief")
            return None
    
    print("Генерация названия...")
    title, title_id = generate_title(llm, creative_brief)
    if not title:
        logger.error("Не удалось сгенерировать название")
        return None
    
    print(f"✓ Название сгенерировано: {title}")
    return title

def stage_story_outline(llm, creative_brief=None, title=None):
    """Этап 4: Генерация Story Outline"""
    print(f"\n{'='*50}")
    print("Этап 4: Генерация структуры сюжета (Story Outline)")
    print(f"{'='*50}")
    
    if not creative_brief or not title:
        print("Загрузка сохраненных артефактов...")
        creative_brief = get_latest_artifact('creative_brief')
        title = get_latest_artifact('title')
        if not creative_brief or not title:
            logger.error("Не найден Creative Brief или название")
            return None
    
    print("Генерация Story Outline...")
    story_outline, outline_id = generate_story_outline(llm, creative_brief, title)
    if not story_outline:
        logger.error("Не удалось сгенерировать Story Outline")
        return None
    
    print("✓ Story Outline сгенерирован")
    return story_outline

def stage_story_structure(llm, story_outline=None):
    """Этап 5: Генерация Story Structure"""
    print(f"\n{'='*50}")
    print("Этап 5: Генерация детальной структуры (Story Structure)")
    print(f"{'='*50}")
    
    if not story_outline:
        print("Загрузка сохраненного Story Outline...")
        story_outline = get_latest_artifact('story_outline')
        if not story_outline:
            logger.error("Не найден Story Outline")
            return None
    
    # Получаем размер книги из preferences
    preferences = get_latest_artifact('preferences')
    if preferences:
        try:
            preferences = json.loads(preferences)
            book_size = preferences.get('book_size', 'short')
            print(f"Размер книги: {book_size}")
        except json.JSONDecodeError:
            logger.error("Ошибка при парсинге preferences")
            book_size = 'short'
    else:
        logger.warning("Не найдены preferences, используем размер по умолчанию")
        book_size = 'short'
    
    print("Генерация Story Structure...")
    story_structure, structure_id = generate_story_structure(llm, story_outline, book_size)
    if not story_structure:
        logger.error("Не удалось сгенерировать Story Structure")
        return None
    
    try:
        structure_data = json.loads(story_structure)
        chapters_count = len(structure_data['chapters'])
        scenes_count = sum(len(chapter['scenes']) for chapter in structure_data['chapters'])
        print(f"✓ Story Structure сгенерирован:")
        print(f"  - Количество глав: {chapters_count}")
        print(f"  - Количество сцен: {scenes_count}")
    except:
        print("✓ Story Structure сгенерирован")
    
    return story_structure

def stage_character_sheets(llm, story_outline=None, story_structure=None):
    """Этап 6: Генерация Character Sheets"""
    print(f"\n{'='*50}")
    print("Этап 6: Генерация описаний персонажей (Character Sheets)")
    print(f"{'='*50}")
    
    if not story_outline or not story_structure:
        print("Загрузка сохраненных артефактов...")
        story_outline = get_latest_artifact('story_outline')
        story_structure = get_latest_artifact('story_structure')
        if not story_outline or not story_structure:
            logger.error("Не найден Story Outline или Story Structure")
            return None
    
    print("Генерация Character Sheets...")
    character_sheets, sheets_id = generate_character_sheets(llm, story_outline, story_structure)
    if not character_sheets:
        logger.error("Не удалось сгенерировать Character Sheets")
        return None
    
    try:
        characters_data = json.loads(character_sheets)
        print(f"✓ Character Sheets сгенерированы:")
        print(f"  - Количество персонажей: {len(characters_data)}")
        for char in characters_data:
            print(f"  - {char.get('name', 'Безымянный персонаж')}")
    except:
        print("✓ Character Sheets сгенерированы")
    
    return character_sheets

def stage_scenes(llm, story_outline=None, story_structure=None, character_sheets=None):
    """Этап 7: Генерация и редактирование сцен"""
    if not all([story_outline, story_structure, character_sheets]):
        story_outline = get_latest_artifact('story_outline')
        story_structure = get_latest_artifact('story_structure')
        character_sheets = get_latest_artifact('character_sheets')
        if not all([story_outline, story_structure, character_sheets]):
            logger.error("Не найдены необходимые артефакты для генерации сцен")
            return None
    
    try:
        story_structure_data = json.loads(story_structure)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при разборе Story Structure JSON: {e}")
        return None
    
    total_chapters = len(story_structure_data['chapters'])
    scenes = {}
    
    print(f"\n{'='*50}")
    print(f"Начинаем генерацию и редактирование сцен")
    print(f"Всего глав: {total_chapters}")
    print(f"{'='*50}\n")
    
    for chapter_idx, chapter in enumerate(story_structure_data['chapters'], 1):
        total_scenes = len(chapter['scenes'])
        print(f"\nГлава {chapter_idx}/{total_chapters}: {chapter['title']}")
        print(f"Количество сцен в главе: {total_scenes}")
        
        for scene_idx, scene in enumerate(chapter['scenes'], 1):
            print(f"\nСцена {scene_idx}/{total_scenes}: {scene['title']}")
            print("Генерация текста сцены...")
            
            scene_text, scene_id = generate_scene(
                llm,
                chapter['title'],
                scene['title'],
                story_structure,
                character_sheets
            )
            if not scene_text:
                logger.error(f"Не удалось сгенерировать сцену {scene['title']}")
                continue
            
            print("✓ Текст сцены сгенерирован")
            
            # Формируем ключ сцены
            scene_key = f"chapter{chapter_idx}_scene{scene_idx}"
            
            print("Начинаем итеративное редактирование...")
            # Редактируем сцену итеративно
            edited_text, edited_scene_key = iterative_editing(
                llm,
                scene_text,
                scene_key,
                chapter_title=chapter['title'],
                scene_title=scene['title']
            )
            
            if edited_text:
                scenes[edited_scene_key] = edited_text
                print("✓ Редактирование успешно завершено")
            else:
                scenes[scene_key] = scene_text
                print("⚠ Редактирование не удалось, сохраняем оригинальный текст")
                logger.warning(f"Не удалось отредактировать сцену {scene['title']}, используем оригинальный текст")
            
            print(f"\nПрогресс: {chapter_idx}/{total_chapters} глав, {scene_idx}/{total_scenes} сцен в текущей главе")
            print(f"{'='*50}")
    
    if not scenes:
        logger.error("Не удалось сгенерировать ни одной сцены")
        return None
        
    print(f"\n{'='*50}")
    print(f"Генерация и редактирование сцен завершены")
    print(f"Всего сгенерировано сцен: {len(scenes)}")
    print(f"{'='*50}\n")
    
    return scenes

def stage_book_assembly(title=None, story_structure=None, scenes=None):
    """Этап 8: Сборка книги и конвертация"""
    print(f"\n{'='*50}")
    print("Этап 8: Финальная сборка книги")
    print(f"{'='*50}")
    
    if not all([title, story_structure, scenes]):
        print("Загрузка сохраненных артефактов...")
        title = get_latest_artifact('title')
        story_structure = get_latest_artifact('story_structure')
        
        if not title or not story_structure:
            logger.error("Не найдены необходимые артефакты для сборки книги")
            return None
            
        try:
            story_structure_data = json.loads(story_structure) if isinstance(story_structure, str) else story_structure
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при разборе JSON структуры: {e}")
            return None
            
        # Собираем сцены из отдельных артефактов
        print("Загрузка сцен из базы данных...")
        scenes_data = {}
        total_chapters = len(story_structure_data['chapters'])
        
        for chapter_idx, chapter in enumerate(story_structure_data['chapters'], 1):
            total_scenes = len(chapter['scenes'])
            print(f"Загрузка сцен главы {chapter_idx}/{total_chapters}: {chapter['title']}")
            
            for scene_idx, scene in enumerate(chapter['scenes'], 1):
                scene_key = f"chapter{chapter_idx}_scene{scene_idx}"
                scene_text = get_latest_artifact(scene_key)
                
                if scene_text:
                    scenes_data[scene_key] = scene_text
                    print(f"  ✓ Загружена сцена {scene_idx}/{total_scenes}: {scene['title']}")
                else:
                    print(f"  ⚠ Не найдена сцена {scene_idx}/{total_scenes}: {scene['title']}")
                    logger.warning(f"Не найдена сцена {scene_key}")
        
        if not scenes_data:
            logger.error("Не удалось загрузить ни одной сцены")
            return None
            
        print(f"✓ Загружено {len(scenes_data)} сцен")
    else:
        # Если scenes передан напрямую, он в формате словаря
        scenes_data = scenes
        story_structure_data = json.loads(story_structure) if isinstance(story_structure, str) else story_structure
    
    print("\nСборка книги...")
    # Собираем книгу
    book_path = assemble_book(title, story_structure_data, scenes_data)
    if not book_path:
        logger.error("Не удалось собрать книгу")
        return None
    
    print("✓ Книга собрана")
    
    # Извлекаем название книги для вывода
    try:
        if isinstance(title, str):
            title_data = json.loads(title)
            book_title = title_data.get('title', 'Без названия')
        else:
            book_title = title.get('title', 'Без названия')
    except:
        book_title = 'Без названия'
    
    # Конвертируем в FB2 и HTML
    print("\nКонвертация в FB2...")
    try:
        fb2_path = convert_to_fb2(book_path)
        if fb2_path and os.path.exists(fb2_path):
            print("✓ FB2 версия создана")
        else:
            print("⚠ Не удалось создать FB2 версию")
    except Exception as e:
        print("⚠ Ошибка при создании FB2 версии")
        logger.error(f"Ошибка при конвертации в FB2: {e}")
    
    print("\nКонвертация в HTML...")
    try:
        html_path = convert_to_html(book_path)
        if html_path and os.path.exists(html_path):
            print("✓ HTML версия создана")
        else:
            print("⚠ Не удалось создать HTML версию")
    except Exception as e:
        print("⚠ Ошибка при создании HTML версии")
        logger.error(f"Ошибка при конвертации в HTML: {e}")
    
    print(f"\n✓ Все этапы завершены. Книга '{book_title}' готова!")
    return book_path

def generate_book(start_stage=1):
    """
    Генерирует книгу, начиная с указанного этапа
    
    Args:
        start_stage (int): Номер этапа, с которого начать генерацию
            1 - Предпочтения пользователя
            2 - Creative Brief
            3 - Название
            4 - Story Outline
            5 - Story Structure
            6 - Character Sheets
            7 - Сцены
            8 - Сборка книги
    """
    try:
        # Настройка логирования
        setup_logging()
        logger.info(f"Начинаем генерацию книги с этапа {start_stage}")
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных")
        initialize_db()
        
        # Получаем LLM API
        preferences = get_latest_artifact('preferences') if start_stage > 1 else None
        if preferences:
            try:
                preferences = json.loads(preferences)
                llm_service = preferences.get('llm_service', 'deepseek')
            except json.JSONDecodeError:
                llm_service = 'deepseek'
        else:
            llm_service = 'deepseek'
            
        llm = get_llm_api(llm_service)
        if not llm:
            logger.error("Не удалось инициализировать LLM API")
            return False
        
        # Инициализируем переменные
        preferences = None
        creative_brief = None
        title = None
        story_outline = None
        story_structure = None
        character_sheets = None
        scenes = None
        
        # Выполняем этапы
        if start_stage <= 1:
            preferences = stage_preferences()
            if not preferences:
                return False
        
        if start_stage <= 2:
            creative_brief = stage_creative_brief(llm, preferences)
            if not creative_brief:
                return False
        
        if start_stage <= 3:
            title = stage_title(llm, creative_brief)
            if not title:
                return False
        
        if start_stage <= 4:
            story_outline = stage_story_outline(llm, creative_brief, title)
            if not story_outline:
                return False
        
        if start_stage <= 5:
            story_structure = stage_story_structure(llm, story_outline)
            if not story_structure:
                return False
        
        if start_stage <= 6:
            character_sheets = stage_character_sheets(llm, story_outline, story_structure)
            if not character_sheets:
                return False
        
        if start_stage <= 7:
            scenes = stage_scenes(llm, story_outline, story_structure, character_sheets)
            if not scenes:
                return False
        
        if start_stage <= 8:
            book_path = stage_book_assembly(title, story_structure, scenes)
            if not book_path:
                return False
        
        logger.info("Генерация книги завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при генерации книги: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Генерация книги')
    parser.add_argument('--stage', type=int, default=1, choices=range(1, 9),
                      help='Этап, с которого начать генерацию (1-8)')
    args = parser.parse_args()
    
    generate_book(args.stage)
