from .base import GorkyStage
import logging
import json
from typing import Dict, Any, List, Optional
from cognistruct.utils.prompts import prompt_manager

logger = logging.getLogger(__name__)

class PromptGenerationStage(GorkyStage):
    """Универсальный этап для генерации артефактов на основе промптов"""
    
    def __init__(self, prompt_name: str, artifact_name: str, required_artifacts: Optional[List[str]] = None):
        """
        Args:
            prompt_name: Имя файла промпта (например, 'creative_brief.jinja2')
            artifact_name: Имя генерируемого артефакта (например, 'creative_brief')
            required_artifacts: Список необходимых артефактов
        """
        super().__init__()
        self.prompt_name = prompt_name
        self.artifact_name = artifact_name
        self.required_artifacts = required_artifacts or []
        self.stage_name = artifact_name.replace('_', ' ').title()
        
    async def check_artifact_exists(self, agent) -> bool:
        """
        Проверяет, существует ли уже артефакт этого этапа
        
        Args:
            agent: Ссылка на агента для доступа к хранилищу
            
        Returns:
            bool: True если артефакт существует, False в противном случае
        """
        try:
            artifact = await self.get_artefact(agent, self.artifact_name)
            return artifact is not None
        except Exception:
            return False
        
    async def process(self, db, llm, agent) -> bool:
        """Генерирует артефакт на основе промпта"""
        try:
            # Проверяем, существует ли уже артефакт
            if await self.check_artifact_exists(agent):
                print(f"✓ Артефакт {self.artifact_name} уже существует")
                return True

            # Собираем контекст из предыдущих артефактов
            params = {}
            if self.required_artifacts:
                for artifact_name in self.required_artifacts:
                    artifact = await self.get_artefact(agent, artifact_name)
                    if not artifact:
                        print(f"⚠️ Не найден артефакт {artifact_name}")
                        return False
                    params[artifact_name] = artifact

            # Загружаем и рендерим промпт
            prompt = prompt_manager.load_prompt(
                self.prompt_name,
                params=params
            )
            if not prompt:
                print(f"⚠️ Не удалось загрузить промпт {self.prompt_name}")
                return False

            print(f"\nПромпт:\n{prompt}\n")

            # Генерируем ответ
            messages = [{"role": "user", "content": prompt}]
            response = await self.show_spinner(
                f"Генерация {self.artifact_name}",
                llm.generate_response(
                    messages,
                    response_format={"type": "json_object"}
                )
            )

            # Извлекаем контент и парсим JSON
            content = response.content
            print(f"\nОтвет LLM:\n{content}\n")

            if not content:
                print("⚠️ Получен пустой ответ от LLM")
                return False

            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"⚠️ Ошибка парсинга JSON: {str(e)}")
                print(f"Контент: {content}")
                return False

            # Сохраняем результат
            await self.set_artefact(agent, self.artifact_name, result, prompt)
            return True

        except Exception as e:
            print(f"⚠️ Ошибка при генерации {self.artifact_name}: {str(e)}")
            return False 