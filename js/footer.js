// Centralized Footer Component
function loadFooter() {
  const footerHTML = `
    <div class="footer">
      <div class="container">
        <div>
          <div class="footer-grid-second">
            <div id="w-node-_8a1b11ab-e58b-9729-ec02-886db88784db-6ccff337" class="flex-space-between">
              <div>
                <a href="index.html" onclick="scrollToHero(event)" style="text-decoration: none !important;"><img width="90" loading="lazy" alt="" src="images/Oski.png"></a>
                <div style="margin-top: 20px; color: #6b7280; font-size: 14px; line-height: 1.4;">
                  ©2025 OSKI. ALL RIGHTS RESERVED. HIPAA-COMPLIANT.<br>DESIGNED BY SAHAJ SATANI.
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
                          <div class="button-line-flex"><div>OSCESim</div></div>
                          <div class="line-horizontal"></div>
                        </a>
                        <a href="rubricon.html" class="button-first-line w-inline-block">
                          <div class="button-line-flex"><div>Rubricon</div></div>
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
                  <div class="title-small">
                    <a href="mailto:support@oski.app" style="text-decoration: none; color: inherit;">support@oski.app</a>
                  </div>
                  <div class="title-small add-top-px">
                    <a href="tel:+12146483111" style="text-decoration: none; color: inherit;">+1 (214) 648-3111</a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer styling to remove underlines and make all links unbolded -->
    <style>
      /* Remove underlines from ALL footer links and make them unbolded like contact info */
      .footer a, .footer .button-first-line {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      .footer a:hover, .footer .button-first-line:hover {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      /* Ensure Navigation and Useful Links sections have no underlines and are unbolded */
      .navigation-grid a {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      .navigation-grid a:hover {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      /* Override any conflicting styles */
      .footer .button-line-flex div {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      /* Contact links styling - keep consistent */
      .footer .title-small a {
          text-decoration: none !important;
          border-bottom: none !important;
          font-weight: normal !important;
      }

      .footer .title-small a:hover {
          text-decoration: none !important;
          border-bottom: none !important;
          opacity: 0.8;
      }
    </style>
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
    } else if (currentPage === 'promptgen.html' && link.getAttribute('href') === 'promptgen.html') {
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