// Get elements
const signUpButton = document.getElementById('signUp');
const signInButton = document.getElementById('signIn');
const container = document.getElementById('container');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

// Toggle between forms
signUpButton.addEventListener('click', () => {
    container.classList.add("right-panel-active");
});
signInButton.addEventListener('click', () => {
    container.classList.remove("right-panel-active");
});

// Demo buttons
function showLogin() {
    container.classList.remove("right-panel-active");
}
function showRegister() {
    container.classList.add("right-panel-active");
}

// Show notification
function showNotification(message, type = 'success') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideDown 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}
function validatePassword(password) {
    return password.length >= 6;
}

// Login form handler
loginForm.addEventListener('submit', function(e) {
    const email = this.email.value.trim();
    const password = this.password.value.trim();
    
    if (!validateEmail(email)) {
        showNotification('البريد الإلكتروني غير صحيح', 'error');
        e.preventDefault();
        return;
    }
    if (!validatePassword(password)) {
        showNotification('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error');
        e.preventDefault();
        return;
    }
    // الفورم يرسل تلقائي بعد التحقق
});

// Register form handler
registerForm.addEventListener('submit', function(e) {
    const formData = new FormData(this);
    const email = formData.get('email').trim();
    const password = formData.get('password').trim();
    const username = formData.get('username').trim();
    
    if (!username) {
        showNotification('يرجى إدخال اسم المستخدم', 'error');
        e.preventDefault();
        return;
    }
    if (!validateEmail(email)) {
        showNotification('البريد الإلكتروني غير صحيح', 'error');
        e.preventDefault();
        return;
    }
    if (!validatePassword(password)) {
        showNotification('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error');
        e.preventDefault();
        return;
    }
    // الفورم يرسل تلقائي بعد التحقق
});

// Password visibility toggle
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="password"]').forEach(input => {
        const wrapper = document.createElement('div');
        wrapper.className = 'password-wrapper';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle';
        toggleBtn.innerHTML = '<i class="far fa-eye"></i>';

        toggleBtn.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                this.innerHTML = '<i class="far fa-eye-slash"></i>';
            } else {
                input.type = 'password';
                this.innerHTML = '<i class="far fa-eye"></i>';
            }
        });

        wrapper.appendChild(toggleBtn);
    });

    // Load countries from JSON
    fetch("{{ url_for('static', filename='countries.json') }}")
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById("country-select");
        select.innerHTML = '<option value="">اختر الدولة</option>';
        data.forEach(country => {
            const option = document.createElement("option");
            option.value = country.name;
            option.text = country.name;
            select.add(option);
        });
    })
    .catch(error => console.log('Using default country list'));
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === 'l') container.classList.remove("right-panel-active");
    if (e.altKey && e.key === 'r') container.classList.add("right-panel-active");
});
