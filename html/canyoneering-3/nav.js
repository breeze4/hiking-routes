(function() {
  var nav = document.querySelector('nav.outline');
  if (!nav) return;

  var toggle = nav.querySelector('.outline-toggle');

  // Determine current page filename
  var path = location.pathname;
  var currentPage = path.substring(path.lastIndexOf('/') + 1) || 'index.html';

  // Highlight current page link and expand its section
  var links = nav.querySelectorAll('.outline-links a');
  for (var i = 0; i < links.length; i++) {
    var href = links[i].getAttribute('href');
    if (!href) continue;
    var linkPage = href.split('#')[0] || 'index.html';
    if (linkPage === currentPage) {
      links[i].classList.add('active');
      // Expand parent <details> elements
      var el = links[i].parentElement;
      while (el && el !== nav) {
        if (el.tagName === 'DETAILS') {
          el.open = true;
        }
        el = el.parentElement;
      }
      // Scroll active link into view in sidebar
      if (window.innerWidth >= 1250) {
        links[i].scrollIntoView({ block: 'center' });
      }
      break;
    }
  }

  // Mobile: toggle nav open/close
  if (toggle) {
    toggle.addEventListener('click', function() {
      nav.classList.toggle('open');
    });
  }

  // For details with children: clicking summary link behavior
  nav.querySelectorAll('details').forEach(function(details) {
    var childLinks = details.querySelectorAll(':scope > a');
    if (childLinks.length === 0) return;

    var summaryLink = details.querySelector('summary a');
    if (!summaryLink) return;

    summaryLink.addEventListener('click', function(e) {
      var href = summaryLink.getAttribute('href');
      var linkPage = href ? href.split('#')[0] : '';
      // If summary points to current page, toggle expansion instead of navigating
      if (linkPage === currentPage || linkPage === '') {
        e.preventDefault();
        e.stopImmediatePropagation();
        details.open = !details.open;
      }
      // Otherwise, allow normal navigation
    });
  });

  // Mobile: close nav when clicking a navigation link
  nav.querySelectorAll('.outline-links a').forEach(function(a) {
    a.addEventListener('click', function() {
      nav.classList.remove('open');
    });
  });

  // Map toggle (deferred — button is in content, after this script)
  document.addEventListener('DOMContentLoaded', function() {
    var mapToggle = document.querySelector('.map-toggle');
    if (mapToggle) {
      mapToggle.addEventListener('click', function() {
        document.body.classList.toggle('map-hidden');
        mapToggle.textContent = document.body.classList.contains('map-hidden') ? 'Show Map' : 'Hide Map';
      });
    }
  });
})();
