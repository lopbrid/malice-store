document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Cart count animation
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        cartCount.style.transition = 'transform 0.3s ease';
        cartCount.addEventListener('mouseenter', () => {
            cartCount.style.transform = 'scale(1.2)';
        });
        cartCount.addEventListener('mouseleave', () => {
            cartCount.style.transform = 'scale(1)';
        });
    }

    // Product card hover effect enhancement
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.zIndex = '10';
        });
        card.addEventListener('mouseleave', function() {
            this.style.zIndex = '1';
        });
    });

    // Parallax effect for hero
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        });
    }

    // Form input focus effects
    const inputs = document.querySelectorAll('.form-control');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });

    // Add to cart animation
    const addToCartBtns = document.querySelectorAll('form[action*="cart_add"] button');
    addToCartBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const originalText = this.textContent;
            this.textContent = 'ADDING...';
            this.style.opacity = '0.7';
            
            setTimeout(() => {
                this.textContent = 'ADDED';
                this.style.background = '#333';
                this.style.color = '#fff';
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.style.opacity = '1';
                    this.style.background = '';
                    this.style.color = '';
                }, 1000);
            }, 300);
        });
    });

    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.product-card').forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        observer.observe(el);
    });
});