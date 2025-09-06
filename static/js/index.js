// Initialize AOS
AOS.init({
    duration: 1000,
    once: true,
    easing: 'ease-in-out'
});

// Counter Animation
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    const speed = 200;
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        const increment = target / speed;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = target.toLocaleString('ar-SA');
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current).toLocaleString('ar-SA');
            }
        }, 10);
    });
}

// Trigger counter animation when stats section is visible
const statsSection = document.querySelector('.stats-section');
if (statsSection) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.unobserve(entry.target);
            }
        });
    });
    observer.observe(statsSection);
}

// Navbar scroll effect
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const offset = 80; // Height of fixed navbar
            const targetPosition = target.offsetTop - offset;
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// Department tabs functionality
const departmentTabs = document.querySelectorAll('.department-tab');
const departmentContents = document.querySelectorAll('.department-content');

departmentTabs.forEach(tab => {
    tab.addEventListener('click', function() {
        const department = this.getAttribute('data-department');
        
        departmentTabs.forEach(t => t.classList.remove('active'));
        departmentContents.forEach(c => c.classList.remove('active'));
        
        this.classList.add('active');
        const content = document.getElementById(department);
        if (content) content.classList.add('active');
    });
});

// Service Selection Interactions
function selectService(serviceType) {
    const button = event.target.closest('.service-btn');
    button.style.transform = 'translateY(-12px) scale(1.05)';
    button.style.borderColor = '#48b4bb';
    button.style.background = 'rgba(72, 180, 187, 0.1)';
    
    setTimeout(() => {
        button.style.transform = '';
        button.style.borderColor = '';
        button.style.background = '';
    }, 300);
    
    const serviceNames = {
        'ready-packages': 'الحزم الجاهزة',
        'custom-package': 'الحزمة المخصصة',
        'recreation': 'برامج الاستجمام'
    };
    
    alert(`تم اختيار: ${serviceNames[serviceType]}. سيتم توجيهك إلى صفحة التفاصيل.`);
}

// Enhanced Service Button Interactions
document.addEventListener('DOMContentLoaded', function() {
    const serviceButtons = document.querySelectorAll('.service-btn');
    
    serviceButtons.forEach(button => {
        // Click ripple effect
        button.addEventListener('click', function(e) {
            const ripple = this.querySelector('.btn-ripple');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = size + 'px';
            ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            ripple.classList.add('ripple-active');
            
            setTimeout(() => {
                ripple.classList.remove('ripple-active');
            }, 600);
        });
        
        // Magnetic effect
        button.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            this.style.transform = `translateY(-8px) rotateX(${y * 0.05}deg) rotateY(${x * 0.05}deg) scale(1.02)`;
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    
    // Intersection observer for service options
    const serviceOptions = document.querySelectorAll('.service-option');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 200);
            }
        });
    });
    
    serviceOptions.forEach(option => {
        option.style.opacity = '0';
        option.style.transform = 'translateY(30px)';
        observer.observe(option);
    });
    
    // Staggered animation for feature items
    const featureItems = document.querySelectorAll('.feature-preview-item');
    featureItems.forEach((item, index) => {
        setTimeout(() => {
            item.style.animation = `fadeInUp 0.6s ease-out ${index * 0.1}s both`;
        }, 1000);
    });
});

// CSS Animations
const fadeInUpStyle = document.createElement('style');
fadeInUpStyle.textContent = `
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .ripple-active {
        animation: rippleEffect 0.6s ease-out;
    }
    @keyframes rippleEffect {
        from { transform: scale(0); opacity: 1; }
        to { transform: scale(4); opacity: 0; }
    }
`;
document.head.appendChild(fadeInUpStyle);

// Testimonials Swiper
var testimonialSwiper = new Swiper(".testimonialSwiper", {
    slidesPerView: 1,
    spaceBetween: 30,
    loop: true,
    autoplay: { delay: 5000, disableOnInteraction: false },
    pagination: { el: ".swiper-pagination", clickable: true },
    breakpoints: { 768: { slidesPerView: 2 }, 1024: { slidesPerView: 3 } }
});

