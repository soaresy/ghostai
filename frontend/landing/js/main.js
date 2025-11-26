// main.js (versão corrigida)
async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

function go(path) {
  if (!path.startsWith("/")) path = "/" + path;
  window.location.href = window.location.origin + path;
}

const CHAT_STORAGE_KEY = "chatQuali";
const CHAT_HISTORY_KEY = "chatHistory";

function createEmptyChatState() {
  return { stage: 0, data: {} };
}
let chatState = loadChatState();
let chatHistory = loadChatHistory();

function loadChatState() {
  try { return JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY)) || createEmptyChatState(); } catch { return createEmptyChatState(); }
}
function loadChatHistory() {
  try { return JSON.parse(sessionStorage.getItem(CHAT_HISTORY_KEY)) || []; } catch { return []; }
}
function saveChatState() { sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatState)); }
function saveChatHistory() { sessionStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(chatHistory)); }

document.addEventListener("DOMContentLoaded", () => {
  if (window.location.pathname === "/success") {
    sessionStorage.removeItem("onboardingData");
    sessionStorage.removeItem("checkout");
    sessionStorage.removeItem(CHAT_STORAGE_KEY);
    sessionStorage.removeItem(CHAT_HISTORY_KEY);
    chatState = createEmptyChatState();
    chatHistory = [];
  }

  const checkoutForm = document.getElementById("checkout-form");
  if (checkoutForm) {
    const stored = JSON.parse(sessionStorage.getItem("checkout") || "{}");
    if (stored.email) checkoutForm.querySelector('[name="email"]').value = stored.email;
    if (stored.whatsapp) checkoutForm.querySelector('[name="whatsapp"]').value = stored.whatsapp;
    checkoutForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(e.target));
      sessionStorage.setItem("checkout", JSON.stringify(data));
      go("/onboarding");
    });
  }

  const form = document.getElementById("onboarding-form");
  if (form) setupOnboarding(form);
  setupChatbotUI();
});

