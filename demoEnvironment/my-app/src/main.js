import './style.css'

document.querySelector('#app').innerHTML = `
<header class="netflix-header">
  <div class="header-inner">
    <div class="logo">NETFLIX</div>
    <div class="header-right">
      <button class="lang-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0014.07 6H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
        </svg>
        English
        <svg width="10" height="6" viewBox="0 0 10 6" fill="currentColor">
          <path d="M5 6L0 0h10L5 6z"/>
        </svg>
      </button>
      <button class="signin-btn">Sign In</button>
    </div>
  </div>
</header>

<main class="hero-section">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <h1 class="hero-title">Unlimited movies, TV<br>shows, and more</h1>
    <p class="hero-subtitle">Starts at $8.99. Cancel anytime.</p>
    <p class="hero-cta">Ready to watch? Enter your email to create or restart your membership.</p>
    <div class="email-form">
      <input type="email" class="email-input" placeholder="Email address" required>
      <button class="get-started-btn">
        Get Started
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
        </svg>
      </button>
    </div>
  </div>
</main>

<section class="promo-banner">
  <div class="promo-inner">
    <div class="promo-icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="8" fill="#E50914"/>
        <path d="M24 12l-8 16h16l-8-16z" fill="white"/>
        <path d="M16 28l8 12 8-12H16z" fill="white"/>
      </svg>
    </div>
    <p class="promo-text">The Netflix you love for just $8.99.</p>
    <button class="learn-more-btn">Learn More</button>
  </div>
</section>
`
