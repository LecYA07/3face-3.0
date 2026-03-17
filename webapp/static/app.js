/**
 * 3FACE Telegram Mini App
 * Premium Design Edition
 */

// SVG Icons
const Icons = {
    match: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 6L18 18M6 18L18 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="6" cy="6" r="2" fill="currentColor"/>
        <circle cx="18" cy="6" r="2" fill="currentColor"/>
        <circle cx="6" cy="18" r="2" fill="currentColor"/>
        <circle cx="18" cy="18" r="2" fill="currentColor"/>
    </svg>`,
    map: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 6L9 3L15 6L21 3V18L15 21L9 18L3 21V6Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
        <path d="M9 3V18M15 6V21" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    score: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
        <path d="M3 9H21M9 3V21" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    calendar: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
        <path d="M3 10H21M8 2V6M16 2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
    star: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor"/>
    </svg>`,
    ticket: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M22 6L12 13L2 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    question: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <path d="M9 9C9 7.34 10.34 6 12 6C13.66 6 15 7.34 15 9C15 10.31 14.17 11.42 13 11.83V13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="17" r="1" fill="currentColor"/>
    </svg>`,
    report: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 9V13M12 17H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M10.29 3.86L1.82 18C1.64 18.31 1.55 18.67 1.55 19.04C1.56 19.4 1.66 19.76 1.84 20.07C2.02 20.38 2.28 20.64 2.59 20.82C2.9 21 3.25 21.09 3.62 21.09H20.56C20.93 21.09 21.28 21 21.59 20.82C21.9 20.64 22.16 20.38 22.34 20.07C22.52 19.76 22.62 19.4 22.63 19.04C22.63 18.67 22.54 18.31 22.36 18L13.89 3.86C13.71 3.56 13.45 3.31 13.15 3.13C12.84 2.96 12.5 2.87 12.15 2.87C11.79 2.87 11.45 2.96 11.14 3.13C10.84 3.31 10.58 3.56 10.4 3.86H10.29Z" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    bug: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 8V7C8 4.79 9.79 3 12 3C14.21 3 16 4.79 16 7V8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <rect x="5" y="8" width="14" height="13" rx="4" stroke="currentColor" stroke-width="2"/>
        <path d="M5 11H2M5 17H2M19 11H22M19 17H22M12 8V21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
    suggestion: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C8.13 2 5 5.13 5 9C5 11.38 6.19 13.47 8 14.74V17C8 17.55 8.45 18 9 18H15C15.55 18 16 17.55 16 17V14.74C17.81 13.47 19 11.38 19 9C19 5.13 15.87 2 12 2Z" stroke="currentColor" stroke-width="2"/>
        <path d="M9 21H15M12 18V21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
    message: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 11.5C21 16.19 16.97 20 12 20C10.64 20 9.35 19.72 8.19 19.22L3 21L4.78 15.81C4.28 14.65 4 13.36 4 12C4 7.03 7.81 3 12.5 3C16.97 3 20.65 6.47 21 10.88" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
    gamepad: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="6" width="20" height="12" rx="3" stroke="currentColor" stroke-width="2"/>
        <path d="M6 10V14M4 12H8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <circle cx="16" cy="10" r="1" fill="currentColor"/>
        <circle cx="19" cy="12" r="1" fill="currentColor"/>
    </svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <path d="M15 9L9 15M9 9L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`
};

// Telegram WebApp API (с поддержкой тестирования в браузере)
const tg = window.Telegram?.WebApp || createMockTelegramWebApp();

// Режим тестирования в браузере (без Telegram)
const isTestMode = !window.Telegram?.WebApp;

// State
let currentUser = null;
let matches = [];
let tickets = [];
let matchesOffset = 0;
const MATCHES_LIMIT = 20;

/**
 * Создать мок Telegram WebApp для тестирования в браузере
 */
function createMockTelegramWebApp() {
    console.log('[3FACE] Running in TEST MODE (browser)');
    
    return {
        ready: () => console.log('[3FACE] Mock: ready()'),
        expand: () => console.log('[3FACE] Mock: expand()'),
        initData: '',
        initDataUnsafe: {
            user: {
                id: 123456789,
                first_name: 'Test',
                last_name: 'User',
                username: 'testuser'
            }
        },
        themeParams: {
            bg_color: '#0f0f12',
            text_color: '#f4f4f5',
            hint_color: '#71717a',
            link_color: '#c77dff',
            button_color: '#5a189a',
            button_text_color: '#ffffff',
            secondary_bg_color: '#18181b'
        },
        HapticFeedback: {
            impactOccurred: (style) => console.log(`[3FACE] Haptic: ${style}`),
            notificationOccurred: (type) => console.log(`[3FACE] Haptic notification: ${type}`)
        }
    };
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Telegram WebApp
    tg.ready();
    tg.expand();
    
    // Show test mode banner if in browser
    if (isTestMode) {
        showTestModeBanner();
    }
    
    // Apply Telegram theme
    applyTelegramTheme();
    
    // Setup navigation
    setupNavigation();
    
    // Setup modals
    setupModals();
    
    // Setup forms
    setupForms();
    
    // Load initial data
    loadUserData();
    loadMatches();
});

