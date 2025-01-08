# utils.py

from jinja2 import Template
import os
import logging
from config import PROMPTS_DIR, LOG_FILE

def load_prompt(template_name, **kwargs):
    template_path = os.path.join(PROMPTS_DIR, template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
        template = Template(template_content)
        return template.render(**kwargs)
    except Exception as e:
        print(f"Error loading prompt template {template_name}: {e}")
        return ""

def setup_logging():
    """
    Настраивает логирование для приложения
    """
    logging.basicConfig(
        filename=LOG_FILE,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Добавляем вывод в консоль
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
