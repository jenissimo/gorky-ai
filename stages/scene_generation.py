from .base import GorkyStage
import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SceneGenerationStage(GorkyStage):
    """Этап генерации и редактирования сцен"""
    
    def __init__(self, iterations: int = 3):
        """
        Args:
            iterations: Количество итераций редактирования каждой сцены
        """
        super().__init__()
        self.iterations = iterations
        
    async def get_scene_version(self, agent, chapter_num: int, scene_num: int) -> int:
        """
        Получает номер версии последней редакции сцены
        
        Args:
            agent: Ссылка на агента для доступа к хранилищу
            chapter_num: Номер главы
            scene_num: Номер сцены
            
        Returns:
            int: Номер версии (0 если сцена не существует)
        """
        try:
            # Формируем ключ сцены
            scene_key = self.get_book_path(agent, f"chapter{chapter_num}/scene{scene_num}")
            
            # Получаем последний артефакт
            latest = await agent.storage.read(scene_key)
            
            if not latest:
                return 0
                
            # Возвращаем версию артефакта
            return latest.get("version", 0)
            
        except Exception as e:
            logger.error(f"Ошибка при получении версии сцены: {str(e)}")
            return 0

    async def get_previous_scene(self, agent, story_structure: dict, chapter_number: int, scene_number: int) -> tuple[str, dict]:
        """
        Получает текст и информацию о предыдущей сцене
        
        Args:
            agent: Ссылка на агента
            story_structure: Структура истории
            chapter_number: Номер текущей главы
            scene_number: Номер текущей сцены
            
        Returns:
            tuple[str, dict]: (текст предыдущей сцены, информация о предыдущей сцене)
        """
        try:
            # Если это первая сцена первой главы
            if chapter_number == 1 and scene_number == 1:
                return None, None
                
            # Если это первая сцена главы
            if scene_number == 1:
                prev_chapter = next(
                    (ch for ch in story_structure['chapters'] if ch['number'] == chapter_number - 1),
                    None
                )
                if prev_chapter:
                    prev_scene = prev_chapter['scenes'][-1]  # Последняя сцена предыдущей главы
                    scene_key = f"chapter{chapter_number-1}/scene{prev_scene['number']}"
            else:
                current_chapter = next(
                    (ch for ch in story_structure['chapters'] if ch['number'] == chapter_number),
                    None
                )
                if current_chapter:
                    prev_scene = next(
                        (sc for sc in current_chapter['scenes'] if sc['number'] == scene_number - 1),
                        None
                    )
                    if prev_scene:
                        scene_key = f"chapter{chapter_number}/scene{scene_number-1}"
                    else:
                        return None, None
                else:
                    return None, None
            
            if prev_scene:
                prev_scene_text = await self.get_artefact(agent, scene_key)
                if isinstance(prev_scene_text, str):
                    try:
                        prev_scene_text = json.loads(prev_scene_text)
                        prev_scene_text = prev_scene_text.get('scene_text', '')
                    except json.JSONDecodeError:
                        pass
                
                prev_scene_info = {
                    'title': prev_scene['title'],
                    'description': prev_scene['description'],
                    'characters': prev_scene['characters'],
                    'location': prev_scene['location'],
                    'time': prev_scene['time'],
                    'dramatic_info': prev_scene['dramatic_info']
                }
                return prev_scene_text, prev_scene_info
                
        except Exception as e:
            logger.error(f"Ошибка при получении предыдущей сцены: {e}")
        
        return None, None

    async def process(self, db, llm, agent):
        """Генерирует и редактирует все сцены книги"""
        try:
            # Получаем необходимые артефакты
            story_structure = await self.get_artefact(agent, "story_structure")
            characters = await self.get_artefact(agent, "characters")
            story_outline = await self.get_artefact(agent, "story_outline")
            
            if not all([story_structure, characters, story_outline]):
                logger.error("Не найдены необходимые артефакты")
                return False
            
            # Преобразуем в словари если нужно
            if isinstance(story_structure, str):
                story_structure = json.loads(story_structure)
            if isinstance(characters, str):
                characters = json.loads(characters)
            if isinstance(story_outline, str):
                story_outline = json.loads(story_outline)
            
            # Проходим по всем главам и сценам из story_structure
            for chapter in story_structure['chapters']:
                print(f"\n📖 Глава {chapter['number']}/{len(story_structure['chapters'])} {chapter['title']}")
                
                for scene in chapter['scenes']:
                    print(f"\n🎬 Сцена {scene['number']}/{len(chapter['scenes'])} {scene['title']}")
                    
                    # Проверяем версию сцены
                    version = await self.get_scene_version(agent, chapter['number'], scene['number'])
                    
                    # Если версий нет - генерируем с нуля
                    if version == 0:
                        print("✍️ Генерация текста...")
                        
                        # Получаем предыдущую сцену
                        prev_scene_text, prev_scene_info = await self.get_previous_scene(
                            agent, 
                            story_structure, 
                            chapter['number'], 
                            scene['number']
                        )
                        
                        prompt = self.load_prompt("scene_generation.jinja2",
                            params={
                                'scene': scene,
                                'chapter': chapter,
                                'characters': characters,
                                'story_structure': story_structure,
                                'story_outline': story_outline,  # Передаем для контекста
                                'prev_scene_text': prev_scene_text,
                                'prev_scene_info': prev_scene_info,
                                'target_word_count': 1500  # TODO: сделать настраиваемым
                            }
                        )
                        
                        messages = [{"role": "user", "content": prompt}]
                        scene_text = await self.show_spinner(
                            "Генерация текста сцены",
                            llm.generate_response(
                                messages
                            )
                        )
                        
                        if not scene_text:
                            logger.error(f"Не удалось сгенерировать сцену {chapter['number']}/{scene['number']}")
                            continue
                            
                        # Получаем текст из LLMResponse
                        scene_text = scene_text.content
                        
                        print("\n📄 Сгенерированный текст:")
                        print("=" * 80)
                        print(scene_text)
                        print("=" * 80)
                        
                        # Сохраняем первичный текст
                        await self.set_artefact(
                            agent,
                            f"chapter{chapter['number']}/scene{scene['number']}",
                            scene_text,
                            prompt
                        )
                        version = 1
                    
                    # Если версий меньше чем нужно итераций - продолжаем редактировать
                    if version <= self.iterations:
                        # Получаем последнюю версию текста
                        current_text = await self.get_artefact(agent, f"chapter{chapter['number']}/scene{scene['number']}")
                        
                        # Продолжаем редактирование с текущей версии
                        for i in range(version - 1, self.iterations):
                            print(f"📝 Итерация редактирования {i+1}/{self.iterations}...")
                            
                            prompt = self.load_prompt("editing.jinja2",
                                params={
                                    'text': current_text,
                                    'scene': scene,
                                    'chapter': chapter,
                                    'characters': characters,
                                    'prev_scene_text': prev_scene_text,
                                    'prev_scene_info': prev_scene_info,
                                    'iteration': i+1
                                }
                            )
                            
                            messages = [{"role": "user", "content": prompt}]
                            edited_text = await self.show_spinner(
                                f"Редактирование (итерация {i+1}/{self.iterations})",
                                llm.generate_response(
                                    messages
                                )
                            )
                            
                            if not edited_text:
                                logger.error(f"Не удалось отредактировать сцену {chapter['number']}/{scene['number']} на итерации {i+1}")
                                continue
                                
                            # Получаем текст из LLMResponse
                            edited_text = edited_text.content
                            
                            print(f"\n📄 Текст после редактирования (итерация {i+1}):")
                            print("=" * 80)
                            print(edited_text)
                            print("=" * 80)
                            
                            current_text = edited_text
                            
                            # Сохраняем новую версию текста
                            await self.set_artefact(
                                agent,
                                f"chapter{chapter['number']}/scene{scene['number']}",
                                edited_text,
                                prompt
                            )
                        
                        print(f"✅ Сцена {chapter['number']}/{scene['number']} завершена")
                    else:
                        print(f"✓ Сцена {chapter['number']}/{scene['number']} уже отредактирована {version-1} раз(а), пропускаем")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при генерации сцен: {str(e)}")
            return False 