function setupOnboarding(form) {
  const steps = Array.from(document.querySelectorAll(".step"));
  const progressFill = document.getElementById("progress-fill");
  const label = document.getElementById("progress-label");
  let step = 0;
  const saved = JSON.parse(sessionStorage.getItem("onboardingData") || "{}");
  // prefill from checkout
  const checkout = JSON.parse(sessionStorage.getItem("checkout") || "{}");
  if (checkout.email && !saved.email) saved.email = checkout.email;
  if (checkout.whatsapp && !saved.whatsapp) saved.whatsapp = checkout.whatsapp;

  Object.entries(saved).forEach(([k, v]) => {
    const els = form.querySelectorAll(`[name="${k}"]`);
    if (!els || els.length === 0) return;
    const el = els[0];
    if (Array.isArray(v)) v.forEach(val => form.querySelector(`[value="${val}"]`)?.click());
    else el.value = v;
  });

  function updateUI() {
    steps.forEach((s, i) => s.classList.toggle("active", i === step));
    progressFill.style.width = ((step + 1) / steps.length) * 100 + "%";
    label.textContent = `Etapa ${step + 1} de ${steps.length}`;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  updateUI();

  form.querySelectorAll(".next").forEach(btn => {
    btn.addEventListener("click", () => {
      const requiredFields = steps[step].querySelectorAll("input[required], textarea[required]");
      for (const field of requiredFields) {
        if (!field.value.trim()) {
          field.classList.add("input-error");
          setTimeout(() => field.classList.remove("input-error"), 1200);
          return;
        }
      }
      if (step < steps.length - 1) { step++; updateUI(); }
    });
  });

  form.querySelectorAll(".back-btn").forEach(btn => {
    btn.addEventListener("click", () => { if (step > 0) { step--; updateUI(); } });
  });

  form.addEventListener("change", () => {
    const fd = new FormData(form);
    const obj = Object.fromEntries(fd.entries());
    obj.canal = fd.getAll("canal");
    obj.objetivo = fd.getAll("objetivo");
    sessionStorage.setItem("onboardingData", JSON.stringify(obj));
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const data = Object.fromEntries(fd.entries());
    data.canal = fd.getAll("canal");
    data.objetivo = fd.getAll("objetivo");
    // attach checkout contact if present
    const raw = sessionStorage.getItem("checkout");
    if (raw) {
      try {
        const c = JSON.parse(raw);
        data.email = data.email || c.email;
        data.whatsapp = data.whatsapp || c.whatsapp;
      } catch {}
    }
    const rawChat = sessionStorage.getItem(CHAT_STORAGE_KEY);
    if (rawChat) data.chat_qualificacao = JSON.parse(rawChat).data;
    try {
      const result = await post("/api/onboarding", data);
      sessionStorage.removeItem("onboardingData");
      go(result.redirect || "/success");
    } catch (err) {
      alert("Erro ao enviar formulário. Tente novamente.");
    }
  });
}

/* CHAT UI */
const chatBtn = document.getElementById("ghost-chat-btn");
const chatBox = document.getElementById("ghost-chat");
const closeChat = document.getElementById("chat-close");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLog = document.getElementById("chat-log");

function setupChatbotUI() {
  chatBtn?.addEventListener("click", () => {
    chatBox.classList.toggle("visible");
    if (chatBox.classList.contains("visible") && chatLog.children.length === 0 && chatState.stage === 0) {
      startCommercialFlow();
    }
  });
  closeChat?.addEventListener("click", () => chatBox.classList.remove("visible"));
}

function addMessage(text, sender = "bot") {
  if (!chatLog) return;
  const msg = document.createElement("div");
  msg.classList.add("chat-msg");
  if (sender === "user") msg.classList.add("user");
  msg.textContent = text;
  chatLog.appendChild(msg);
  chatLog.scrollTo({ top: chatLog.scrollHeight, behavior: "smooth" });
}

async function botTypingEffect(text, delay = 12) {
  if (!chatLog) return;
  const msg = document.createElement("div");
  msg.classList.add("chat-msg");
  chatLog.appendChild(msg);
  for (let i = 0; i < text.length; i++) {
    msg.textContent += text[i];
    chatLog.scrollTo({ top: chatLog.scrollHeight });
    await new Promise(r => setTimeout(r, delay));
  }
}

async function startCommercialFlow() {
  chatState.stage = 1; saveChatState();
  await botTypingEffect("👋 Opa! Antes de personalizar sua automação, me diz rapidinho:\n\nVocê já usa automação ou está começando do zero?");
}

async function handleChatFlow(userText) {
  switch (chatState.stage) {
    case 1: chatState.data.automacao = userText; break;
    case 2: chatState.data.segmento = userText; break;
    case 3: chatState.data.canal = userText; break;
    case 4: chatState.data.volume = userText; break;
    case 5: chatState.data.objetivo = userText; break;
    case 6:
      chatState.data.urgencia = userText;
      chatState.stage = 7;
      saveChatState();
      return botTypingEffect("Perfeito 👌 Agora é só clicar em Iniciar diagnóstico no site!");
  }
  chatState.stage++; saveChatState();
  return botTypingEffect(waitingResponses(chatState.stage));
}

function waitingResponses(stage) {
  return {
    2: "Boa! Qual o segmento do seu negócio? (ex: estética, loja, infoproduto, restaurante...)",
    3: "Legal. Hoje onde chegam mais mensagens? WhatsApp, Insta, site…?",
    4: "Show. Quantas pessoas te chamam por dia em média?",
    5: "E qual objetivo principal agora? (vendas, atendimento, agendamento, suporte…)",
    6: "Última: pretende implementar quando?",
  }[stage];
}

/* IA chat submit */
chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = (chatInput?.value || "").trim();
  if (!message) return;
  addMessage(message, "user");
  chatInput.value = "";
  chatHistory.push({ role: "user", content: message });
  saveChatHistory();
  if (chatState.stage < 7) return handleChatFlow(message);
  try {
    const ai = await post("/api/chat", { message, history: chatHistory });
    if (ai.reply) {
      addMessage(ai.reply, "bot");
      chatHistory.push({ role: "assistant", content: ai.reply });
      saveChatHistory();
    }
    if (/(fechar|contratar|link|checkout|começar|ativar|onde pago|assinar|pagar)/i.test(message)) {
      await botTypingEffect("Show! 🤝 Para continuar use o botão Iniciar diagnóstico ou acesse /checkout no site.");
    }
  } catch (err) {
    addMessage("😅 Algo deu ruim — tenta de novo!", "bot");
  }
});
