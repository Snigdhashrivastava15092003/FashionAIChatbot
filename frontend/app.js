var API = "/api";
var SESSION_KEY = "fashion-ai-session-id";
var state = {
  history: [],
  sessionId: null,
  knownSlots: [],
  pendingSlot: null
};

var el = {
  healthBadge: document.getElementById("healthBadge"),
  modelBadge: document.getElementById("modelBadge"),
  sessionBadge: document.getElementById("sessionBadge"),
  slotStrip: document.getElementById("slotStrip"),
  chatHistory: document.getElementById("chatHistory"),
  chatForm: document.getElementById("chatForm"),
  messageInput: document.getElementById("messageInput"),
  typingIndicator: document.getElementById("typingIndicator"),
  errorBox: document.getElementById("errorBox"),
  warningBox: document.getElementById("warningBox"),
  preferenceHints: document.getElementById("preferenceHints"),
  clearButton: document.getElementById("clearButton"),
  recommendationTitle: document.getElementById("recommendationTitle"),
  recommendationSummary: document.getElementById("recommendationSummary"),
  occasionMatch: document.getElementById("occasionMatch"),
  personalityMatch: document.getElementById("personalityMatch"),
  budgetFit: document.getElementById("budgetFit"),
  confidenceSummary: document.getElementById("confidenceSummary"),
  sourceBadge: document.getElementById("sourceBadge"),
  mainItemsList: document.getElementById("mainItemsList"),
  layeringList: document.getElementById("layeringList"),
  footwearList: document.getElementById("footwearList"),
  accessoriesList: document.getElementById("accessoriesList"),
  paletteList: document.getElementById("paletteList"),
  stylingTipsList: document.getElementById("stylingTipsList"),
  alternativesList: document.getElementById("alternativesList"),
  retrievedMatches: document.getElementById("retrievedMatches"),
  personalityInput: document.getElementById("personalityInput"),
  budgetInput: document.getElementById("budgetInput"),
  occasionInput: document.getElementById("occasionInput"),
  placeInput: document.getElementById("placeInput"),
  weatherInput: document.getElementById("weatherInput"),
  colorInput: document.getElementById("colorInput"),
  styleInput: document.getElementById("styleInput"),
  issueInput: document.getElementById("issueInput")
};

function createSessionId() {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return "session-" + Date.now();
}

function ensureSession() {
  var stored = window.localStorage.getItem(SESSION_KEY);
  if (!stored) {
    stored = createSessionId();
    window.localStorage.setItem(SESSION_KEY, stored);
  }
  state.sessionId = stored;
  el.sessionBadge.textContent = "Session active";
}

function resetSession() {
  state.sessionId = createSessionId();
  window.localStorage.setItem(SESSION_KEY, state.sessionId);
  el.sessionBadge.textContent = "New session ready";
}

function nowStamp() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function createList(listEl, items, emptyText) {
  listEl.innerHTML = "";
  if (!items || !items.length) {
    var li = document.createElement("li");
    li.textContent = emptyText || "No details yet.";
    listEl.appendChild(li);
    return;
  }
  for (var i = 0; i < items.length; i++) {
    var item = document.createElement("li");
    item.textContent = items[i];
    listEl.appendChild(item);
  }
}

function createPalette(colors) {
  el.paletteList.innerHTML = "";
  if (!colors || !colors.length) {
    var empty = document.createElement("span");
    empty.textContent = "Awaiting color direction";
    el.paletteList.appendChild(empty);
    return;
  }
  for (var i = 0; i < colors.length; i++) {
    var swatch = document.createElement("span");
    swatch.textContent = colors[i];
    el.paletteList.appendChild(swatch);
  }
}

function showError(message) {
  el.errorBox.textContent = message;
  el.errorBox.classList.remove("hidden");
}

function clearError() {
  el.errorBox.textContent = "";
  el.errorBox.classList.add("hidden");
}

