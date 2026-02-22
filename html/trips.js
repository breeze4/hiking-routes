(function() {
  var trips = [
    {name: "Muddy Creek", dir: "muddy-creek"},
    {name: "Stevens Canyon & Baker Route", dir: "stevens-canyon"}
  ];

  var style = document.createElement('style');
  style.textContent =
    '#trip-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 9999;' +
    ' background: #2c2c2c; padding: 0 1rem; display: flex; align-items: center;' +
    ' gap: 1.5rem; height: 36px; overflow-x: auto; font: 13px/1 -apple-system,' +
    ' BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }' +
    '#trip-nav a { color: #aaa; text-decoration: none; white-space: nowrap; }' +
    '#trip-nav a:hover { color: #fff; }' +
    '#trip-nav a.current { color: #fff; font-weight: 600; }';
  document.head.appendChild(style);

  var pathParts = location.pathname.split('/').filter(Boolean);
  var currentDir = pathParts[pathParts.length - 2] || '';

  var nav = document.createElement('nav');
  nav.id = 'trip-nav';
  trips.forEach(function(trip) {
    var a = document.createElement('a');
    a.href = '../' + trip.dir + '/index.html';
    a.textContent = trip.name;
    if (trip.dir === currentDir) a.className = 'current';
    nav.appendChild(a);
  });
  document.body.prepend(nav);

  document.body.style.paddingTop =
    (parseFloat(getComputedStyle(document.body).paddingTop) + 36) + 'px';
})();
