
      // Initialize form interactions
      const form = document.getElementById('consultationForm');
      const questionField = document.getElementById('questionField');
      const descriptionField = document.getElementById('descriptionField');
      const medicalHistory = document.getElementById('medicalHistory');
      const requiredMsg = document.getElementById('requiredMsg');
      const progressFill = document.querySelector('.progress-fill');
      
      // Character counters
      function updateCounter(field, counterId, maxLength) {
          const counter = document.getElementById(counterId);
          const length = field.value.length;
          counter.textContent = `${length}/${maxLength}`;
          
          // Color coding
          const percentage = (length / maxLength) * 100;
          if (percentage > 90) {
              counter.style.color = '#e74c3c';
          } else if (percentage > 70) {
              counter.style.color = '#f39c12';
          } else {
              counter.style.color = 'var(--text-secondary)';
          }
      }

      // Question field handlers
      questionField.addEventListener('input', function() {
          updateCounter(this, 'questionCounter', 200);
          
          // Toggle required message
          if (this.value.trim()) {
              requiredMsg.style.display = 'none';
          } else {
              requiredMsg.style.display = 'flex';
          }
          
          updateProgress();
      });

      // Description field handler
      descriptionField.addEventListener('input', function() {
          updateCounter(this, 'descriptionCounter', 500);
          updateProgress();
      });

      // Medical history handler
      medicalHistory.addEventListener('input', function() {
          updateCounter(this, 'historyCounter', 300);
          updateProgress();
      });

      // Update progress bar
      function updateProgress() {
          const fields = [
              document.getElementById('specialization').value ? 1 : 0,
              questionField.value.trim() ? 1 : 0,
              descriptionField.value.trim() ? 1 : 0,
              document.querySelector('input[name="questionFor"]:checked') ? 1 : 0,
              document.querySelector('input[name="gender"]:checked') ? 1 : 0,
              document.querySelector('.age-input').value ? 1 : 0
          ];
          
          const completed = fields.reduce((a, b) => a + b, 0);
          const percentage = (completed / 6) * 100;
          progressFill.style.width = percentage + '%';
      }

      // Specialization change
      document.getElementById('specialization').addEventListener('change', updateProgress);

      // Radio buttons change
      document.querySelectorAll('input[type="radio"]').forEach(radio => {
          radio.addEventListener('change', updateProgress);
      });

      // Age input change
      document.querySelector('.age-input').addEventListener('input', updateProgress);

      // Form submission
      form.addEventListener('submit', function(e) {
          e.preventDefault();
          
          // Validate required fields
          const specialization = document.getElementById('specialization').value;
          const question = questionField.value.trim();
          const age = document.querySelector('.age-input').value;
          
          if (!specialization) {
              alert('الرجاء اختيار التخصص الطبي');
              document.getElementById('specialization').focus();
              return;
          }
          
          if (!question) {
              questionField.focus();
              requiredMsg.style.display = 'flex';
              return;
          }
          
          if (!age) {
              document.querySelector('.age-input').focus();
              alert('الرجاء إدخال العمر');
              return;
          }
          
          // Animate button
          const btn = this.querySelector('.submit-btn');
          btn.innerHTML = '<span style="position: relative; z-index: 1;">جاري الإرسال...</span>';
          btn.style.opacity = '0.8';
          
          // Simulate sending
          setTimeout(() => {
              btn.innerHTML = '<span style="position: relative; z-index: 1;">✓ تم الإرسال بنجاح</span>';
              btn.style.background = 'linear-gradient(135deg, var(--success-color), #218838)';
              
              setTimeout(() => {
                  alert('تم إرسال استشارتك بنجاح! سيتم الرد عليك قريباً.');
                  form.reset();
                  updateProgress();
              }, 1000);
          }, 2000);
      });

      // Initialize progress on load
      updateProgress();