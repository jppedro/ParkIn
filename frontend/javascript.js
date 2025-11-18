function abrirLink(url) {
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

function logout() {
  localStorage.removeItem("userRole");
  window.location.href = "login.html";
  console.log("Logout clicado!");
  alert("Função Logout() chamada!");
}