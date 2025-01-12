from typing import Optional, Dict, Any
from cognistruct.core import IOMessage
import logging

logger = logging.getLogger(__name__)

class CommandHandler:
    """Обработчик консольных команд"""
    
    def __init__(self, agent):
        self.agent = agent
        
    async def handle_command(self, message: IOMessage, stream: bool = True) -> None:
        """Обработка команд пользователя"""
        # Получаем текст сообщения
        if hasattr(message, 'content'):
            text = message.content
        else:
            text = str(message)
            
        cmd = text.strip().lower()
        
        # Справка
        if cmd == "help" or cmd == "/help":
            print(self._get_help())
            return
            
        # Создание новой книги
        if cmd.startswith("/new "):
            result = await self._create_book(text[5:].strip())
            print(result)
            return
            
        # Открытие существующей книги
        if cmd.startswith("/open "):
            result = await self._open_book(text[6:].strip())
            print(result)
            return
                
        # Список книг
        if cmd == "/list":
            result = await self._list_books()
            print(result)
            return
            
        # Удаление книги
        if cmd.startswith("/delete "):
            result = await self._delete_book(text[8:].strip())
            print(result)
            return
                
        # Запуск/продолжение генерации
        if cmd == "/start":
            result = await self._start_generation()
            print(result)
            return
            
        # Неизвестная команда
        print("❌ Неизвестная команда. Введите /help для просмотра списка доступных команд.")
            
    def _get_help(self) -> str:
        """Возвращает справку по командам"""
        return """
📚 Доступные команды:
/new <название> - создать новую книгу
/open <id> - открыть существующую книгу
/list - показать список книг
/delete <id> - удалить книгу
/start - начать/продолжить генерацию текущей книги
/help - показать эту справку
        """
        
    async def _create_book(self, name: str) -> str:
        """Создает новую книгу"""
        project = await self.agent.project.create({
            "name": name,
            "description": "Книга в процессе генерации",
            "metadata": {
                "stage": 1,
                "status": "new"
            }
        })
        self.agent.current_project = project
        return f"✨ Создана новая книга '{name}' (ID: {project.id})"
        
    async def _open_book(self, project_id: str) -> str:
        """Открывает существующую книгу"""
        try:
            project_id = int(project_id)
            project = await self.agent.project.read(project_id)
            if project:
                self.agent.current_project = project
                stage = project.metadata.get("stage", 1)
                return f"📖 Открыта книга '{project.name}' (этап {stage})"
            return "❌ Книга не найдена"
        except ValueError:
            return "❌ Неверный ID книги"
            
    async def _list_books(self) -> str:
        """Возвращает список книг"""
        projects = await self.agent.project.search({})
        if not projects:
            return "📚 Список книг пуст"
        result = "📚 Список книг:\n"
        for p in projects:
            stage = p.metadata.get("stage", 1)
            status = p.metadata.get("status", "new")
            result += f"- {p.id}: {p.name} (этап {stage}, статус: {status})\n"
        return result
        
    async def _delete_book(self, project_id: str) -> str:
        """Удаляет книгу и все связанные с ней артефакты"""
        try:
            project_id = int(project_id)
            
            # Получаем проект перед удалением
            project = await self.agent.project.read(project_id)
            if not project:
                return "❌ Книга не найдена"
                
            # Формируем шаблон для поиска артефактов
            book_prefix = f"book{project_id}/"
            
            # Получаем все артефакты книги
            artifacts = await self.agent.storage.search({
                "key_prefix": book_prefix
            })
            
            # Удаляем все артефакты
            deleted_count = 0
            for artifact in artifacts:
                await self.agent.storage.delete(artifact["key"])
                deleted_count += 1
                
            # Удаляем сам проект
            if await self.agent.project.delete(project_id):
                if self.agent.current_project and self.agent.current_project.id == project_id:
                    self.agent.current_project = None
                return f"🗑️ Книга и {deleted_count} артефактов удалены"
                
            return "❌ Ошибка при удалении книги"
            
        except ValueError:
            return "❌ Неверный ID книги"
        except Exception as e:
            logger.error(f"Ошибка при удалении книги: {str(e)}")
            return f"❌ Ошибка при удалении: {str(e)}"
            
    async def _start_generation(self) -> str:
        """Запускает/продолжает генерацию книги"""
        if not self.agent.current_project:
            return "❌ Сначала откройте или создайте книгу"
            
        stage = self.agent.current_project.metadata.get("stage", 1)
        success = await self.agent.generate_book(stage)
        
        if success:
            # Обновляем статус и этап
            stage += 1
            await self.agent.project.update(self.agent.current_project.id, {
                "metadata": {
                    "stage": stage,
                    "status": "in_progress"
                }
            })
            return f"✨ Этап {stage-1} успешно завершен!"
        return "❌ Произошла ошибка при генерации" 