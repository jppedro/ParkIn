function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();

  if (username === "admin" && password === "admin") {
    localStorage.setItem("userRole", "admin");
    window.location.href = "admin.html";
  } else if (username === "aluno" && password === "aluno") {
    localStorage.setItem("userRole", "aluno");
    window.location.href = "index.html";
  } else {
    alert("Usuário ou senha incorretos!");
  }
}

function logout() {
  localStorage.removeItem("userRole");
  window.location.href = "login.html";
}

document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  const role = localStorage.getItem("userRole");

  if (path.includes("admin.html") || path.includes("regiao.html")) {
    if (role !== "admin") {
      alert("Acesso restrito! Faça login como admin.");
      window.location.href = "login.html";
    }
  }

  if (path.includes("index.html") || path.includes("estacionamento.html") || path.includes("visualizar-vagas.html")) {
    if (role !== "aluno" && role !== "admin") {
      alert("Sessão expirada. Faça login novamente.");
      window.location.href = "login.html";
    }
  }
});

function abrirRegiao(setor) {
  window.location.href = `regiao.html?setor=${setor}`;
}
