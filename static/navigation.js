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
 const sections = [...document.querySelectorAll('.news-section[id]')];
 let pending = false;
 const update = () => {
   const edge = (document.querySelector('.site-header')?.getBoundingClientRect().bottom || 0) + 40;
   let active = '';
   for (const section of sections) {
     if (section.getBoundingClientRect().top <= edge) active = section.id;
     else break;
   }
   mark(active);
   pending = false;
 };
 window.addEventListener('scroll', () => { if (!pending) { pending = true; requestAnimationFrame(update); } }, { passive: true });
 window.addEventListener('resize', update);
 update();
})();
