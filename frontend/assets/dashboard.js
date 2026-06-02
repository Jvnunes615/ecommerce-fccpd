// Dashboard de monitoramento: consulta /status do Gateway periodicamente.
const grid = document.getElementById("svcGrid");
const lastUpdate = document.getElementById("lastUpdate");

const LABELS = {
  "users": "Usuarios",
  "orders": "Pedidos",
  "products-primario": "Produtos (primario)",
  "products-replica": "Produtos (replica)",
};

function fmt(ts) {
  try { return new Date(ts).toLocaleTimeString("pt-BR"); } catch { return ts; }
}

async function refresh() {
  try {
    const resp = await fetch("/status");
    const data = await resp.json();
    grid.innerHTML = data.services.map((s) => {
      const cls = s.up ? "up" : "down";
      const label = LABELS[s.name] || s.name;
      return `
        <div class="svc">
          <div class="svc-name"><span class="dot ${cls}"></span>${label}</div>
          <div class="svc-url">${s.url}</div>
          <div class="row" style="margin:6px 0">
            <span class="badge ${cls}">${s.up ? "ONLINE" : "OFFLINE"}</span>
          </div>
          <div class="svc-meta">Falhas consecutivas: ${s.failures}</div>
          <div class="svc-meta">Ultima mudanca: ${fmt(s.last_change)}</div>
        </div>`;
    }).join("");
    lastUpdate.textContent = "Atualizado " + fmt(data.timestamp);
  } catch (e) {
    grid.innerHTML = '<p class="empty">Gateway inacessivel.</p>';
    lastUpdate.textContent = "sem conexao";
  }
}

refresh();
setInterval(refresh, 2000);
