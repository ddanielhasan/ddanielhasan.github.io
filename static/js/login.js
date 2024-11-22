document.addEventListener("DOMContentLoaded", () => {
    const toggleIcons = document.querySelectorAll(".toggle-password");

    toggleIcons.forEach((icon) => {
        icon.addEventListener("click", () => {
            // Get the associated password input field (previous sibling)
            const passwordInput = icon.previousElementSibling;

            if (passwordInput && passwordInput.type === "password") {
                passwordInput.type = "text";
                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash"); // Change to hide icon
            } else if (passwordInput) {
                passwordInput.type = "password";
                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye"); // Change to show icon
            }
        });
    });
});