function showWarnings(warnings) {
  if (!warnings || !warnings.length) {
    el.warningBox.textContent = "";
    el.warningBox.classList.add("hidden");
    return;
  }
  el.warningBox.textContent = warnings.join(" ");
  el.warningBox.classList.remove("hidden");
}

function renderSlots() {
  el.slotStrip.innerHTML = "";
  var chips = [];
  if (state.knownSlots && state.knownSlots.length) {
    chips.push("Known: " + state.knownSlots.join(", "));
  }
  if (state.pendingSlot) {
    chips.push("Waiting for: " + state.pendingSlot);
  }
  if (!chips.length) {
    chips.push("Tell me the occasion and budget to get started.");
  }
  for (var i = 0; i < chips.length; i++) {
    var badge = document.createElement("span");
    badge.textContent = chips[i];
    el.slotStrip.appendChild(badge);
  }
}

function renderHistory() {
  el.chatHistory.innerHTML = "";
  for (var i = 0; i < state.history.length; i++) {
    var message = state.history[i];
    var row = document.createElement("div");
    row.className = "message-row " + message.role;

    var bubbleWrap = document.createElement("div");
    bubbleWrap.className = "message-wrap";

    var bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = message.content;

    var meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = (message.role === "user" ? "You" : "Fashion AI") + " • " + (message.timestamp || nowStamp());

    bubbleWrap.appendChild(bubble);
    bubbleWrap.appendChild(meta);
    row.appendChild(bubbleWrap);
    el.chatHistory.appendChild(row);
  }
  el.chatHistory.scrollTop = el.chatHistory.scrollHeight;
}

function renderRecommendation(data) {
  if (!data.recommendation) {
    el.sourceBadge.textContent = data.source || "clarification";
    return;
  }

  var rec = data.recommendation;
  el.recommendationTitle.textContent = rec.recommendation_title || "Your outfit direction";
  el.recommendationSummary.textContent = rec.summary || "";
  el.occasionMatch.textContent = rec.occasion_match || "-";
  el.personalityMatch.textContent = rec.personality_match || "-";
  el.budgetFit.textContent = rec.budget_fit || "-";
  el.confidenceSummary.textContent = rec.confidence_summary || "-";
  el.sourceBadge.textContent = data.source || "dataset-fallback";

  createList(el.mainItemsList, rec.main_outfit_items, "No items yet.");
  createList(el.layeringList, rec.layering, "No extra layers needed.");
  createList(el.footwearList, rec.footwear, "No footwear noted.");
  createList(el.accessoriesList, rec.accessories, "No accessories yet.");
  createList(el.stylingTipsList, rec.styling_tips, "No styling notes yet.");
  createList(el.alternativesList, rec.optional_alternatives, "No alternatives yet.");
  createPalette(rec.color_palette);

  el.retrievedMatches.innerHTML = "";
  var matches = data.retrieved_items || [];
  for (var i = 0; i < matches.length; i++) {
    var match = matches[i];
    var item = document.createElement("article");
    item.className = "match-item";
    var title = document.createElement("strong");
    title.textContent = match.recommended_outfit_title;
    var detail = document.createElement("p");
    detail.textContent = match.occasion + " | " + match.budget_category + " | " + match.style_vibe + " | retrieval " + Number(match.retrieval_score || 0).toFixed(2);
    item.appendChild(title);
    item.appendChild(detail);
    el.retrievedMatches.appendChild(item);
  }
}

function collectRequestBody(message) {
  return {
    session_id: state.sessionId,
    message: message,
    history: state.history.slice(-12),
    personality: el.personalityInput.value || null,
    budget: el.budgetInput.value || null,
    occasion: el.occasionInput.value || null,
    place: el.placeInput.value || null,
    weather: el.weatherInput.value || null,
    color_preference: el.colorInput.value || null,
    style_preference: el.styleInput.value || null,
    fashion_issue: el.issueInput.value || null
  };
}

function pushMessage(role, content) {
  state.history.push({ role: role, content: content, timestamp: nowStamp() });
  renderHistory();
}

