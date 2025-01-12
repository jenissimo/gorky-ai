from .base import GorkyStage
import logging
from typing import Dict, Any
from cognistruct.utils.prompts import prompt_manager
import asyncio
import json

logger = logging.getLogger(__name__)

class PreferencesStage(GorkyStage):
    """Этап сбора предпочтений пользователя"""
    
    async def check_preferences_exist(self, agent) -> bool:
        """
        Проверяет, существуют ли уже предпочтения
        
        Args:
            agent: Ссылка на агента для доступа к хранилищу
            
        Returns:
            bool: True если предпочтения существуют, False в противном случае
        """
        try:
            preferences = await self.get_artefact(agent, "preferences")
            return preferences is not None
        except Exception:
            return False
            
    async def _ask_question(self, question, agent) -> Any:
        """
        Задает вопрос пользователю и обрабатывает ответ
        
        Args:
            question: Словарь с параметрами вопроса
            agent: Ссылка на агента для доступа к IO
            
        Returns:
            Any: Обработанный ответ пользователя или None если ввод отменен
        """
        try:
            # Запрашиваем ввод
            default = question.get("default", "")
            prompt = f"{question['text']}"
            if default:
                prompt += f"[{default}] "
            answer = input(prompt) or default
            
            # Если ответ пустой и вопрос опциональный
            if not answer and question.get("optional"):
                return None
                
            # Обрабатываем тип ответа
            if question.get("type") == "list":
                # Разбиваем строку на список по разделителю
                separator = question.get("separator", ",")
                items = [item.strip() for item in answer.split(separator) if item.strip()]
                return items
            else:
                # Возвращаем как есть для текстового типа
                return answer
                
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {str(e)}")
            return None
    
    async def process(self, db, llm, agent):
        """Собирает предпочтения пользователя через диалог"""
        try:
            # Проверяем, существуют ли уже предпочтения
            if await self.check_preferences_exist(agent):
                print("✓ Предпочтения уже собраны, пропускаем этап")
                return True
            
            # Загружаем опросник
            try:
                questionnaire = self.load_prompt("preferences.jinja2")
            except Exception as e:
                logger.error(f"Error loading prompt template preferences.jinja2: {str(e)}")
                return False
            
            if not questionnaire:
                logger.error("Не удалось загрузить опросник")
                return False
                
            # Преобразуем строку в JSON
            try:
                questionnaire = json.loads(questionnaire)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при разборе опросника: {e}")
                return False
                
            # Собираем ответы пользователя
            preferences = {}
            
            # Выводим приветственное сообщение
            print(f"\n{questionnaire['welcome_message']}\n")
            
            # Проходим по всем секциям
            for section_id, section in questionnaire["sections"].items():
                print(f"\n{section['title']}")
                
                if section.get("type") == "choice":
                    # Выводим опции
                    for i, option in enumerate(section["options"], 1):
                        print(f"{i}. {option['text']}")
                    
                    # Запрашиваем выбор
                    default = section.get("default", "1")
                    prompt = f"{section['text']}"
                    if default:
                        prompt += f"[{default}] "
                    choice = input(prompt) or default
                    
                    # Находим выбранную опцию
                    try:
                        choice_num = int(choice)
                        selected_option = section["options"][choice_num - 1]
                        preferences[section_id] = {
                            "type": selected_option["id"],
                            "chapters": int(selected_option["value"])
                        }
                    except (ValueError, IndexError):
                        print("⚠️ Некорректный выбор, используем значение по умолчанию")
                        default_option = section["options"][int(default) - 1]
                        preferences[section_id] = {
                            "type": default_option["id"],
                            "chapters": int(default_option["value"])
                        }
                else:
                    # Обрабатываем обычные вопросы
                    section_data = {}
                    for question in section.get("questions", []):
                        answer = await self._ask_question(question, agent)
                        if answer is None:  # Пользователь отменил ввод
                            return False
                        section_data[question["id"]] = answer
                    preferences[section_id] = section_data
            
            # Выводим итоговые предпочтения
            print("\n📋 Итоговые предпочтения:")
            print(json.dumps(preferences, indent=2, ensure_ascii=False))
            print()
            
            # Сохраняем предпочтения
            return await self.set_artefact(agent, "preferences", preferences)
            
        except Exception as e:
            logger.error(f"Ошибка при сборе предпочтений: {str(e)}")
            return False
        