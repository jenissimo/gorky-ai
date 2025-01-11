class DbHandler {
    constructor(dropZoneId, fileInputId) {
        this.dropZone = document.getElementById(dropZoneId);
        this.fileInput = document.getElementById(fileInputId);
        this.artifactsList = document.getElementById('artifactsList');
        this.contentViewer = document.getElementById('contentViewer');
        this.contentTitle = document.getElementById('contentTitle');
        this.contentBody = document.getElementById('contentBody');
        this.dbInfo = document.getElementById('dbInfo');
        
        // Инициализируем SQL.js
        this.initSqlJs();
        this.initializeEventListeners();
    }
    
    async initSqlJs() {
        try {
            this.SQL = await initSqlJs({
                locateFile: filename => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/${filename}`
            });
        } catch (error) {
            console.error('Ошибка инициализации SQL.js:', error);
            alert('Ошибка инициализации SQL.js. Проверьте консоль для деталей.');
        }
    }
    
    initializeEventListeners() {
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });
        
        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('dragover');
        });
        
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) this.loadDatabase(file);
        });
        
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });
        
        this.fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.loadDatabase(file);
        });
    }
    
    async loadDatabase(file) {
        try {
            if (!this.SQL) {
                throw new Error('SQL.js не инициализирован');
            }
            
            const arrayBuffer = await file.arrayBuffer();
            const db = new this.SQL.Database(new Uint8Array(arrayBuffer));
            
            // Получаем информацию о базе данных
            const tables = this.getTables(db);
            const artifactsCount = this.getArtifactsCount(db);
            
            // Отображаем информацию о БД
            this.dbInfo.innerHTML = `
                <strong>Файл:</strong> ${file.name}<br>
                <strong>Размер:</strong> ${(file.size / 1024).toFixed(2)} KB<br>
                <strong>Таблицы:</strong> ${tables.join(', ')}<br>
                <strong>Артефактов:</strong> ${artifactsCount}
            `;
            
            // Отображаем список артефактов
            this.displayArtifacts(db);
            
        } catch (error) {
            console.error('Ошибка при загрузке базы данных:', error);
            alert('Ошибка при загрузке базы данных: ' + error.message);
        }
    }
    
    getTables(db) {
        const result = db.exec("SELECT name FROM sqlite_master WHERE type='table'");
        return result[0].values.map(row => row[0]);
    }
    
    getArtifactsCount(db) {
        const result = db.exec("SELECT COUNT(*) FROM artifacts");
        return result[0].values[0][0];
    }
    
    displayArtifacts(db) {
        const artifacts = db.exec(`
            WITH ranked_artifacts AS (
                SELECT 
                    step,
                    GROUP_CONCAT(content, '|||') as contents,
                    GROUP_CONCAT(created_at, '|||') as timestamps,
                    MIN(created_at) as first_created,
                    COUNT(*) as versions_count
                FROM artifacts 
                GROUP BY step
                ORDER BY first_created ASC
            )
            SELECT * FROM ranked_artifacts
        `);
        
        this.artifactsList.innerHTML = '';
        
        if (artifacts.length > 0) {
            artifacts[0].values.forEach(([step, contents, timestamps, firstCreated, versionsCount]) => {
                const card = document.createElement('div');
                card.className = 'artifact-card fade-in';
                
                // Разбираем сгруппированные данные
                const contentsList = contents.split('|||');
                const timestampsList = timestamps.split('|||');
                
                // Создаем массив данных с версиями на основе времени
                const sortedData = timestampsList.map((timestamp, idx) => ({
                    version: idx + 1,
                    content: contentsList[idx],
                    timestamp: timestamp,
                    created: new Date(timestamp)
                })).sort((a, b) => b.created - a.created); // Сортируем по времени создания
                
                // Форматируем дату первой версии
                const firstDate = new Date(firstCreated).toLocaleString();
                
                // Создаем список версий
                const versionsHtml = sortedData.map(({version, content, timestamp}) => `
                    <div class="version-item" data-version="${version}" data-content="${encodeURIComponent(content)}">
                        v${version} (${new Date(timestamp).toLocaleTimeString()})
                    </div>
                `).join('');
                
                card.innerHTML = `
                    <div class="artifact-header">
                        <div class="artifact-type">
                            ${step}
                            <span class="versions-count">(${versionsCount} версий)</span>
                        </div>
                        <div class="artifact-timestamp">${firstDate}</div>
                    </div>
                    <div class="versions-list">
                        ${versionsHtml}
                    </div>
                `;
                
                // Обработчик клика по карточке
                card.onclick = () => {
                    // Убираем выделение со всех карточек
                    document.querySelectorAll('.artifact-card').forEach(c => 
                        c.classList.remove('selected'));
                    // Выделяем текущую карточку
                    card.classList.add('selected');
                    
                    // Находим текущую активную версию или берем первую
                    const currentVersion = card.querySelector('.version-item.current') 
                        || card.querySelector('.version-item:first-child');
                    
                    if (currentVersion) {
                        // Убираем подсветку со всех версий
                        card.querySelectorAll('.version-item').forEach(v => 
                            v.classList.remove('current'));
                        // Подсвечиваем текущую версию
                        currentVersion.classList.add('current');
                        
                        const content = decodeURIComponent(currentVersion.dataset.content);
                        const version = currentVersion.dataset.version;
                        this.displayArtifactContent(step, content, firstDate, version);
                    }
                };
                
                // Обработчики для версий
                card.querySelectorAll('.version-item').forEach(item => {
                    item.onclick = (e) => {
                        e.stopPropagation(); // Предотвращаем всплытие события
                        
                        // Убираем подсветку со всех версий в этой карточке
                        card.querySelectorAll('.version-item').forEach(v => 
                            v.classList.remove('current'));
                        // Подсвечиваем текущую версию
                        item.classList.add('current');
                        
                        // Убираем выделение со всех карточек
                        document.querySelectorAll('.artifact-card').forEach(c => 
                            c.classList.remove('selected'));
                        // Выделяем текущую карточку
                        card.classList.add('selected');
                        
                        const content = decodeURIComponent(item.dataset.content);
                        const version = item.dataset.version;
                        this.displayArtifactContent(step, content, firstDate, version);
                    };
                });
                
                this.artifactsList.appendChild(card);
            });
            
            // Автоматически показываем первую карточку
            const firstCard = this.artifactsList.querySelector('.artifact-card');
            if (firstCard) {
                // Выделяем первую версию
                const firstVersion = firstCard.querySelector('.version-item:first-child');
                if (firstVersion) {
                    firstVersion.classList.add('current');
                }
                firstCard.click();
            }
        }
    }
    
    displayArtifactContent(step, content, timestamp, version) {
        this.contentViewer.style.display = 'block';
        this.contentTitle.textContent = `${step} v${version} (${timestamp})`;
        
        try {
            // Пробуем распарсить как JSON
            const jsonData = JSON.parse(content);
            this.contentBody.textContent = JSON.stringify(jsonData, null, 2);
        } catch {
            // Если не JSON, отображаем как есть
            this.contentBody.textContent = content;
        }
    }
} 