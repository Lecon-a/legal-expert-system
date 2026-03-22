const reveals = document.querySelectorAll('.reveal');
  window.addEventListener('scroll', () => {
    reveals.forEach(r => {
      const top = r.getBoundingClientRect().top;
      if (top < window.innerHeight - 80) r.classList.add('active');
    });
  });


const toggle = document.getElementById("navToggle");
const navLinks = document.getElementById("navLinks");

toggle.addEventListener("click", () => {
    navLinks.classList.toggle("open");
});