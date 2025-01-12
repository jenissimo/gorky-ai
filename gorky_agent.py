import sys
import os
import logging
import json
import asyncio
import threading
import uvicorn
from pathlib import Path
from functools import partial
from typing import Optional, Dict, Any

from cognistruct import BaseAgent
from cognistruct.plugins.storage.versioned.plugin import VersionedStoragePlugin
from cognistruct.plugins.storage.project.plugin import ProjectStoragePlugin
from cognistruct.llm import LLMRouter
from cognistruct.utils import Config
from cognistruct.utils.prompts import prompt_manager
from cognistruct.utils.pipeline import StageChain
from stages.preferences import PreferencesStage
from stages.prompt_generation import PromptGenerationStage
from stages.scene_generation import SceneGenerationStage
from stages.book_assembly import BookAssemblyStage
from stages.update_title import UpdateProjectTitleStage
from commands import CommandHandler
from web.server import app

logger = logging.getLogger(__name__)

# Добавляем директорию с промптами проекта
project_prompts = os.path.join(Path(__file__).parent, "prompts")
if os.path.exists(project_prompts):
    prompt_manager.add_prompt_dir(project_prompts)

# Системный промпт для агента
SYSTEM_PROMPT = """
Ты профессоральный писатель.
""".strip()

def run_web_server():
    """Запускает веб-сервер в отдельном потоке"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def create_agent(llm_service="deepseek"):
    """Создает и возвращает настроенный экземпляр BaseAgent"""
    # Конфигурация LLM
    llm_config = {
        "provider": llm_service,
        "model": "deepseek-chat",
        "api_key": Config.load().deepseek_api_key,
        "temperature": 0.7
    }
    
    # Инициализируем LLM
    llm = LLMRouter().create_instance(**llm_config)
    
    # Создаем базового агента
    agent = BaseAgent(llm=llm, auto_load_plugins=False)
    
    # Создаем плагины
    storage = VersionedStoragePlugin()
    project = ProjectStoragePlugin()
    
    # Создаем цепочку этапов
    pipeline = StageChain([
        # 1. Этап сбора предпочтений (интерактивный)
        PreferencesStage(),
        
        # 2. Этап генерации Creative Brief
        PromptGenerationStage(
            prompt_name="creative_brief.jinja2",
            artifact_name="creative_brief",
            required_artifacts=["preferences"]
        ),
        
        # 3. Этап генерации названия
        PromptGenerationStage(
            prompt_name="title_generation.jinja2",
            artifact_name="title",
            required_artifacts=["creative_brief"]
        ),
        
        # 4. Этап обновления названия проекта
        UpdateProjectTitleStage(),
        
        # 5. Этап генерации Story Outline
        PromptGenerationStage(
            prompt_name="story_outline.jinja2",
            artifact_name="story_outline",
            required_artifacts=["creative_brief", "title"]
        ),
        
        # 6. Этап генерации Story Structure
        PromptGenerationStage(
            prompt_name="story_structure.jinja2",
            artifact_name="story_structure",
            required_artifacts=["story_outline", "creative_brief"]
        ),
        
        # 7. Этап генерации Character Sheets
        PromptGenerationStage(
            prompt_name="character_sheet.jinja2",
            artifact_name="characters",
            required_artifacts=["story_outline", "story_structure"]
        ),
        
        # 8. Этап генерации и редактирования сцен
        SceneGenerationStage(iterations=2),
        
        # 9. Этап финальной сборки книги
        BookAssemblyStage()
    ])
    
    # Добавляем необходимые атрибуты агенту
    agent.storage = storage
    agent.project = project
    agent.current_project = None
    agent.pipeline = pipeline
    
    # Добавляем метод generate_book
    async def generate_book(start_stage=1):
        """Генерирует книгу, начиная с указанного этапа"""
        try:
            # Запускаем пайплайн
            success = await pipeline.run(None, llm, agent)
            if not success:
                logger.error("Пайплайн завершился с ошибкой")
                return False
            return True
        except Exception as e:
            logger.error(f"Ошибка при генерации книги: {e}")
            return False
            
    agent.generate_book = generate_book
    
    # Создаем обработчик команд
    command_handler = CommandHandler(agent)
    agent.command_handler = command_handler
    
    return agent, storage, project, pipeline, command_handler

async def main():
    """Точка входа"""
    try:
        # Создаем директорию для данных
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Создаем агента и компоненты
        agent, storage, project, pipeline, command_handler = create_agent()
        
        # Инициализируем плагины
        await storage.setup()
        await project.setup()
        
        # Регистрируем плагины
        agent.plugin_manager.register_plugin("storage", storage)
        agent.plugin_manager.register_plugin("project", project)
        
        # Запускаем веб-сервер в отдельном потоке
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        print("🌐 Веб-интерфейс доступен по адресу http://localhost:8000")
        
        # Запускаем агента
        await agent.start()
        
        # Выводим приветствие
        intro = f"""
{"="*50}
🤖 Горький AI - генератор книг
{"="*50}

👋 Добро пожаловать в систему генерации книг!
🧠 Используется модель: {agent.llm.provider.name}/{agent.llm.provider.model}

📝 Как начать:
1. Создайте новую книгу: /new <название>
2. Или откройте существующую: /open <id>
3. Запустите генерацию: /start

🌐 Веб-интерфейс: http://localhost:8000

❓ Введите /help для просмотра всех команд
{"="*50}
"""
        print(intro)
        
        # Основной цикл обработки команд
        while True:
            try:
                user_input = input("👤 ").strip()
                
                if user_input.lower() == "exit":
                    print("\n👋 До свидания!")
                    break
                    
                await command_handler.handle_command(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Работа прервана пользователем")
                break
            
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {str(e)}")
        raise
    finally:
        if 'agent' in locals():
            await agent.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Работа прервана пользователем")
