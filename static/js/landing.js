document.addEventListener('DOMContentLoaded', () => {
    // Wait a brief moment to ensure fonts and layout are rendered
    setTimeout(() => {
        gsap.from(".hero-text-anim", {
            y: 100,              // Start 100px below normal position
            opacity: 0,          // Start completely transparent
            duration: 1.2,       // Take 1.2 seconds to animate
            stagger: 0.15,       // Wait 0.15 seconds between each line
            ease: "power4.out",  // Start fast, end very smoothly (The Apple feel)
        });
    }, 100);
});