/**
 * Показать баннер тестового режима
 */
function showTestModeBanner() {
    const banner = document.createElement('div');
    banner.className = 'test-banner';
    banner.textContent = 'ТЕСТОВЫЙ РЕЖИМ — Данные демонстрационные';
    document.body.prepend(banner);
    document.body.style.paddingTop = '32px';
}

// Apply Telegram theme colors
function applyTelegramTheme() {
    const root = document.documentElement;
    
    if (tg.themeParams) {
        if (tg.themeParams.bg_color) {
            root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color);
        }
        if (tg.themeParams.text_color) {
            root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color);
        }
        if (tg.themeParams.hint_color) {
            root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color);
        }
        if (tg.themeParams.link_color) {
            root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color);
        }
        if (tg.themeParams.button_color) {
            root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color);
        }
        if (tg.themeParams.button_text_color) {
            root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color);
        }
        if (tg.themeParams.secondary_bg_color) {
            root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color);
        }
    }
}

// Navigation
function setupNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Update content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabId}-tab`).classList.add('active');
            
            // Load data for tab
            if (tabId === 'support' && tickets.length === 0) {
                loadTickets();
            }
            
            // Haptic feedback
            tg.HapticFeedback.impactOccurred('light');
        });
    });
}

// Modals
function setupModals() {
    // New Ticket Modal
    document.getElementById('newTicketBtn').addEventListener('click', () => {
        openModal('newTicketModal');
    });
    
    document.getElementById('closeModal').addEventListener('click', () => {
        closeModal('newTicketModal');
    });
    
    // Match Modal
    document.getElementById('closeMatchModal').addEventListener('click', () => {
        closeModal('matchModal');
    });
    
    // Ticket Modal
    document.getElementById('closeTicketModal').addEventListener('click', () => {
        closeModal('ticketModal');
    });
    
    // Close on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
    tg.HapticFeedback.impactOccurred('light');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Forms
function setupForms() {
    // Ticket form
    const ticketForm = document.getElementById('ticketForm');
    const messageTextarea = ticketForm.querySelector('textarea[name="message"]');
    const charCount = document.getElementById('charCount');
    
    messageTextarea.addEventListener('input', () => {
        charCount.textContent = messageTextarea.value.length;
    });
    
    ticketForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(ticketForm);
        const data = {
            type: formData.get('type'),
            message: formData.get('message')
        };
        
        try {
            const response = await apiRequest('/api/tickets', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            if (response.ticket_id) {
                showToast('Тикет успешно создан', 'success');
                closeModal('newTicketModal');
                ticketForm.reset();
                charCount.textContent = '0';
                loadTickets();
                tg.HapticFeedback.notificationOccurred('success');
            }
        } catch (error) {
            showToast(error.message || 'Ошибка создания тикета', 'error');
            tg.HapticFeedback.notificationOccurred('error');
        }
    });
    
    // Load more matches
    document.getElementById('loadMoreMatches').addEventListener('click', () => {
        loadMatches(true);
    });
}

// API
async function apiRequest(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': tg.initData
    };
    
    const response = await fetch(url, {
        ...options,
        headers: {
            ...headers,
            ...options.headers
        }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'API Error');
    }
    
    return data;
}

// Load User Data
async function loadUserData() {
    try {
        const user = await apiRequest('/api/user');
        currentUser = user;
        
        document.getElementById('ratingValue').textContent = user.rating || 1000;
    } catch (error) {
        console.error('[3FACE] Failed to load user:', error);
    }
}

// Load Matches
async function loadMatches(loadMore = false) {
    const matchesList = document.getElementById('matchesList');
    const loadMoreBtn = document.getElementById('loadMoreMatches');
    
    if (!loadMore) {
        matchesList.innerHTML = '<div class="loading">Загрузка...</div>';
        matchesOffset = 0;
        matches = [];
    }
    
    try {
        const data = await apiRequest(`/api/matches?limit=${MATCHES_LIMIT}&offset=${matchesOffset}`);
        
        if (data.matches.length === 0 && matches.length === 0) {
            matchesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">${Icons.gamepad}</div>
                    <p>У вас пока нет сыгранных матчей</p>
                </div>
            `;
            loadMoreBtn.style.display = 'none';
            return;
        }
        
        matches = [...matches, ...data.matches];
        matchesOffset += data.matches.length;
        
        if (!loadMore) {
            matchesList.innerHTML = '';
        }
        
        data.matches.forEach(match => {
            matchesList.appendChild(createMatchCard(match));
        });
        
        loadMoreBtn.style.display = data.matches.length >= MATCHES_LIMIT ? 'block' : 'none';
        
    } catch (error) {
        console.error('[3FACE] Failed to load matches:', error);
        if (!loadMore) {
            matchesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">${Icons.error}</div>
                    <p>Не удалось загрузить матчи</p>
                </div>
            `;
        }
    }
}

// Create Match Card
function createMatchCard(match) {
    const isWin = match.winner_team === match.team;
    const card = document.createElement('div');
    card.className = `match-card ${isWin ? 'win' : 'loss'}`;
    
    const ratingChange = match.rating_change || 0;
    const ratingClass = ratingChange >= 0 ? 'positive' : 'negative';
    const ratingSign = ratingChange >= 0 ? '+' : '';
    
    card.innerHTML = `
        <div class="match-header">
            <span class="match-id">
                <span class="match-id-icon">${Icons.match}</span>
                Матч #${match.match_id}
            </span>
            <span class="match-result ${isWin ? 'win' : 'loss'}">${isWin ? 'Победа' : 'Поражение'}</span>
        </div>
        <div class="match-info">
            <span class="match-info-item">
                ${Icons.map}
                ${match.map_name}
            </span>
            <span class="match-info-item">
                ${Icons.score}
                ${match.team1_score}:${match.team2_score}
            </span>
        </div>
        <div class="match-stats">
            <div class="stat">
                <div class="stat-value">${match.kills || 0}</div>
                <div class="stat-label">Убийства</div>
            </div>
            <div class="stat">
                <div class="stat-value">${match.deaths || 0}</div>
                <div class="stat-label">Смерти</div>
            </div>
            <div class="stat">
                <div class="stat-value">${match.assists || 0}</div>
                <div class="stat-label">Ассисты</div>
            </div>
            <div class="stat">
                <div class="stat-value ${ratingClass}">${ratingSign}${ratingChange}</div>
                <div class="stat-label">Рейтинг</div>
            </div>
        </div>
        ${match.is_mvp ? `<div class="mvp-badge">${Icons.star} MVP матча</div>` : ''}
    `;
    
    card.addEventListener('click', () => {
        openMatchDetails(match.match_id);
    });
    
    return card;
}

// Open Match Details
async function openMatchDetails(matchId) {
    const modal = document.getElementById('matchModal');
    const titleText = document.querySelector('.match-modal-title-text');
    const details = document.getElementById('matchDetails');
    
    titleText.textContent = `Матч #${matchId}`;
    details.innerHTML = '<div class="loading">Загрузка...</div>';
    openModal('matchModal');
    
    try {
        const match = await apiRequest(`/api/match/${matchId}`);
        
        const team1Players = match.players.filter(p => p.team === 1);
        const team2Players = match.players.filter(p => p.team === 2);
        
        const userId = currentUser?.user_id || tg.initDataUnsafe?.user?.id;
        
        details.innerHTML = `
            <div class="match-details-header">
                <div class="match-meta">
                    <span class="match-meta-item">
                        ${Icons.map}
                        ${match.map_name}
                    </span>
                    <span class="match-meta-item">
                        ${Icons.calendar}
                        ${formatDate(match.finished_at || match.created_at)}
                    </span>
                </div>
                <div class="match-score">
                    <span class="team1-score">${match.team1_score}</span>
                    <span class="separator">:</span>
                    <span class="team2-score">${match.team2_score}</span>
                </div>
            </div>
            
            <div class="team-section">
                <div class="team-header team1">
                    <span class="team-label">
                        <span class="team-indicator"></span>
                        Команда 1
                    </span>
                    <span>${match.team1_start_side}</span>
                </div>
                ${team1Players.map(p => createPlayerRow(p, userId)).join('')}
            </div>
            
            <div class="team-section">
                <div class="team-header team2">
                    <span class="team-label">
                        <span class="team-indicator"></span>
                        Команда 2
                    </span>
                    <span>${match.team2_start_side}</span>
                </div>
                ${team2Players.map(p => createPlayerRow(p, userId)).join('')}
            </div>
        `;
        
    } catch (error) {
        console.error('[3FACE] Failed to load match:', error);
        details.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">${Icons.error}</div>
                <p>Не удалось загрузить данные матча</p>
            </div>
        `;
    }
}

function createPlayerRow(player, currentUserId) {
    const isYou = player.user_id === currentUserId;
    const name = player.game_nickname || player.full_name || player.username || 'Игрок';
    const ratingChange = player.rating_change || 0;
    const ratingSign = ratingChange >= 0 ? '+' : '';
    const ratingClass = ratingChange >= 0 ? 'positive' : 'negative';
    
    return `
        <div class="player-row">
            <div class="player-name ${isYou ? 'is-you' : ''}">
                ${player.is_mvp ? `<span class="player-mvp">${Icons.star}</span>` : ''}
                ${name}
                ${isYou ? '<span class="player-you-badge">вы</span>' : ''}
            </div>
            <div class="player-stats">
                <span class="player-kda">${player.kills}/${player.deaths}/${player.assists}</span>
                <span class="player-rating-change ${ratingClass}">${ratingSign}${ratingChange}</span>
            </div>
        </div>
    `;
}

// Load Tickets
async function loadTickets() {
    const ticketsList = document.getElementById('ticketsList');
    ticketsList.innerHTML = '<div class="loading">Загрузка...</div>';
    
    try {
        const data = await apiRequest('/api/tickets');
        tickets = data.tickets;
        
        if (tickets.length === 0) {
            ticketsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">${Icons.message}</div>
                    <p>У вас пока нет обращений</p>
                </div>
            `;
            return;
        }
        
        ticketsList.innerHTML = '';
        tickets.forEach(ticket => {
            ticketsList.appendChild(createTicketCard(ticket));
        });
        
    } catch (error) {
        console.error('[3FACE] Failed to load tickets:', error);
        ticketsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">${Icons.error}</div>
                <p>Не удалось загрузить тикеты</p>
            </div>
        `;
    }
}

// Create Ticket Card
function createTicketCard(ticket) {
    const card = document.createElement('div');
    card.className = 'ticket-card';
    
    const typeIcons = {
        'question': Icons.question,
        'report': Icons.report,
        'bug': Icons.bug,
        'suggestion': Icons.suggestion
    };
    
    const typeLabels = {
        'question': 'Вопрос',
        'report': 'Жалоба',
        'bug': 'Баг',
        'suggestion': 'Предложение'
    };
    
    const statusLabels = {
        'open': 'Открыт',
        'answered': 'Отвечен',
        'closed': 'Закрыт'
    };
    
    card.innerHTML = `
        <div class="ticket-header">
            <span class="ticket-id">
                ${Icons.ticket}
                Тикет #${ticket.ticket_id}
            </span>
            <span class="ticket-status ${ticket.status}">${statusLabels[ticket.status] || ticket.status}</span>
        </div>
        <div class="ticket-type">
            ${typeIcons[ticket.ticket_type] || Icons.question}
            ${typeLabels[ticket.ticket_type] || ticket.ticket_type}
        </div>
        <div class="ticket-preview">${ticket.message}</div>
        <div class="ticket-date">${formatDate(ticket.created_at)}</div>
    `;
    
    card.addEventListener('click', () => {
        openTicketDetails(ticket);
    });
    
    return card;
}

// Open Ticket Details
function openTicketDetails(ticket) {
    const modal = document.getElementById('ticketModal');
    const titleText = document.querySelector('.ticket-modal-title-text');
    const details = document.getElementById('ticketDetails');
    
    const typeIcons = {
        'question': Icons.question,
        'report': Icons.report,
        'bug': Icons.bug,
        'suggestion': Icons.suggestion
    };
    
    const typeLabels = {
        'question': 'Вопрос',
        'report': 'Жалоба',
        'bug': 'Баг',
        'suggestion': 'Предложение'
    };
    
    const statusLabels = {
        'open': 'Открыт',
        'answered': 'Отвечен',
        'closed': 'Закрыт'
    };
    
    titleText.textContent = `Тикет #${ticket.ticket_id}`;
    
    let html = `
        <div class="ticket-message-section">
            <h4>${typeLabels[ticket.ticket_type] || ticket.ticket_type} — ${statusLabels[ticket.status]}</h4>
            <div class="ticket-message">${ticket.message}</div>
            <div class="ticket-date">${formatDate(ticket.created_at)}</div>
        </div>
    `;
    
    if (ticket.admin_response) {
        const adminName = ticket.admin_name || ticket.admin_username || 'Администратор';
        html += `
            <div class="ticket-message-section">
                <h4>Ответ</h4>
                <div class="ticket-admin-name">От: ${adminName}</div>
                <div class="ticket-message ticket-response">${ticket.admin_response}</div>
            </div>
        `;
    }
    
    details.innerHTML = html;
    openModal('ticketModal');
}

// Utils
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 24 hours
    if (diff < 86400000) {
        return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
    
    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days} ${getDaysWord(days)} назад`;
    }
    
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

function getDaysWord(days) {
    if (days === 1) return 'день';
    if (days >= 2 && days <= 4) return 'дня';
    return 'дней';
}

function showToast(message, type = '') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}
