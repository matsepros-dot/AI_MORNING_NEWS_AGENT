(() => {
 const menu = document.querySelector('.mobile-menu');
 const links = [...document.querySelectorAll('.desktop-nav a, .mobile-menu nav a')];
 const mark = (id) => links.forEach(link => {
   if (link.getAttribute('href') === '#' + id) link.setAttribute('aria-current', 'location');
   else link.removeAttribute('aria-current');
 });
 links.forEach(link => link.addEventListener('click', () => { if (menu) menu.open = false; mark(link.hash.slice(1)); }));
 document.addEventListener('click', event => { if (menu && !menu.contains(event.target)) menu.open = false; });
 document.addEventListener('keydown', event => { if (event.key === 'Escape' && menu) { menu.open = false; menu.querySelector('summary').focus(); } });
 if ('IntersectionObserver' in window) {
   const observer = new IntersectionObserver(entries => {
     const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top - b.boundingClientRect.top);
     if (visible.length) mark(visible[0].target.id);
   }, { rootMargin: '-110px 0px -55% 0px', threshold: 0 });
   document.querySelectorAll('.news-section[id]').forEach(section => observer.observe(section));
 }
})();
