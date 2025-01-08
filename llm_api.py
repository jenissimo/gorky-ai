# llm_api.py

import openai
import requests
from config import OPENAI_API_KEY, CLAUDE_API_KEY, OLLAMA_API_KEY, DEEPSEEK_API_KEY
import logging
import json
import time
from datetime import datetime
import os
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('llm_api')

# Классы исключений
class LLMAPIError(Exception):
    """Базовый класс для исключений LLM API"""
    pass

class APIConnectionError(LLMAPIError):
    """Ошибка подключения к API"""
    pass

class APIResponseError(LLMAPIError):
    """Ошибка в ответе от API"""
    pass

class InvalidAPIKeyError(LLMAPIError):
    """Ошибка аутентификации API ключа"""
    pass

class ConversationLogger:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.log_dir = os.path.join('output', 'llm_logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.session_file = os.path.join(self.log_dir, f'session_{self.session_id}.json')
        self.conversation_data = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'interactions': []
        }
        self._save_session()
    
    def _save_session(self):
        """Сохраняет текущее состояние сессии в файл"""
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_data, f, ensure_ascii=False, indent=2)
    
    def log_interaction(self, prompt, response, service_name, metadata=None):
        """
        Логирует одно взаимодействие с API
        
        Args:
            prompt: Текст запроса
            response: Ответ от API (может быть строкой или JSON)
            service_name: Название сервиса (deepseek, openai, etc)
            metadata: Дополнительные метаданные
        """
        # Подготавливаем response для сериализации
        if isinstance(response, (dict, list)):
            prepared_response = response
        else:
            prepared_response = str(response)
        
        # Создаем запись о взаимодействии
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'service': service_name,
            'prompt': str(prompt),
            'response': prepared_response,
            'response_type': type(response).__name__,
            'metadata': metadata or {}
        }
        
        # Добавляем взаимодействие в список
        self.conversation_data['interactions'].append(interaction)
        
        # Обновляем файл
        self._save_session()
        
        logger.debug(f"Добавлено новое взаимодействие в сессию {self.session_id}")

# Глобальный экземпляр логгера
conversation_logger = None

def get_conversation_logger():
    """Возвращает глобальный экземпляр логгера, создавая его при необходимости"""
    global conversation_logger
    if conversation_logger is None:
        conversation_logger = ConversationLogger()
    return conversation_logger

class LLMAPI:
    def generate(self, prompt, temperature=0.7, max_tokens=1500, json_mode=False):
        # Логируем параметры запроса
        logger.debug(f"Параметры запроса:")
        logger.debug(f"temperature={temperature}")
        logger.debug(f"max_tokens={max_tokens}")
        logger.debug(f"json_mode={json_mode}")
        logger.debug("Контекст запроса:")
        logger.debug(f"{prompt[:1000]}...")  # Логируем первую 1000 символов промпта
        raise NotImplementedError

class OpenAIAPI(LLMAPI):
    def __init__(self):
        if not OPENAI_API_KEY:
            raise InvalidAPIKeyError("OpenAI API ключ не установлен")
        openai.api_key = OPENAI_API_KEY

    def generate(self, prompt, temperature=0.7, max_tokens=1500, json_mode=False):
        try:
            # Логируем параметры запроса
            logger.debug(f"OpenAI API параметры:")
            logger.debug(f"temperature={temperature}")
            logger.debug(f"max_tokens={max_tokens}")
            logger.debug(f"json_mode={json_mode}")
            logger.debug("Контекст запроса:")
            logger.debug(f"{prompt[:1000]}...")  # Логируем первую 1000 символов промпта

            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].text.strip()
        except openai.error.AuthenticationError:
            error_msg = "Неверный API ключ OpenAI"
            logging.error(error_msg)
            raise InvalidAPIKeyError(error_msg)
        except openai.error.APIConnectionError as e:
            error_msg = f"Ошибка подключения к OpenAI API: {str(e)}"
            logging.error(error_msg)
            raise APIConnectionError(error_msg)
        except openai.error.APIError as e:
            error_msg = f"Ошибка OpenAI API: {str(e)}"
            logging.error(error_msg)
            raise APIResponseError(error_msg)
        except Exception as e:
            error_msg = f"Неожиданная ошибка OpenAI API: {str(e)}"
            logging.error(error_msg)
            raise LLMAPIError(error_msg)

