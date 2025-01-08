# workflow/chapter_assembly.py

import os
import logging
from datetime import datetime
from db import get_latest_artifact

logger = logging.getLogger(__name__)

def assemble_chapter(chapter_title, scene_ids):
    """
    Собирает главу из сцен
    
    Args:
        chapter_title: Название главы
        scene_ids: Список ID сцен в правильном порядке (формат: chapter{N}_scene{M})
    
    Returns:
        str: Путь к сохранённому файлу главы
    """
    
    logger.info(f"Начало сборки главы: {chapter_title}")
    logger.info(f"Получены ID сцен: {scene_ids}")
    
    # Создаем директорию для глав, если её нет
    os.makedirs("output/chapters", exist_ok=True)
    
    # Формируем имя файла с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/chapters/chapter_{timestamp}.md"
    
    content = []
    
    # Добавляем заголовок главы
    content.append(f"# {chapter_title}\n")
    
    # Собираем сцены
    for i, scene_id in enumerate(scene_ids, 1):
        logger.info(f"Обработка сцены {i}/{len(scene_ids)} (ID: {scene_id})")
        
        # Получаем последнюю версию сцены
        scene_text = get_latest_artifact(scene_id)
        
        if scene_text:
            logger.info(f"Сцена {i} найдена, длина текста: {len(scene_text)}")
            content.append(scene_text)
            content.append("\n---\n")  # Разделитель между сценами
        else:
            logger.warning(f"Сцена {i} (ID: {scene_id}) не найдена в базе данных")
    
    # Записываем в файл
    with open(filename, "w", encoding="utf-8", newline='\n') as f:
        content_text = "\n".join(content)
        f.write(content_text)
        logger.info(f"Записан файл главы: {filename}, размер: {len(content_text)} символов")
    
    return filename 