function sendChat(message) {
  clearError();
  showWarnings([]);
  pushMessage("user", message);
  el.typingIndicator.classList.remove("hidden");

  fetch(API + "/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectRequestBody(message))
  })
    .then(function(res) {
      return res.json().then(function(payload) {
        if (!res.ok) {
          throw new Error(payload.detail || "Request failed.");
        }
        return payload;
      });
    })
    .then(function(data) {
      state.sessionId = data.session_id || state.sessionId;
      window.localStorage.setItem(SESSION_KEY, state.sessionId);
      state.knownSlots = data.known_slots || [];
      state.pendingSlot = data.pending_slot || null;
      pushMessage("assistant", data.reply || "Here is your recommendation.");
      showWarnings(data.warnings || []);
      renderRecommendation(data);
      renderSlots();
    })
    .catch(function(error) {
      showError(error.message || "Unexpected error");
    })
    .finally(function() {
      el.typingIndicator.classList.add("hidden");
    });
}

function loadHealth() {
  fetch(API + "/health")
    .then(function(res) { return res.json(); })
    .then(function(data) {
      el.healthBadge.textContent = data.llm_enabled ? "Gemini configured" : "Dataset mode";
      el.modelBadge.textContent = data.vector_store_ready ? ("Retrieval: " + data.vector_backend) : "Retrieval unavailable";
    })
    .catch(function() {
      el.healthBadge.textContent = "Backend offline";
      el.modelBadge.textContent = "Status unavailable";
    });
}

function loadPreferences() {
  fetch(API + "/preferences")
    .then(function(res) { return res.json(); })
    .then(function(data) {
      var hints = [];
      if (data.occasions && data.occasions.length) {
        hints.push("Popular occasions: " + data.occasions.slice(0, 4).join(", "));
      }
      if (data.style_vibes && data.style_vibes.length) {
        hints.push("Style moods: " + data.style_vibes.slice(0, 4).join(", "));
      }
      if (data.budgets && data.budgets.length) {
        hints.push("Budget buckets: " + data.budgets.join(", "));
      }

      el.preferenceHints.innerHTML = "";
      for (var i = 0; i < hints.length; i++) {
        var hint = document.createElement("span");
        hint.textContent = hints[i];
        el.preferenceHints.appendChild(hint);
      }
    })
    .catch(function() {
      el.preferenceHints.innerHTML = "";
    });
}

function resetState() {
  state.history = [];
  state.knownSlots = [];
  state.pendingSlot = null;
  resetSession();
  renderHistory();
  renderSlots();
  showWarnings([]);
  clearError();
  el.chatForm.reset();
  el.recommendationTitle.textContent = "Waiting for your brief";
  el.recommendationSummary.textContent = "Share your occasion and budget to receive a polished outfit recommendation.";
  el.occasionMatch.textContent = "-";
  el.personalityMatch.textContent = "-";
  el.budgetFit.textContent = "-";
  el.confidenceSummary.textContent = "-";
  el.sourceBadge.textContent = "preview";
  createList(el.mainItemsList, [], "No items yet.");
  createList(el.layeringList, [], "No extra layers needed.");
  createList(el.footwearList, [], "No footwear noted.");
  createList(el.accessoriesList, [], "No accessories yet.");
  createList(el.stylingTipsList, [], "No styling notes yet.");
  createList(el.alternativesList, [], "No alternatives yet.");
  createPalette([]);
  el.retrievedMatches.innerHTML = "";
}

el.chatForm.addEventListener("submit", function(event) {
  event.preventDefault();
  var message = el.messageInput.value.trim();
  if (!message) {
    return;
  }
  el.messageInput.value = "";
  sendChat(message);
});

el.clearButton.addEventListener("click", resetState);

var chips = document.querySelectorAll(".chip");
for (var i = 0; i < chips.length; i++) {
  chips[i].addEventListener("click", function() {
    var prompt = this.getAttribute("data-prompt");
    if (prompt) {
      sendChat(prompt);
    }
  });
}

ensureSession();
resetState();
loadHealth();
loadPreferences();
