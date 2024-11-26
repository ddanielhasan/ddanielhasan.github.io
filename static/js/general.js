//make flashes disappear
document.addEventListener("DOMContentLoaded", () => {
    const flashMessages = document.querySelectorAll(".flashes li");

    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(message => {
                message.style.transition = "opacity 0.5s ease";
                message.style.opacity = "0"; // Fade out
                setTimeout(() => {
                    message.remove(); // Remove after fading out
                }, 500); // Match the transition duration
            });
        }, 3000); // Delay before fade-out starts (3 seconds)
    }
});
