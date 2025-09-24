# Sistema ParkIn - Frontend Interface

## Como Executar

### **Comando Único:**
```bash
cd "/Users/joao.rodrigues/Documents/Faculdade/6º Semestre/PI/ParkIn/frontend" && python3 -m http.server 8080
```

### **Passo a Passo:**
```bash
# 1. Navegar para o diretório frontend
cd "/Users/joao.rodrigues/Documents/Faculdade/6º Semestre/PI/ParkIn/frontend"

# 2. Iniciar servidor HTTP
python3 -m http.server 8080
```

### **Alternativas de Servidor:**

**Node.js (se instalado):**
```bash
npx http-server -p 8080
```

**Live Server (VS Code):**
- Instale a extensão "Live Server"
- Clique direito em `index.html` → "Open with Live Server"

## URLs de Acesso

- **Servidor:** http://localhost:8080
- **Página Principal:** http://localhost:8080/index.html
- **Estacionamento:** http://localhost:8080/estacionamento.html
- **Visualizar Vagas:** http://localhost:8080/visualizar-vagas.html

## Estrutura do Frontend

### **Páginas Disponíveis:**

1. **`index.html`** - Página inicial com menu principal
   - Acesso aos diferentes módulos do sistema
   - Design responsivo e moderno

2. **`estacionamento.html`** - Lista de setores do estacionamento
   - Visualização dos setores (H15, Mescla, H07, H00)
   - Navegação para visualização das vagas

3. **`visualizar-vagas.html`** - **Nova funcionalidade principal**
   - Exibe a imagem real do estacionamento
   - Overlay das vagas com cores dinâmicas
   - Dashboard com estatísticas em tempo real

### **Arquivos de Estilo:**

- **`style.css`** - Estilos globais compartilhados
- **`visualizar-vagas.css`** - Estilos específicos da visualização de vagas

### **Recursos:**
- **`imagem/`** - Diretório com todas as imagens e ícones
- **`javascript.js`** - Scripts JavaScript globais