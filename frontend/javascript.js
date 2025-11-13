function abrirLink(url) {
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

function logout() {
  console.log("Logout clicado!");
  alert("Função Logout() chamada!");
}