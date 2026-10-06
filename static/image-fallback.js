document.querySelectorAll('img.thumbnail').forEach((image) => {
  const fallback = () => { image.hidden = true; image.parentElement.classList.add('image-failed'); };
  image.addEventListener('error', fallback, { once: true });
  if (image.complete && image.naturalWidth === 0) fallback();
});
