const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");

// Switch to Register
registerTab.onclick = () => {
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
};

// Switch to Login
loginTab.onclick = () => {
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
    registerForm.classList.add("hidden");
    loginForm.classList.remove("hidden");
};


// HANDLE LOGIN
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const res = await fetch("/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: loginEmail.value,
            password: loginPassword.value
        })
    });

    if (res.ok) {
        window.location.href = "/dashboard"; // redirect to chat UI
    } else {
        alert("Invalid login");
    }
});


// HANDLE REGISTER
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const res = await fetch("/register", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            fullname: regName.value,
            email: regEmail.value,
            password: regPassword.value
        })
    });

    if (res.ok) {
        alert("Account created! You can now login.");
        loginTab.click();
    } else {
        alert("Registration failed");
    }
});