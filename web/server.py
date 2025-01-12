from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional
import json
import os

from cognistruct.plugins.storage.versioned.plugin import VersionedStoragePlugin
from cognistruct.plugins.storage.project.plugin import ProjectStoragePlugin

app = FastAPI(title="Gorky AI Web Interface")

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Инициализируем шаблоны
templates = Jinja2Templates(directory="web/templates")

# Инициализируем хранилище
storage = VersionedStoragePlugin()
project_storage = ProjectStoragePlugin()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервера"""
    await storage.setup()
    await project_storage.setup()

def get_book_path(book_id: str, *parts: str) -> str:
    """
    Создает путь к артефакту книги
    
    Args:
        book_id: ID книги
        *parts: Дополнительные части пути (например, 'chapter1', 'scene1')
    """
    # Начинаем с ID книги
    path_parts = [("book", str(book_id))]
    
    # Добавляем остальные части
    for part in parts:
        if part.startswith('chapter'):
            num = part.replace('chapter', '')
            path_parts.append(('chapter', num))
        elif part.startswith('scene'):
            num = part.replace('scene', '')
            path_parts.append(('scene', num))
        else:
            path_parts.append(part)
            
    return storage.generate_hierarchical_id(*path_parts)

async def get_artifact_versions(book_id: str, artifact_path: str) -> List[Dict]:
    """Получает все версии артефакта"""
    full_path = get_book_path(book_id, artifact_path)
    artifact = await storage.read(full_path)
    if not artifact:
        return []
    # Создаем список версий из всех версий артефакта
    versions = []
    version = 1
    while True:
        version_data = await storage.read(full_path, version=version)
        if not version_data:
            break
        versions.append(version_data)
        version += 1
    return versions

async def get_latest_artifact(book_id: str, artifact_path: str) -> Optional[Dict]:
    """Получает последнюю версию артефакта"""
    full_path = get_book_path(book_id, artifact_path)
    return await storage.read(full_path)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница со списком книг"""
    books = []
    # Получаем список всех проектов через search_projects
    projects = await project_storage.search({})
    
    for project in projects:
        book_id = project.id  # Project это dataclass с полем id
        title = await get_latest_artifact(str(book_id), 'title')
        if title:
            books.append({
                'id': book_id,
                'title': title.get('value', {}).get('title', f'Книга {book_id}')
            })
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "books": books}
    )

@app.get("/book/{book_id}", response_class=HTMLResponse)
async def book_details(request: Request, book_id: str):
    """Страница с деталями книги"""
    # Получаем основные артефакты
    title = await get_latest_artifact(book_id, 'title')
    story_structure = await get_latest_artifact(book_id, 'story_structure')
    
    if not title or not story_structure:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Книга не найдена"}
        )
    
    # Собираем информацию о сценах
    scenes = []
    for chapter in story_structure.get('value', {}).get('chapters', []):
        for scene in chapter.get('scenes', []):
            scene_path = f"chapter{chapter['number']}/scene{scene['number']}"
            scene_versions = await get_artifact_versions(book_id, scene_path)
            scenes.append({
                'chapter': chapter['number'],
                'scene': scene['number'],
                'title': scene.get('title', ''),
                'versions': len(scene_versions)
            })
    
    return templates.TemplateResponse(
        "book.html",
        {
            "request": request,
            "book_id": book_id,
            "title": title.get('value', {}).get('title', ''),
            "scenes": scenes
        }
    )

@app.get("/book/{book_id}/scene/{chapter_num}/{scene_num}", response_class=HTMLResponse)
async def scene_versions(request: Request, book_id: str, chapter_num: int, scene_num: int):
    """Страница сравнения версий сцены"""
    # Получаем название книги для breadcrumbs
    title_artifact = await get_latest_artifact(book_id, 'title')
    if not title_artifact:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Книга не найдена"}
        )
    book_title = title_artifact.get('value', {}).get('title', f'Книга {book_id}')
    
    # Получаем версии сцены
    scene_path = f"chapter{chapter_num}/scene{scene_num}"
    versions = await get_artifact_versions(book_id, scene_path)
    
    if not versions:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Сцена не найдена"}
        )
    
    # Добавляем промпты к версиям
    for version in versions:
        version['prompt'] = version.get('metadata', {}).get('prompt', '')
    
    return templates.TemplateResponse(
        "scene_versions.html",
        {
            "request": request,
            "book_id": book_id,
            "title": book_title,  # Добавляем название книги
            "chapter_num": chapter_num,
            "scene_num": scene_num,
            "versions": versions
        }
    )

@app.get("/book/{book_id}/prompt/{artifact_path:path}", response_class=HTMLResponse)
async def prompt_response(request: Request, book_id: str, artifact_path: str):
    """Страница с промптом и ответом"""
    artifact = await get_latest_artifact(book_id, artifact_path)
    
    if not artifact:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Артефакт не найден"}
        )
    
    # Получаем значение ответа
    response = artifact.get('value', '')
    
    # Если ответ уже является строкой JSON, преобразуем его обратно в объект
    # чтобы избежать двойного экранирования
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            pass
    
    return templates.TemplateResponse(
        "prompt_response.html",
        {
            "request": request,
            "book_id": book_id,
            "artifact_path": artifact_path,
            "prompt": artifact.get('metadata', {}).get('prompt', ''),
            "response": json.dumps(response) if isinstance(response, (dict, list)) else response
        }
    ) 