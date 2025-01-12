from .base import GorkyStage
import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, List
import re

logger = logging.getLogger(__name__)

class BookAssemblyStage(GorkyStage):
    """Этап сборки финальной книги"""
    
    def _escape_yaml(self, text):
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

    def assemble_book(self, title_json, story_structure, scenes_data):
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

    async def convert_to_html(self, markdown_file, agent):
        """
        Конвертирует markdown файл в HTML с добавлением метаданных и стилей
        
        Args:
            markdown_file: Путь к markdown файлу
            agent: Ссылка на агента для доступа к артефактам
        """
        if not os.path.exists(markdown_file):
            logger.error(f"Файл {markdown_file} не найден")
            return None
        
        # Проверяем наличие шаблона
        template_path = os.path.join('templates', 'default.html5')
        if not os.path.exists(template_path):
            logger.error(f"Шаблон {template_path} не найден")
            return None
        
        metadata_file = None
        try:
            # Получаем метаданные
            title_json = await self.get_artefact(agent, "title")
            try:
                if isinstance(title_json, str):
                    title_data = json.loads(title_json)
                    title = title_data.get('title', 'Без названия')
                else:
                    title = title_json.get('title', 'Без названия')
            except:
                title = 'Без названия'
            
            # Создаем временный файл с метаданными
            metadata_file = markdown_file.replace('.md', '_metadata.yaml')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.write(f"""---
title: {self._escape_yaml(title)}
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
            if metadata_file and os.path.exists(metadata_file):
                os.remove(metadata_file)
            return None

    async def convert_to_fb2(self, markdown_file, agent):
        """
        Конвертирует markdown файл в формат FB2
        Требует установки pandoc: pip install pandoc
        
        Args:
            markdown_file: Путь к markdown файлу
            agent: Ссылка на агента для доступа к артефактам
        """
        if not os.path.exists(markdown_file):
            logger.error(f"Файл {markdown_file} не найден")
            return None
        
        metadata_file = None
        try:
            # Получаем метаданные
            title_json = await self.get_artefact(agent, "title")
            story_outline = await self.get_artefact(agent, "story_outline")
            
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
title: {self._escape_yaml(title)}
author: AI Author
date: {datetime.now().strftime("%Y-%m-%d")}
lang: ru
description: |
    {self._escape_yaml(description)}
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
            if metadata_file and os.path.exists(metadata_file):
                os.remove(metadata_file)
            return None

    def _clean_editor_notes(self, text: str) -> str:
        """
        Очищает текст от примечаний редактора с помощью регулярных выражений
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        if not text:
            return ""
            
        # Паттерн для поиска любого текста между знаками равенства
        # (?s) - флаг DOTALL, позволяет . матчить переносы строк
        # (?m) - флаг MULTILINE, обрабатывает текст построчно
        # =+ - один или более знаков равенства
        # .*? - любой текст (нежадный режим)
        # =+ - один или более знаков равенства
        pattern = r"(?sm)==+.*\n==+"
        
        # Заменяем найденные блоки на пустую строку
        cleaned_text = re.sub(pattern, "", text)
        
        # Убираем двойные переносы строк
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        
        return cleaned_text.strip()

    async def process(self, db, llm, agent):
        """Собирает книгу из всех сгенерированных артефактов"""
        try:
            # Получаем необходимые артефакты
            title = await self.get_artefact(agent, "title")
            story_structure = await self.get_artefact(agent, "story_structure")
            
            if not all([title, story_structure]):
                logger.error("Не найдены необходимые артефакты")
                return False
                
            # Преобразуем в словари если нужно
            if isinstance(story_structure, str):
                story_structure = json.loads(story_structure)
            
            # Получаем все сцены
            scenes_data = {}
            for chapter in story_structure['chapters']:
                for scene in chapter['scenes']:
                    scene_key = f"chapter{chapter['number']}_scene{scene['number']}"
                    scene_text = await self.get_artefact(agent, f"chapter{chapter['number']}/scene{scene['number']}")
                    if scene_text:
                        # Если текст в JSON формате, извлекаем его
                        if isinstance(scene_text, str):
                            try:
                                scene_text = json.loads(scene_text)
                                if isinstance(scene_text, dict):
                                    scene_text = scene_text.get('scene_text', '')
                            except json.JSONDecodeError:
                                pass  # Оставляем как есть, если это просто текст
                        elif isinstance(scene_text, dict):
                            scene_text = scene_text.get('scene_text', '')
                            
                        # Очищаем текст от примечаний редактора
                        scene_text = self._clean_editor_notes(scene_text)
                        if scene_text:  # Добавляем только если есть текст
                            scenes_data[scene_key] = scene_text
            
            if not scenes_data:
                logger.error("Не найдены сгенерированные сцены")
                return False
            
            # Собираем книгу
            print("📚 Сборка книги...")
            book_file = self.assemble_book(title, story_structure, scenes_data)
            if not book_file:
                logger.error("Не удалось собрать книгу")
                return False
                
            print(f"✅ Книга собрана: {book_file}")
            
            # Конвертируем в разные форматы
            print("📖 Конвертация в FB2...")
            fb2_file = await self.convert_to_fb2(book_file, agent)
            if fb2_file:
                print(f"✅ Создан FB2: {fb2_file}")
                
            print("🌐 Конвертация в HTML...")
            html_file = await self.convert_to_html(book_file, agent)
            if html_file:
                print(f"✅ Создан HTML: {html_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сборке книги: {e}")
            return False 