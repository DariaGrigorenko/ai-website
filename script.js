const API_URL = "https://ai-website-exwx.onrender.com";

const themeToggle = document.getElementById("themeToggle");
const sitePreview = document.getElementById("sitePreview");
const statusBox = document.getElementById("statusBox");
const publicLinkBox = document.getElementById("publicLinkBox");
const aiSummary = document.getElementById("aiSummary");

const stages = [
  document.getElementById("stage1"),
  document.getElementById("stage2"),
  document.getElementById("stage3"),
  document.getElementById("stage4")
];

const indicators = [
  document.getElementById("step1Indicator"),
  document.getElementById("step2Indicator"),
  document.getElementById("step3Indicator"),
  document.getElementById("step4Indicator")
];

const projectDescription = document.getElementById("projectDescription");
const siteType = document.getElementById("siteType");
const goal = document.getElementById("goal");
const designPreferences = document.getElementById("designPreferences");
const desiredInfo = document.getElementById("desiredInfo");
const contactEmail = document.getElementById("contactEmail");
const contactPhone = document.getElementById("contactPhone");
const buttonCount = document.getElementById("buttonCount");
const regenerationNote = document.getElementById("regenerationNote");

let currentProject = null;
let currentPayload = null;
let generatedPublicLink = "";

function applySavedTheme() {
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light") {
    document.body.classList.add("light-theme");
    themeToggle.textContent = "Тёмная тема";
  } else {
    document.body.classList.remove("light-theme");
    themeToggle.textContent = "Светлая тема";
  }
}

themeToggle.addEventListener("click", function () {
  document.body.classList.toggle("light-theme");
  if (document.body.classList.contains("light-theme")) {
    localStorage.setItem("theme", "light");
    themeToggle.textContent = "Тёмная тема";
  } else {
    localStorage.setItem("theme", "dark");
    themeToggle.textContent = "Светлая тема";
  }
});

function showStage(number) {
  stages.forEach(stage => stage.classList.remove("active"));
  stages[number - 1].classList.add("active");

  indicators.forEach((indicator, index) => {
    indicator.classList.remove("active", "done");
    if (index + 1 < number) indicator.classList.add("done");
    if (index + 1 === number) indicator.classList.add("active");
  });
}

