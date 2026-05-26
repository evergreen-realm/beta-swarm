// Get all cards
const cards = document.querySelectorAll('.card');

// Add event listener to each card
cards.forEach((card) => {
    card.addEventListener('click', () => {
        // Toggle class
        card.classList.toggle('active');
    });
});

// Add smooth scroll to header
const header = document.querySelector('.header');
const headerHeight = header.offsetHeight;

window.addEventListener('scroll', () => {
    if (window.scrollY > headerHeight) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

// Add animation to cards
const content = document.querySelector('.content');
const cardsContainer = document.querySelector('.cards-container');

content.addEventListener('scroll', () => {
    if (content.scrollTop > 100) {
        cardsContainer.classList.add('animate');
    } else {
        cardsContainer.classList.remove('animate');
    }
});