from cognistruct.utils.pipeline import Stage
from cognistruct.utils.prompts import prompt_manager
import logging
from typing import Any, Optional, Union, Tuple, Dict
import asyncio
import itertools
import sys
import time

logger = logging.getLogger(__name__)

class GorkyStage(Stage):
    """Базовый класс для всех этапов генерации книги"""
    
    def __init__(self):
        super().__init__()
        self.stage_name = self.__class__.__name__.replace('Stage', '')
    
    async def run(self, db, llm, agent):
        """
        Выполняет этап обработки
        
        Args:
            db: Объект базы данных
            llm: Объект языковой модели
            agent: Ссылка на агента для доступа к плагинам
            
        Returns:
            bool: True если этап выполнен успешно, False в противном случае
        """
        try:
            print(f"📝 Этап: {self.stage_name}")
            result = await self.process(db, llm, agent)
            if result:
                print(f"✓ Этап {self.stage_name} завершен успешно")
            else:
                print(f"⚠ Этап {self.stage_name} завершился с ошибкой")
            return result
        except Exception as e:
            logger.exception(f"Ошибка в этапе {self.stage_name}")
            print(f"❌ Ошибка в этапе {self.stage_name}: {str(e)}")
            return False
    
    async def process(self, db, llm, agent):
        """
        Основная логика этапа. Должна быть переопределена в наследниках.
        
        Args:
            db: Объект базы данных
            llm: Объект языковой модели
            agent: Ссылка на агента для доступа к плагинам
            
        Returns:
            bool: True если этап выполнен успешно, False в противном случае
        """
        raise NotImplementedError("Метод process должен быть переопределен в наследнике")
        
    def get_book_path(self, agent, *parts: str) -> str:
        """
        Создает путь к артефакту книги
        
        Args:
            agent: Ссылка на агента
            *parts: Дополнительные части пути (например, 'chapter1', 'scene1')
            
        Returns:
            str: Полный путь к артефакту
            
        Examples:
            >>> get_book_path(agent)  # Book42
            >>> get_book_path(agent, 'preferences')  # Book42/preferences
            >>> get_book_path(agent, 'chapter1', 'scene1')  # Book42/Chapter1/Scene1
        """
        book_id = agent.current_project.id if agent.current_project else None
        if not book_id:
            raise ValueError("Не выбрана текущая книга")
            
        # Начинаем с ID книги
        path_parts = [("book", str(book_id))]
        
        # Добавляем остальные части, преобразуя их в нужный формат
        for part in parts:
            if part.startswith('chapter'):
                num = part.replace('chapter', '')
                path_parts.append(('chapter', num))
            elif part.startswith('scene'):
                num = part.replace('scene', '')
                path_parts.append(('scene', num))
            else:
                path_parts.append(part)
                
        return agent.storage.generate_hierarchical_id(*path_parts)
        
    async def get_artefact(self, agent, key: str) -> Any:
        """
        Получает артефакт из хранилища
        
        Args:
            agent: Ссылка на агента для доступа к хранилищу
            key: Ключ артефакта
            
        Returns:
            Any: Значение артефакта или None если не найден
        """
        try:
            # Формируем полный путь
            full_key = self.get_book_path(agent, key)
            
            # Получаем последний артефакт
            artifact = await agent.storage.read(full_key)
            
            if not artifact:
                return None
            
            return artifact.get("value")
            
        except Exception as e:
            logger.error(f"Ошибка при получении артефакта {key}: {str(e)}")
            return None
            
    async def set_artefact(self, agent, key: str, value: Any, prompt: Optional[str] = None) -> bool:
        """
        Сохраняет артефакт этапа
        
        Args:
            agent: Ссылка на агента для доступа к хранилищу
            key: Ключ артефакта
            value: Значение артефакта
            prompt: Текст использованного промпта (опционально)
            
        Returns:
            bool: True если артефакт сохранен успешно, False в противном случае
        """
        try:
            # Формируем путь к артефакту
            storage_key = self.get_book_path(agent, key)
            
            # Формируем метаданные
            metadata = {
                "stage": self.stage_name,
                "stage_class": self.__class__.__name__,
                "book_id": agent.current_project.id
            }
            
            # Если был использован промпт, сохраняем его
            if prompt:
                metadata["prompt"] = prompt
            
            # Сохраняем артефакт
            await agent.storage.create({
                "key": storage_key,
                "value": value,
                "metadata": metadata
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении артефакта {key}: {str(e)}")
            return False 
        
    async def show_spinner(self, message: str, coro):
        """
        Показывает анимированный спиннер во время выполнения корутины
        
        Args:
            message: Сообщение для отображения
            coro: Корутина для выполнения
            
        Returns:
            Any: Результат выполнения корутины
        """
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        task = asyncio.create_task(coro)
        
        try:
            while not task.done():
                frame = next(spinner)
                print(f"\r{frame} {message}...", end='', flush=True)
                await asyncio.sleep(0.1)
                
            print("\r" + " " * (len(message) + 10) + "\r", end='', flush=True)
            return await task
            
        except asyncio.CancelledError:
            task.cancel()
            print("\r" + " " * (len(message) + 10) + "\r", end='', flush=True)
            raise
            
        except Exception as e:
            print("\r" + " " * (len(message) + 10) + "\r", end='', flush=True)
            raise e 