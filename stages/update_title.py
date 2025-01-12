from .base import GorkyStage
import logging
import json

logger = logging.getLogger(__name__)

class UpdateProjectTitleStage(GorkyStage):
    """Этап обновления названия проекта после генерации заголовка"""
    
    def __init__(self):
        super().__init__()
        self.stage_name = "Обновление названия"
        
    async def process(self, prev_result, llm, agent):
        """Обновляет название проекта сгенерированным заголовком"""
        # Получаем сгенерированный заголовок
        title = await self.get_artefact(agent, "title")
        print(f"🔍 Получен заголовок: {title}")
        
        if not agent.current_project:
            logger.error("Не выбран текущий проект")
            return False
            
        print(f"📚 ID проекта: {agent.current_project.id}")
        
        if not title:
            logger.error("Не найден сгенерированный заголовок")
            return False
            
        # Если заголовок в JSON формате, извлекаем его
        if isinstance(title, str):
            try:
                title_data = json.loads(title)
                title = title_data.get('title', title)
            except json.JSONDecodeError:
                pass  # Оставляем как есть, если это просто текст
        elif isinstance(title, dict):
            title = title.get('title', '')
            
        if not title:
            logger.error("Не удалось извлечь заголовок")
            return False
            
        # Получаем текущий проект
        project = await agent.project.read(agent.current_project.id)
        if not project:
            logger.error("Не найден текущий проект")
            return False
            
        # Обновляем название проекта через словарь с данными
        update_data = {
            "name": title,
            "description": project.description,  # Сохраняем текущее описание
            "metadata": project.metadata  # Сохраняем текущие метаданные
        }
        
        await agent.project.update(agent.current_project.id, update_data)
        
        print(f"✅ Название проекта обновлено: {title}")
        return True