function updateStatus(text) {
  statusBox.textContent = text;
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function validateFirstStep() {
  const description = projectDescription.value.trim();
  if (!description || description.length < 10) {
    updateStatus("Введите описание проекта минимум 10 символов.");
    return false;
  }
  if (!goal.value) {
    updateStatus("Выберите главную цель сайта.");
    return false;
  }
  return true;
}

function buildPayload(extra = {}) {
  return {
    description: projectDescription.value.trim(),
    siteType: siteType.value,
    goal: goal.value,
    designPreferences: designPreferences.value.trim(),
    desiredInfo: desiredInfo.value.trim(),
    contactEmail: contactEmail.value.trim(),
    contactPhone: contactPhone.value.trim(),
    buttonCount: Number(buttonCount.value || 1),
    ...extra
  };
}

function renderLocalDraft() {
  sitePreview.innerHTML = `
    <div class="preview-empty">
      <div>
        <strong>ИИ подготовит сайт по этим данным:</strong><br><br>
        ${escapeHtml(projectDescription.value.trim())}<br><br>
        Тип сайта: ${escapeHtml(siteType.value)}<br>
        Цель: ${escapeHtml(goal.value)}
      </div>
    </div>
  `;
}

document.getElementById("nextToInfoBtn").addEventListener("click", function () {
  if (!validateFirstStep()) return;
  renderLocalDraft();
  updateStatus("Описание принято. Теперь укажи пожелания к оформлению, информацию, контакты и количество кнопок.");
  showStage(2);
});

document.getElementById("backToProjectBtn").addEventListener("click", function () {
  showStage(1);
  updateStatus("Можно изменить описание проекта или тип сайта.");
});

document.getElementById("generateSiteBtn").addEventListener("click", async function () {
  if (!validateFirstStep()) {
    showStage(1);
    return;
  }

  currentPayload = buildPayload();
  await generateSite(currentPayload, false);
});

document.getElementById("regenerateBtn").addEventListener("click", async function () {
  if (!currentProject || !currentProject.siteJson) {
    updateStatus("Сначала нужно сгенерировать первый вариант сайта.");
    return;
  }

  const note = regenerationNote.value.trim();
  const payload = buildPayload({
    previousSiteJson: currentProject.siteJson,
    regenerationNote: note || "Пользователю не понравился предыдущий вариант. Сделай заметно другой дизайн, структуру и тексты."
  });

  currentPayload = payload;
  await generateSite(payload, true);
});

document.getElementById("openGeneratedBtn").addEventListener("click", function () {
  openGeneratedLink();
});

async function generateSite(payload, isRegeneration) {
  showStage(3);
  publicLinkBox.classList.remove("visible");
  publicLinkBox.innerHTML = "";
  updateStatus(isRegeneration ? "ИИ перегенерирует сайт." : "ИИ генерирует сайт.");

  try {
    const response = await fetch(`${API_URL}/api/projects/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Backend error:", response.status, errorText);
      throw new Error(`Backend вернул ошибку: ${response.status}`);
    }

    const project = await response.json();
    currentProject = project;
    generatedPublicLink = project.fullPublicUrl;

    localStorage.setItem("currentProject", JSON.stringify(project));
    localStorage.setItem("generatedPublicLink", generatedPublicLink);

    renderGeneratedResult(project);
    showStage(4);
    updateStatus(isRegeneration ? "Новый вариант сайта готов." : "ИИ сгенерировал сайт. Можно посмотреть предпросмотр или перегенерировать.");
  } catch (error) {
    console.error("Ошибка генерации сайта:", error);
    showStage(4);
    sitePreview.innerHTML = `
      <div class="preview-empty">
        Не удалось сгенерировать сайт. Проверь Render Logs или попробуй ещё раз.
      </div>
    `;
    aiSummary.innerHTML = `<strong>Ошибка:</strong> ${escapeHtml(error.message)}`;
    updateStatus("Ошибка: сайт не был сгенерирован.");
  }
}

function renderGeneratedResult(project) {
  const siteJson = project.siteJson || {};
  const pages = Array.isArray(siteJson.siteMap) ? siteJson.siteMap : [];
  const contacts = siteJson.contact || {};

  const pagesHtml = pages.map(page => `
    <li><strong>${escapeHtml(page.title)}</strong> — ${escapeHtml(page.description || "")}</li>
  `).join("");

  aiSummary.innerHTML = `
    <strong>Сайт готов:</strong><br>
    Название: ${escapeHtml(siteJson.siteName || project.name)}<br>
    Тип: ${escapeHtml(siteJson.siteType || project.siteType)}<br>
    Контакты: ${escapeHtml(contacts.phone || "")} · ${escapeHtml(contacts.email || "")}
    <ul>${pagesHtml}</ul>
  `;

  sitePreview.innerHTML = `
    <iframe class="preview-frame" src="${escapeHtml(project.fullPublicUrl)}" title="Предпросмотр сайта"></iframe>
  `;

  publicLinkBox.classList.add("visible");
  publicLinkBox.innerHTML = `
    <strong>Ссылка на сайт готова</strong>
    <p>Эту ссылку можно открыть в браузере или отправить другому человеку.</p>
    <a href="${escapeHtml(project.fullPublicUrl)}" target="_blank" class="public-link">${escapeHtml(project.fullPublicUrl)}</a>
    <div class="public-link-actions">
      <button class="btn btn-primary" onclick="copyGeneratedLink()">Скопировать ссылку</button>
      <button class="btn btn-secondary" onclick="openGeneratedLink()">Открыть сайт</button>
    </div>
  `;
}

function copyGeneratedLink() {
  const link = generatedPublicLink || localStorage.getItem("generatedPublicLink");
  if (!link) {
    alert("Сначала сгенерируй сайт");
    return;
  }
  navigator.clipboard.writeText(link)
    .then(() => alert("Ссылка скопирована"))
    .catch(() => prompt("Скопируй ссылку вручную:", link));
}

function openGeneratedLink() {
  const link = generatedPublicLink || localStorage.getItem("generatedPublicLink");
  if (!link) {
    alert("Сначала сгенерируй сайт");
    return;
  }
  window.open(link, "_blank");
}

applySavedTheme();
