function fillDemoInputs(email, password) {
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    if (!emailInput || !passwordInput) {
        return;
    }

    emailInput.value = email;
    passwordInput.value = password;
}

function attachDemoAccountHandlers() {
    const demoAccounts = document.querySelectorAll('[data-demo-email][data-demo-password]');

    demoAccounts.forEach((account) => {
        account.addEventListener('click', () => {
            fillDemoInputs(account.dataset.demoEmail, account.dataset.demoPassword);
        });
    });
}

window.addEventListener('DOMContentLoaded', () => {
    attachDemoAccountHandlers();
});
