// Global variables
let map;
let markers = [];
let sessionId = generateSessionId();
let currentRecommendations = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    focusMessageInput();
});

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Initialize Leaflet map
function initializeMap() {
    // Initialize map centered on Vietnam
    map = L.map('map').setView([16.0583, 108.2772], 6);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add a marker for Vietnam center
    L.marker([16.0583, 108.2772])
        .addTo(map)
        .bindPopup('<b>Việt Nam</b><br>Chào mừng bạn đến với hệ thống tư vấn du lịch!')
        .openPopup();
}

// Focus on message input
function focusMessageInput() {
    document.getElementById('messageInput').focus();
}

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Send message to chatbot
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Clear input and show loading
    messageInput.value = '';
    showLoadingState(true);
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    try {
        // Send request to backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Add bot response to chat với style phù hợp
            addMessageToChat(data.response, 'bot', data.is_travel_related);

            // Update recommendations và map chỉ khi có gợi ý du lịch
            if (data.is_travel_related && data.has_recommendations) {
                updateRecommendations(data.recommendations);
                updateMap(data.recommendations);
            } else if (data.is_travel_related && !data.has_recommendations) {
                // Trường hợp liên quan du lịch nhưng không tìm được gợi ý
                clearRecommendations();
            } else {
                // Trường hợp không liên quan du lịch - hiển thị hướng dẫn
                showTravelGuidance();
            }
        } else {
            addMessageToChat('Xin lỗi, đã có lỗi xảy ra: ' + data.error, 'bot', false);
        }
        
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('Xin lỗi, không thể kết nối đến server. Vui lòng thử lại sau.', 'bot');
    } finally {
        showLoadingState(false);
        focusMessageInput();
    }
}

// Show/hide loading state
function showLoadingState(loading) {
    const sendButton = document.getElementById('sendButtonText');
    const spinner = document.getElementById('sendButtonSpinner');
    const messageInput = document.getElementById('messageInput');
    
    if (loading) {
        sendButton.classList.add('d-none');
        spinner.classList.remove('d-none');
        messageInput.disabled = true;
    } else {
        sendButton.classList.remove('d-none');
        spinner.classList.add('d-none');
        messageInput.disabled = false;
    }
}

// Add message to chat
function addMessageToChat(message, sender, isTravelRelated = true) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');

    // Thêm class phù hợp dựa trên loại message
    let messageClass = `message ${sender}-message`;
    if (sender === 'bot' && !isTravelRelated) {
        messageClass += ' refusal-message';
    }
    messageDiv.className = messageClass;

    const currentTime = new Date().toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    messageDiv.innerHTML = `
        <div class="message-content">
            <strong>${sender === 'user' ? 'Bạn' : 'Chatbot'}:</strong> ${message}
        </div>
        <div class="message-time">${currentTime}</div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update recommendations list
function updateRecommendations(recommendations) {
    currentRecommendations = recommendations;
    const recommendationsList = document.getElementById('recommendationsList');
    
    if (recommendations.length === 0) {
        recommendationsList.innerHTML = '<p class="text-muted">Không tìm thấy gợi ý phù hợp.</p>';
        return;
    }
    
    let html = '';
    recommendations.forEach((rec, index) => {
        html += `
            <div class="recommendation-item" onclick="selectRecommendation(${index})" data-index="${index}">
                <div class="recommendation-title">
                    ${rec.city}, ${rec.province}
                </div>
                <div class="recommendation-details">
                    ${rec.region} • ${rec.terrain} • Tháng ${rec.month}
                </div>
                <div class="weather-info">
                    <div class="weather-item">
                        <span class="weather-value">${rec.avgtemp_c.toFixed(1)}°C</span>
                        <span class="weather-label">Nhiệt độ</span>
                    </div>
                    <div class="weather-item">
                        <span class="weather-value">${rec.maxwind_kph.toFixed(1)}</span>
                        <span class="weather-label">Gió (km/h)</span>
                    </div>
                    <div class="weather-item">
                        <span class="weather-value">${rec.avghumidity.toFixed(0)}%</span>
                        <span class="weather-label">Độ ẩm</span>
                    </div>
                    <div class="weather-item">
                        <span class="weather-value">${rec.score.toFixed(2)}</span>
                        <span class="weather-label">Điểm</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    recommendationsList.innerHTML = html;
}

