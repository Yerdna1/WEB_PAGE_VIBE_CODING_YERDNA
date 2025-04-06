document.addEventListener('DOMContentLoaded', () => {
    // --- File Upload Display Logic --- 
    const fileInput = document.getElementById('game-upload');
    const filenameDisplay = document.querySelector('.file-upload-filename');
    const defaultFileText = 'Žiadny súbor nevybraný';

    if (fileInput && filenameDisplay) {
        filenameDisplay.textContent = defaultFileText;

        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                filenameDisplay.textContent = this.files[0].name;
            } else {
                filenameDisplay.textContent = defaultFileText;
            }
        });
    }

    // --- Smooth Scrolling for Navigation Links (using JS for Header Offset) --- 
    const header = document.querySelector('header');
    const headerHeight = header ? header.offsetHeight : 0;

    document.querySelectorAll('nav a[href^="#"], footer a[href^="#"], a.cta-button[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            // Check if it's actually an internal link
            if (targetId && targetId.startsWith('#') && targetId.length > 1) {
                e.preventDefault(); // Prevent default only for internal links
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    const elementPosition = targetElement.getBoundingClientRect().top;
                    // Calculate position considering current scroll and header height
                    const offsetPosition = window.pageYOffset + elementPosition - headerHeight - 10; // Added 10px buffer

                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // --- Contact Form Submission Handling --- 
    const contactForm = document.getElementById('contact-form');
    const formStatus = document.getElementById('form-status');

    if (contactForm && formStatus) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault(); // Prevent default browser submission
            formStatus.textContent = 'Odosielam...';
            formStatus.className = ''; // Reset class
            formStatus.style.display = 'block'; // Make status visible

            const formData = new FormData(contactForm);
            
            // --- !!! BACKEND INTEGRATION POINT !!! ---
            // This section simulates a successful submission.
            // In a real application, you would replace the 'await new Promise...' block 
            // with a fetch() call to your server-side endpoint (e.g., a Firebase Function 
            // or another API) to actually process the data (send email, save to database).
            
            /* --- Example using fetch (replace simulation below) ---
            try {
                const response = await fetch('/api/submit-contact', { // Replace with your actual endpoint
                    method: 'POST',
                    body: formData // FormData handles file uploads correctly
                });

                if (response.ok) {
                    const result = await response.json(); // Or .text() 
                    formStatus.textContent = 'Správa úspešne odoslaná! Ďakujeme.';
                    formStatus.className = 'success';
                    contactForm.reset(); 
                    if (filenameDisplay) filenameDisplay.textContent = defaultFileText;
                    console.log('Form submitted successfully:', result);
                } else {
                    const errorText = await response.text();
                    formStatus.textContent = `Chyba (${response.status}): ${errorText || 'Nepodarilo sa odoslať.'}`;
                    formStatus.className = 'error';
                    console.error('Form submission error:', response.status, errorText);
                }
            } catch (error) {
                formStatus.textContent = 'Chyba siete. Skúste to prosím neskôr.';
                formStatus.className = 'error';
                console.error('Network or other error:', error);
            }
            */
            
            // --- Start of Simulation Block --- 
            console.log('Form data (simulation - not sent):');
            for (let [key, value] of formData.entries()) {
                console.log(`${key}:`, value instanceof File ? value.name : value);
            }
            // Simulate network delay
            await new Promise(resolve => setTimeout(resolve, 1500)); 
            
            formStatus.textContent = 'Správa bola úspešne odoslaná! (Simulácia)';
            formStatus.className = 'success';
            contactForm.reset(); // Clear form fields
            if (filenameDisplay) filenameDisplay.textContent = defaultFileText; // Reset file input display
            // --- End of Simulation Block --- 
            
            // Hide status message after a few seconds
            setTimeout(() => {
                formStatus.style.display = 'none';
                formStatus.className = '';
                formStatus.textContent = '';
            }, 5000); // Hide after 5 seconds
        });
    }

});
