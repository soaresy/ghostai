// =========================================
// GhostAI Login — Lógica JS
// =========================================

document.getElementById("btnLogin")?.addEventListener("click", loginUser);

async function loginUser() {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!email || !password) {
        showError("Preencha email e senha.");
        return;
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        if (res.status === 200) {
            window.location.href = "/dashboard";
        } else {
            const data = await res.json();
            showError(data.detail || "Credenciais inválidas.");
        }
    } catch (e) {
        showError("Erro de conexão.");
    }
}

/* UI → Mensagens de erro */
function showError(msg) {
    let el = document.getElementById("login-error");

    if (!el) {
        el = document.createElement("div");
        el.id = "login-error";
        el.style.color = "#ff6b6b";
        el.style.marginTop = "10px";
        el.style.fontSize = "14px";
        document.querySelector(".login-card").appendChild(el);
    }

    el.textContent = msg;
}