// Select a recommendation
function selectRecommendation(index) {
    // Remove active class from all items
    document.querySelectorAll('.recommendation-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to selected item
    const selectedItem = document.querySelector(`[data-index="${index}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Center map on selected location
    if (currentRecommendations[index]) {
        const rec = currentRecommendations[index];
        map.setView([rec.lat, rec.lon], 10);
        
        // Open popup for the selected marker
        markers.forEach((marker, i) => {
            if (i === index) {
                marker.openPopup();
            }
        });
    }
}

// Update map with recommendations
function updateMap(recommendations) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    if (recommendations.length === 0) {
        return;
    }
    
    // Add new markers
    recommendations.forEach((rec, index) => {
        const marker = L.marker([rec.lat, rec.lon])
            .addTo(map)
            .bindPopup(`
                <div class="popup-title">${rec.city}, ${rec.province}</div>
                <div class="popup-details">
                    <strong>Vùng:</strong> ${rec.region}<br>
                    <strong>Địa hình:</strong> ${rec.terrain}<br>
                    <strong>Tháng:</strong> ${rec.month}<br>
                    <strong>Nhiệt độ:</strong> ${rec.avgtemp_c.toFixed(1)}°C<br>
                    <strong>Gió:</strong> ${rec.maxwind_kph.toFixed(1)} km/h<br>
                    <strong>Độ ẩm:</strong> ${rec.avghumidity.toFixed(0)}%<br>
                    <strong>Điểm phù hợp:</strong> ${rec.score.toFixed(2)}/100
                </div>
            `);
        
        // Add click event to marker
        marker.on('click', function() {
            selectRecommendation(index);
        });
        
        markers.push(marker);
    });
    
    // Fit map to show all markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
    
    // Auto-select first recommendation
    if (recommendations.length > 0) {
        setTimeout(() => selectRecommendation(0), 500);
    }
}

// Clear map markers helper
function clearMapMarkers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
}

// Clear recommendations
function clearRecommendations() {
    document.getElementById('recommendationsList').innerHTML = '<p class="text-muted">Không tìm thấy gợi ý phù hợp với yêu cầu của bạn.</p>';
    clearMapMarkers();
}

// Show travel guidance for non-travel queries
function showTravelGuidance() {
    const examples = [
        "Tôi muốn đi biển miền Trung tháng 6",
        "Nơi nào mát mẻ vào mùa đông?",
        "Gợi ý địa điểm leo núi ở Tây Nguyên"
    ];

    document.getElementById('recommendationsList').innerHTML = `
        <div class="travel-guidance">
            <h6>Hướng dẫn sử dụng</h6>
            <p class="text-muted mb-2">Để nhận gợi ý du lịch, hãy hỏi về:</p>
            <ul class="guidance-list">
                <li>Địa điểm du lịch (biển, núi, thành phố)</li>
                <li>Thời tiết mong muốn</li>
                <li>Thời gian du lịch (tháng, mùa)</li>
                <li>Vùng miền (Bắc, Trung, Nam)</li>
            </ul>
            <div class="example-queries">
                <p class="mb-1"><strong>Ví dụ:</strong></p>
                ${examples.map(ex => `<div class="example-item" onclick="fillExampleQuery('${ex}')">"${ex}"</div>`).join('')}
            </div>
        </div>
    `;
    clearMapMarkers();
}

// Fill example query into input
function fillExampleQuery(query) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = query;
    messageInput.focus();
}
