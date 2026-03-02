// Crypto Arbitrage Pro - Website JavaScript
// Interactive features and animations

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all features
    initMobileMenu();
    initSmoothScroll();
    initScrollAnimations();
    initCounterAnimation();
    initDemoUpdates();
});

// ===== Mobile Menu =====
function initMobileMenu() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (!hamburger || !navMenu) return;
    
    hamburger.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        hamburger.classList.toggle('active');
    });
    
    // Close menu when clicking a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            hamburger.classList.remove('active');
        });
    });
}

// ===== Smooth Scroll =====
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// ===== Scroll Animations =====
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements
    document.querySelectorAll('.feature-card, .step, .pricing-card, .docs-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// Add animate-in styles
const style = document.createElement('style');
style.textContent = `
    .animate-in {
        opacity: 1 !important;
        transform: translateY(0) !important;
    }
`;
document.head.appendChild(style);

// ===== Counter Animation =====
function initCounterAnimation() {
    const counters = document.querySelectorAll('.stat-value, .demo-stat-value');
    
    const animateCounter = (counter) => {
        const target = counter.innerText;
        
        // Extract number from string (handle %, +, etc.)
        const match = target.match(/[\d.]+/);
        if (!match) return;
        
        const targetNum = parseFloat(match[0]);
        const suffix = target.replace(match[0], '');
        const duration = 2000; // 2 seconds
        const step = targetNum / (duration / 16); // 60fps
        let current = 0;
        
        const updateCounter = () => {
            current += step;
            if (current < targetNum) {
                counter.innerText = Math.floor(current).toLocaleString() + suffix;
                requestAnimationFrame(updateCounter);
            } else {
                counter.innerText = target;
            }
        };
        
        updateCounter();
    };
    
    // Observe counters
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                counterObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => counterObserver.observe(counter));
}

// ===== Demo Live Updates =====
function initDemoUpdates() {
    const demoData = [
        { pair: 'BTC/USDT', buy: 'Kraken', sell: 'Coinbase', profit: 0.42 },
        { pair: 'ETH/USDT', buy: 'Binance', sell: 'KuCoin', profit: 0.28 },
        { pair: 'SOL/USDT', buy: 'Huobi', sell: 'Binance', profit: 0.35 },
        { pair: 'XRP/USDT', buy: 'Coinbase', sell: 'Kraken', profit: 0.19 },
        { pair: 'ADA/USDT', buy: 'KuCoin', sell: 'Binance', profit: 0.23 },
        { pair: 'DOGE/USDT', buy: 'Binance', sell: 'Coinbase', profit: 0.31 },
        { pair: 'MATIC/USDT', buy: 'Kraken', sell: 'Huobi', profit: 0.26 },
        { pair: 'DOT/USDT', buy: 'Huobi', sell: 'KuCoin', profit: 0.18 },
    ];
    
    const tableBody = document.getElementById('demo-table-body');
    const scansEl = document.getElementById('demo-scans');
    const oppsEl = document.getElementById('demo-opps');
    const profitEl = document.getElementById('demo-profit');
    
    if (!tableBody) return;
    
    let scans = 1247;
    let opps = 52;
    let avgProfit = 0.18;
    
    // Update table every 3 seconds
    setInterval(() => {
        // Randomly select new data
        const randomData = demoData
            .sort(() => Math.random() - 0.5)
            .slice(0, 3);
        
        // Update table with animation
        tableBody.style.opacity = '0';
        
        setTimeout(() => {
            tableBody.innerHTML = randomData.map(item => `
                <tr>
                    <td><strong>${item.pair}</strong></td>
                    <td>${item.buy}</td>
                    <td>${item.sell}</td>
                    <td class="positive">+${item.profit.toFixed(2)}%</td>
                </tr>
            `).join('');
            
            tableBody.style.opacity = '1';
            tableBody.style.transition = 'opacity 0.3s ease';
        }, 300);
        
        // Update stats
        scans += Math.floor(Math.random() * 5) + 1;
        opps += Math.floor(Math.random() * 2);
        avgProfit = 0.15 + Math.random() * 0.1;
        
        if (scansEl) scansEl.innerText = scans.toLocaleString();
        if (oppsEl) oppsEl.innerText = opps;
        if (profitEl) profitEl.innerText = avgProfit.toFixed(2) + '%';
        
    }, 3000);
}

// ===== Navbar Scroll Effect =====
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
        navbar.style.background = 'rgba(10, 10, 15, 0.98)';
        navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.5)';
    } else {
        navbar.style.background = 'rgba(10, 10, 15, 0.95)';
        navbar.style.boxShadow = 'none';
    }
    
    lastScroll = currentScroll;
});

// ===== Typing Effect for Hero (Optional) =====
function typeWriter(element, text, speed = 50) {
    let i = 0;
    element.innerText = '';
    
    function type() {
        if (i < text.length) {
            element.innerText += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// ===== Parallax Effect for Hero Visual =====
const heroVisual = document.querySelector('.hero-visual');

if (heroVisual) {
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const heroSection = document.querySelector('.hero');
        
        if (scrolled < heroSection.offsetHeight) {
            heroVisual.style.transform = `translateY(${scrolled * 0.3}px)`;
        }
    });
}

// ===== Tooltip System =====
function createTooltip(element, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.innerText = text;
    
    element.addEventListener('mouseenter', (e) => {
        tooltip.style.left = e.pageX + 10 + 'px';
        tooltip.style.top = e.pageY - 30 + 'px';
        document.body.appendChild(tooltip);
    });
    
    element.addEventListener('mouseleave', () => {
        tooltip.remove();
    });
}

// ===== Lazy Loading Images =====
const images = document.querySelectorAll('img[data-src]');

const imageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
        }
    });
});

images.forEach(img => imageObserver.observe(img));

// ===== Console Easter Egg =====
console.log('%c💰 Crypto Arbitrage Pro', 'font-size: 24px; font-weight: bold; color: #00d9ff;');
console.log('%cBuilt with ❤️ by Siraj Shaikh', 'font-size: 14px; color: #a0a0a0;');
console.log('%c🚀 Final Year Project 2026', 'font-size: 14px; color: #00ff88;');
console.log('%c\nInterested in the code? Check out: https://github.com/Siraj637909/crypto-arbitrage-pro', 'font-size: 12px; color: #6b6b8a;');

// ===== Performance Monitoring (Optional) =====
if (window.performance) {
    window.addEventListener('load', () => {
        setTimeout(() => {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log(`Page Load Time: ${pageLoadTime}ms`);
        }, 0);
    });
}

// ===== Error Handling =====
window.addEventListener('error', (e) => {
    console.error('Website Error:', e.error);
    // In production, you might want to log this to a service
});

// ===== Service Worker Registration (For PWA) =====
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment to enable PWA
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered:', registration))
        //     .catch(error => console.log('SW registration failed:', error));
    });
}
