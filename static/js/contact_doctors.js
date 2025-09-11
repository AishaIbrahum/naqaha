
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (message) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-sent';
        
        const currentTime = new Date().toLocaleTimeString('ar-SA', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div>${message}</div>
            <div class="message-time">${currentTime}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        input.value = '';
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Show typing indicator
        showTypingIndicator();
        
        // Simulate doctor response
        setTimeout(() => {
            hideTypingIndicator();
            addDoctorResponse();
        }, 2000);
    }
}

function showTypingIndicator() {
    document.getElementById('typingIndicator').style.display = 'flex';
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
    document.getElementById('typingIndicator').style.display = 'none';
}

function addDoctorResponse() {
    const responses = [
        'شكراً لك على هذه المعلومات، سأراجعها وأعطيك رأيي.',
        'أفهم ما تقولين، دعيني أسألك عن بعض التفاصيل الإضافية.',
        'هذا مفيد جداً، هل تشعرين بأي أعراض أخرى؟',
        'بناءً على ما ذكرتِ، أنصحك بإجراء بعض الفحوصات.'
    ];
    
    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-received';
    
    const currentTime = new Date().toLocaleTimeString('ar-SA', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    messageDiv.innerHTML = `
        <div>${randomResponse}</div>
        <div class="message-time">${currentTime}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function switchDoctor(element, doctorName) {
    // Remove active class from all doctor items
    document.querySelectorAll('.doctor-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to selected doctor
    element.classList.add('active');
    
    // Update chat header
    document.querySelector('.doctor-name').textContent = doctorName;
    document.querySelector('.doctor-avatar').textContent = doctorName.charAt(2);
    
    // Clear chat messages
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = `
        <div class="message message-received">
            <div>أهلاً وسهلاً، أنا ${doctorName}. كيف يمكنني مساعدتك؟</div>
            <div class="message-time">${new Date().toLocaleTimeString('ar-SA', {hour: '2-digit', minute: '2-digit'})}</div>
        </div>
    `;
}

function quickAction(action) {
    const actions = {
        'appointment': 'سيتم توجيهك لصفحة حجز المواعيد',
        'prescription': 'سيتم عرض الوصفات الطبية الحالية',
        'results': 'سيتم عرض نتائج التحاليل الأخيرة',
        'report': 'سيتم إنشاء تقرير طبي شامل'
    };
    
    alert(actions[action]);
}

function emergency() {
    if (confirm('هل تريدين الاتصال بخدمات الطوارئ؟')) {
        alert('جاري الاتصال بخدمات الطوارئ...');
    }
}

// Enter key to send message
document.getElementById('messageInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Auto-scroll to bottom on page load
window.addEventListener('load', () => {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
});