// Gallery lightbox
document.querySelectorAll('.gallery-item').forEach(item => {
    item.addEventListener('click', function() {
        const src = this.querySelector('img').getAttribute('src');
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); display: flex; align-items: center;
            justify-content: center; z-index: 9999; cursor: pointer;
        `;
        const modalImg = document.createElement('img');
        modalImg.src = src;
        modalImg.style.cssText = `max-width:90%; max-height:90%; border-radius:10px;`;
        modal.appendChild(modalImg);
        document.body.appendChild(modal);
        modal.addEventListener('click', () => modal.remove());
    });
});

// Contact form
const contactForm = document.querySelector('.contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success alert-dismissible fade show mt-3';
        successAlert.innerHTML = `
            <strong>شكراً لك!</strong> تم إرسال رسالتك بنجاح. سنتواصل معك قريباً.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        this.appendChild(successAlert);
        this.reset();
        setTimeout(() => successAlert.remove(), 5000);
    });
}

// Newsletter subscription
const newsletterForm = document.querySelector('.footer form');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = this.querySelector('input[type="email"]').value;
        if (email) {
            alert('شكراً لك! تم الاشتراك في النشرة البريدية بنجاح.');
            this.reset();
        }
    });
}

// Appointment modal
function openAppointmentModal() {
    const modalHTML = `
        <div class="modal fade" id="appointmentModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header" style="background: linear-gradient(135deg, #00a8a8, #008080); color: white;">
                        <h5 class="modal-title">حجز موعد</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form>
                            <div class="row">
                                <div class="col-md-6 mb-3"><label class="form-label">الاسم الكامل</label><input type="text" class="form-control" required></div>
                                <div class="col-md-6 mb-3"><label class="form-label">رقم الهاتف</label><input type="tel" class="form-control" required></div>
                                <div class="col-md-6 mb-3"><label class="form-label">البريد الإلكتروني</label><input type="email" class="form-control" required></div>
                                <div class="col-md-6 mb-3"><label class="form-label">القسم</label>
                                    <select class="form-control" required>
                                        <option value="">اختر القسم</option>
                                        <option>قسم القلب</option>
                                        <option>قسم العظام</option>
                                        <option>قسم الأطفال</option>
                                        <option>قسم الجلدية</option>
                                        <option>قسم الأسنان</option>
                                        <option>قسم العيون</option>
                                    </select>
                                </div>
                                <div class="col-md-6 mb-3"><label class="form-label">تاريخ الموعد</label><input type="date" class="form-control" required></div>
                                <div class="col-md-6 mb-3"><label class="form-label">وقت الموعد</label>
                                    <select class="form-control" required>
                                        <option value="">اختر الوقت</option>
                                        <option>9:00 صباحاً</option>
                                        <option>10:00 صباحاً</option>
                                        <option>11:00 صباحاً</option>
                                        <option>12:00 ظهراً</option>
                                        <option>2:00 مساءً</option>
                                        <option>3:00 مساءً</option>
                                        <option>4:00 مساءً</option>
                                        <option>5:00 مساءً</option>
                                    </select>
                                </div>
                                <div class="col-12 mb-3"><label class="form-label">ملاحظات (اختياري)</label><textarea class="form-control" rows="3"></textarea></div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إلغاء</button>
                        <button type="button" class="btn btn-primary" onclick="submitAppointment()">تأكيد الحجز</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    if (!document.getElementById('appointmentModal')) document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('appointmentModal'));
    modal.show();
}

function submitAppointment() {
    alert('تم حجز موعدك بنجاح! سنتواصل معك قريباً للتأكيد.');
    const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentModal'));
    modal.hide();
}

// Scroll to top button
const scrollTopBtn = document.createElement('button');
scrollTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
scrollTopBtn.style.cssText = `
    position: fixed; bottom: 100px; left: 30px; width: 50px; height: 50px;
    background: var(--primary-color); color: white; border: none; border-radius: 50%;
    font-size: 20px; cursor: pointer; opacity: 0; transition: all 0.3s ease; z-index: 998;
`;
document.body.appendChild(scrollTopBtn);

window.addEventListener('scroll', function() {
    scrollTopBtn.style.opacity = window.scrollY > 500 ? '1' : '0';
});

scrollTopBtn.addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});