class DeepSeekAPI(LLMAPI):
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API ключ отсутствует")
            raise InvalidAPIKeyError("DeepSeek API ключ не установлен")
        self.api_key = DEEPSEEK_API_KEY
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"
        logger.info("DeepSeek API инициализирован")

    def generate(self, prompt, temperature=0.7, max_tokens=1500, json_mode=False):
        try:
            start_time = time.time()
            logger.info(f"Отправка запроса к DeepSeek API: температура={temperature}, max_tokens={max_tokens}, json_mode={json_mode}")
            logger.debug(f"Промпт: {prompt[:1000]}...")

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            # Добавляем формат JSON если требуется
            if json_mode:
                data['response_format'] = {'type': 'json_object'}
                # Добавляем системное сообщение для JSON
                data['messages'].insert(0, {
                    'role': 'system',
                    'content': 'Ты должен отвечать только в формате JSON. Не добавляй никаких пояснений или дополнительного текста.'
                })
            
            logger.debug(f"Ожидаем ответа от DeepSeek API...")
            response = requests.post(self.endpoint, json=data, headers=headers)
            
            if response.status_code == 401:
                logger.error("Ошибка аутентификации DeepSeek API")
                raise InvalidAPIKeyError("Неверный API ключ DeepSeek")
            response.raise_for_status()
            
            response_data = response.json()
            execution_time = time.time() - start_time
            
            # Логируем статистику запроса
            logger.info(f"Запрос выполнен успешно: время={execution_time:.2f}с, "
                       f"токены={response_data.get('usage', {}).get('total_tokens', 'N/A')}")
            
            result = response_data['choices'][0]['message']['content'].strip()
            logger.debug(f"Получен ответ: {result[:1000]}...")
            
            # Если включен JSON режим, проверяем валидность JSON
            if json_mode:
                try:
                    result = json.loads(result)
                    logger.debug("Ответ успешно распарсен как JSON")
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON ответа: {e}")
                    raise APIResponseError("Получен невалидный JSON")
            
            # Сохраняем пару запрос-ответ
            metadata = {
                'temperature': temperature,
                'max_tokens': max_tokens,
                'json_mode': json_mode,
                'execution_time': execution_time,
                'usage': response_data.get('usage', {}),
                'status_code': response.status_code
            }
            
            # Используем новый логгер для сохранения взаимодействия
            conversation_logger = get_conversation_logger()
            conversation_logger.log_interaction(prompt, result, 'deepseek', metadata)
            
            return result
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Ошибка подключения к DeepSeek API: {str(e)}"
            logger.error(error_msg)
            raise APIConnectionError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса к DeepSeek API: {str(e)}"
            logger.error(error_msg)
            raise APIResponseError(error_msg)
        except Exception as e:
            error_msg = f"Неожиданная ошибка DeepSeek API: {str(e)}"
            logger.error(error_msg)
            raise LLMAPIError(error_msg)

def get_llm_api(service_name):
    """Фабричный метод для создания экземпляра LLM API"""
    logger.info(f"Запрос на создание API клиента для сервиса: {service_name}")
    
    if service_name == "openai":
        api = OpenAIAPI()
        logger.info("OpenAI API инициализирован")
        return api
    elif service_name == "deepseek":
        api = DeepSeekAPI()
        logger.info("DeepSeek API инициализирован")
        return api
    else:
        error_msg = f"Неподдерживаемый LLM сервис: {service_name}"
        logger.error(error_msg)
        raise ValueError(error_msg)
