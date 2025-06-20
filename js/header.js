// Centralized Header Component
function loadHeader() {
  // Check if we're on rubricon.html to show logout button
  const isRubriconPage = window.location.pathname.includes('rubricon.html');
  
  const headerHTML = `
    <div class="navigation-wrapper">
      <div data-w-id="2ec87728-4b9f-a5bf-eacf-e9e9575fcd6a" data-animation="default" data-collapse="medium" data-duration="400" data-easing="ease" data-easing2="ease" role="banner" class="navbar-component w-nav">
        <div class="new-container">
          <a href="index.html" class="logo-link-main w-nav-brand" onclick="scrollToHero(event)">
            <div><img loading="lazy" src="images/Oski.png" alt="Oski Logo" class="logotype"></div>
          </a>
          <nav role="navigation" class="navbar-menu w-nav-menu">
            <div class="menu-right">
              <div class="menu-left">
                <a href="index.html#features" class="navbar-link w-nav-link">Features</a>
                <a href="index.html#pricing" class="navbar-link w-nav-link">Pricing</a>
                <a href="oscesim.html" class="navbar-link w-nav-link">OSCESim</a>
                <a href="rubricon.html" class="navbar-link w-nav-link">Rubricon</a>
              </div>
            </div>
          </nav>
          <div class="button-flex-left">
            <div class="menu-button-new w-nav-button">
              <div class="icon-component">
                <div class="line-top"></div>
                <div class="line-midddle"><div class="line-middle-inner"></div></div>
                <div class="line-bottom"></div>
              </div>
            </div>
            ${isRubriconPage ? `
              <button onclick="logout()" class="button-first _01 w-inline-block" style="background: #dc2626; border: none; cursor: pointer;">
                <div class="txt-wrapper">
                  <div class="button-txt">Logout</div>
                  <div class="button-txt">Logout</div>
                </div>
              </button>
            ` : `
              <a data-w-id="87ece5ab-4141-8518-64d6-497478bacd68" href="mailto:support@oski.app" class="button-first _01 w-inline-block">
                <div class="txt-wrapper">
                  <div class="button-txt">Contact</div>
                  <div class="button-txt">Contact</div>
                </div>
              </a>
            `}
          </div>
        </div>
      </div>
    </div>
  `;
  
  // Insert header into the page
  const headerContainer = document.getElementById('header-container');
  if (headerContainer) {
    headerContainer.innerHTML = headerHTML;
  }
  
  // Set active navigation link based on current page
  setActiveNavLink();
}

function setActiveNavLink() {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  const navLinks = document.querySelectorAll('.navbar-link');
  
  navLinks.forEach(link => {
    link.classList.remove('w--current');
    
    // Check if this link matches the current page
    if (currentPage === 'simulation.html' && link.getAttribute('href') === 'simulation.html') {
      link.classList.add('w--current');
    } else if (currentPage === 'rubricon.html' && link.getAttribute('href') === 'rubricon.html') {
      link.classList.add('w--current');
    } else if (currentPage === 'index.html' || currentPage === '') {
      // For index page, don't add w--current to any nav links since we removed Home
      // The logo will serve as the home indicator
    }
  });
}

// Smooth scroll to hero section
function scrollToHero(event) {
  // If we're on the same page, prevent default and scroll
  if (window.location.pathname.includes('index.html') || window.location.pathname === '/') {
    event.preventDefault();
    const heroSection = document.getElementById('hero');
    if (heroSection) {
      heroSection.scrollIntoView({ behavior: 'smooth' });
    }
  }
  // If we're on a different page, let the link work normally to go to index.html
}

// Load header when DOM is ready
document.addEventListener('DOMContentLoaded', loadHeader); 