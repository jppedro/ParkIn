function abrirLink(url) {
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

// ADICIONE ESTA FUNÇÃO:
function logout() {
  console.log("Logout clicado!");
  // Adicione a sua lógica de logout aqui
  // Por agora, vamos voltar para a página de login (exemplo)
  // window.location.href = 'login.html'; 
  alert("Função Logout() chamada!");
}