document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    copyButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const targetId = btn.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                // Find the code element inside the target
                const codeElement = targetElement.querySelector('code');
                const textToCopy = codeElement ? codeElement.innerText : targetElement.innerText;
                
                try {
                    await navigator.clipboard.writeText(textToCopy);
                    
                    // Visual feedback
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                    
                    setTimeout(() => {
                        btn.innerHTML = originalHTML;
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                }
            }
        });
    });

    // Simple scroll reveal animation for elements
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Initial state for elements to animate
    const animateElements = document.querySelectorAll('.api-card, .timeline-item, .contributor-card, .feature-card, .cta-box');
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(el);
    });
});

// Tab switching for interactive code block
window.switchTab = function(evt, tabName) {
    const codeSwitcher = evt.currentTarget.closest('.hero-console');
    const tabcontents = codeSwitcher.getElementsByClassName("console-content");
    for (let i = 0; i < tabcontents.length; i++) {
        tabcontents[i].classList.remove("active");
    }
    const tablinks = codeSwitcher.getElementsByClassName("console-tab-btn");
    for (let i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove("active");
    }
    document.getElementById(tabName).classList.add("active");
    evt.currentTarget.classList.add("active");
    
    // Update file name indicator
    const fileLabel = document.getElementById('console-file-name');
    if (fileLabel) {
        if (tabName === 'curl') fileLabel.textContent = 'query.sh';
        else if (tabName === 'js') fileLabel.textContent = 'fetch.js';
        else if (tabName === 'python') fileLabel.textContent = 'query.py';
    }
}

// Copy functionality for switcher tabs
window.copySnippet = function(elementId) {
    const codeElement = document.getElementById(elementId);
    const textToCopy = codeElement.textContent;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const btn = codeElement.closest('.console-content').querySelector('.copy-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.color = '#4CAF50'; // Green for success
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}
