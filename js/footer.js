// Centralized Footer Component
function loadFooter() {
  const footerHTML = `
    <div class="footer">
      <div class="container">
        <div>
          <div class="footer-grid-second">
            <div id="w-node-_8a1b11ab-e58b-9729-ec02-886db88784db-6ccff337" class="flex-space-between">
              <div>
                <a href="index.html" onclick="scrollToHero(event)"><img width="80" loading="lazy" alt="" src="images/Oski.png"></a>
                <div style="margin-top: 20px; color: #6b7280; font-size: 14px; line-height: 1.4;">
                  ©2025 OSKI. ALL RIGHTS RESERVED.<br>DESIGNED BY SAHAJ SATANI.
                </div>
              </div>
            </div>
            <div id="w-node-_8a1b11ab-e58b-9729-ec02-886db88784f8-6ccff337">
              <div>
                <p class="title-small for-footer-title">Navigation</p>
                <div class="margin-20">
                  <div class="footer-small-grid no-grid">
                    <div>
                      <div class="navigation-grid">
                        <a href="index.html" class="button-first-line w-inline-block" onclick="scrollToHero(event)">
                          <div class="button-line-flex"><div>Home</div></div>
                          <div class="line-horizontal"></div>
                        </a>
                        <a href="index.html#features" class="button-first-line w-inline-block">
                          <div class="button-line-flex"><div>Features</div></div>
                          <div class="line-horizontal"></div>
                        </a>
                        <a href="index.html#pricing" class="button-first-line w-inline-block">
                          <div class="button-line-flex"><div>Pricing</div></div>
                          <div class="line-horizontal"></div>
                        </a>
                        <a href="simulation.html" class="button-first-line w-inline-block">
                          <div class="button-line-flex"><div>Simulation</div></div>
                          <div class="line-horizontal"></div>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div id="w-node-_8a1b11ab-e58b-9729-ec02-886db88784ff-6ccff337">
              <div>
                <p class="title-small for-footer-title">useful links</p>
                <div class="margin-20">
                  <div class="footer-small-grid">
                    <div class="navigation-grid">
                      <a href="https://labs.utsouthwestern.edu/jamieson-lab" target="_blank" class="button-first-line w-inline-block">
                        <div class="button-line-flex"><div>Jamieson Lab</div></div>
                        <div class="line-horizontal"></div>
                      </a>
                      <a href="privacy-policy.html" class="button-first-line w-inline-block">
                        <div class="button-line-flex"><div>Privacy Policy</div></div>
                        <div class="line-horizontal"></div>
                      </a>
                      <a href="terms-conditions.html" class="button-first-line w-inline-block">
                        <div class="button-line-flex"><div>Terms & Conditions</div></div>
                        <div class="line-horizontal"></div>
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div id="w-node-_8a1b11ab-e58b-9729-ec02-886db8878548-6ccff337">
              <div>
                <p class="title-small for-footer-title">contact us</p>
                <div class="margin-20">
                  <p class="title-small">support@oski.app<br></p>
                  <p class="title-small add-top-px">(214) 648-3111<br></p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
  
  // Insert footer into the page
  const footerContainer = document.getElementById('footer-container');
  if (footerContainer) {
    footerContainer.innerHTML = footerHTML;
  }
  
  // Set active footer link based on current page
  setActiveFooterLink();
}

function setActiveFooterLink() {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  const footerLinks = document.querySelectorAll('.footer .button-first-line');
  
  footerLinks.forEach(link => {
    link.classList.remove('w--current');
    
    // Check if this link matches the current page
    if (currentPage === 'simulation.html' && link.getAttribute('href') === 'simulation.html') {
      link.classList.add('w--current');
    } else if ((currentPage === 'index.html' || currentPage === '') && link.getAttribute('href') === 'index.html') {
      link.classList.add('w--current');
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

// Load footer when DOM is ready
document.addEventListener('DOMContentLoaded', loadFooter); 