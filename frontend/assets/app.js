// Frontend da loja. Todas as chamadas passam pelo API Gateway (mesma origem).
const state = {
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
};

const $ = (id) => document.getElementById(id);

function toast(msg, type = "") {
  const el = $("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  setTimeout(() => (el.className = "toast"), 3200);
}

async function api(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await resp.json(); } catch (_) {}
  if (!resp.ok) {
    const err = (data && (data.error || data.detail)) || `Erro ${resp.status}`;
    throw new Error(err);
  }
  return data;
}

function renderAuth() {
  const logged = !!state.token;
  $("authSection").classList.toggle("hidden", logged);
  $("logoutBtn").classList.toggle("hidden", !logged);
  $("ordersSection").classList.toggle("hidden", !logged);
  $("adminSection").classList.toggle("hidden", !(state.user && state.user.role === "admin"));
  if (logged && state.user) {
    const badge = `<span class="badge ${state.user.role}">${state.user.role}</span>`;
    $("userInfo").innerHTML = `${state.user.name} ${badge}`;
  } else {
    $("userInfo").textContent = "nao autenticado";
  }
}

function setSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  renderAuth();
  loadProducts();
  loadOrders();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.clear();
  renderAuth();
  $("ordersBody").innerHTML = "";
}

async function loadProducts() {
  try {
    const products = await api("/products");
    const list = $("productsList");
    if (!products.length) {
      list.innerHTML = '<p class="empty">Nenhum produto cadastrado.</p>';
      return;
    }
    list.innerHTML = products.map((p) => `
      <div class="product">
        <span class="name">${escapeHtml(p.name)}</span>
        <span class="desc">${escapeHtml(p.description || "")}</span>
        <span class="price">R$ ${Number(p.price).toFixed(2)}</span>
        <span class="muted" style="font-size:.78rem">Estoque: ${p.stock ?? 0}</span>
        ${state.token ? `<button data-id="${p.id}" class="buyBtn">Comprar</button>` : ""}
      </div>`).join("");
    document.querySelectorAll(".buyBtn").forEach((b) =>
      b.addEventListener("click", () => createOrder(b.dataset.id)));
  } catch (e) {
    $("productsList").innerHTML = `<p class="empty">Falha ao carregar produtos: ${e.message}</p>`;
  }
}

async function loadOrders() {
  if (!state.token || !state.user) return;
  try {
    const orders = await api(`/orders/${state.user.id}`, { auth: true });
    const body = $("ordersBody");
    if (!orders.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty">Nenhum pedido ainda.</td></tr>';
      return;
    }
    body.innerHTML = orders.map((o) => `
      <tr>
        <td>${escapeHtml(o.productName)}</td>
        <td>${o.quantity}</td>
        <td>R$ ${Number(o.unitPrice).toFixed(2)}</td>
        <td>R$ ${Number(o.total).toFixed(2)}</td>
        <td>${new Date(o.created_at).toLocaleString("pt-BR")}</td>
      </tr>`).join("");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function createOrder(productId) {
  try {
    await api("/orders", { method: "POST", auth: true, body: { productId, quantity: 1 } });
    toast("Pedido criado!", "success");
    loadOrders();
  } catch (e) {
    toast(e.message, "error");
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- Eventos ----
$("loginBtn").addEventListener("click", async () => {
  try {
    const data = await api("/users/login", {
      method: "POST",
      body: { email: $("loginEmail").value, password: $("loginPassword").value },
    });
    setSession(data.token, data.user);
    toast(`Bem-vindo, ${data.user.name}!`, "success");
  } catch (e) { toast(e.message, "error"); }
});

$("registerBtn").addEventListener("click", async () => {
  try {
    await api("/users/register", {
      method: "POST",
      body: {
        name: $("regName").value,
        email: $("regEmail").value,
        password: $("regPassword").value,
        role: $("regAdmin").checked ? "admin" : "user",
      },
    });
    toast("Conta criada! Faca login.", "success");
  } catch (e) { toast(e.message, "error"); }
});

$("logoutBtn").addEventListener("click", logout);
$("reloadBtn").addEventListener("click", loadProducts);
$("reloadOrdersBtn").addEventListener("click", loadOrders);

$("createProductBtn").addEventListener("click", async () => {
  try {
    await api("/products", {
      method: "POST", auth: true,
      body: {
        name: $("pName").value,
        price: parseFloat($("pPrice").value),
        stock: parseInt($("pStock").value || "0", 10),
        description: $("pDesc").value,
      },
    });
    toast("Produto criado e replicado!", "success");
    ["pName", "pPrice", "pStock", "pDesc"].forEach((id) => ($(id).value = ""));
    loadProducts();
  } catch (e) { toast(e.message, "error"); }
});

// ---- Init ----
renderAuth();
loadProducts();
loadOrders();
