const API_URL = "https://ai-website-exwx.onrender.com";

async function generateSite() {
  const description = document.getElementById("description").value.trim();
  const siteType = document.getElementById("siteType").value;
  const goal = document.getElementById("goal").value;
  const style = document.getElementById("style").value;

  const resultBlock = document.getElementById("generation-result");

  if (!description || description.length < 10) {
    resultBlock.innerHTML = `
      <p class="error-text">Введите описание проекта минимум 10 символов.</p>
    `;
    return;
  }

  resultBlock.innerHTML = `
    <p class="loading-text">Сайт генерируется...</p>
  `;

  try {
    const response = await fetch(`${API_URL}/api/projects/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        description,
        siteType,
        goal,
        style
      })
    });

    if (!response.ok) {
      throw new Error("Ошибка генерации сайта");
    }

    const project = await response.json();

    localStorage.setItem("currentProject", JSON.stringify(project));

    showGeneratedPreview(project.siteJson);

    resultBlock.innerHTML = `
      <div class="result-card">
        <h3>Сайт создан</h3>

        <p>
          Временная публичная ссылка готова. Её можно отправить другому человеку.
        </p>

        <a href="${project.fullPublicUrl}" target="_blank">
          ${project.fullPublicUrl}
        </a>

        <div class="result-actions">
          <button class="btn secondary" type="button" onclick="copyPublicLink()">
            Скопировать ссылку
          </button>

          <button class="btn primary" type="button" onclick="openPublicSite()">
            Открыть сайт
          </button>
        </div>
      </div>
    `;

  } catch (error) {
    resultBlock.innerHTML = `
      <p class="error-text">
        Не удалось сгенерировать сайт. Проверьте, запущен ли backend.
      </p>
    `;
  }
}

function showGeneratedPreview(siteJson) {
  const previewSection = document.getElementById("preview");

  let pagesHtml = "";

  siteJson.pages.forEach((page, index) => {
    pagesHtml += `
      <div class="page ${index === 0 ? "active" : ""}">
        <strong>${page.title}</strong>
        <p>${page.sections.map(section => section.type).join(", ")}</p>
      </div>
    `;
  });

  const firstPage = siteJson.pages[0];
  const heroSection = firstPage.sections.find(section => section.type === "hero");

  previewSection.innerHTML = `
    <div class="section-title">
      <h2>Сгенерированный сайт</h2>
      <p>Так выглядит результат генерации.</p>
    </div>

    <div class="preview-layout">
      <div class="sitemap">
        <h3>Карта сайта</h3>
        ${pagesHtml}
      </div>

      <div class="site-preview">
        <div class="browser-top">
          <span></span>
          <span></span>
          <span></span>
        </div>

        <div class="preview-content">
          <div class="preview-hero">
            <h3>${heroSection?.title || siteJson.siteName}</h3>
            <p>${heroSection?.subtitle || "Описание сайта"}</p>
            <button>${heroSection?.buttonText || "Оставить заявку"}</button>
          </div>

          <div class="preview-blocks">
            <div></div>
            <div></div>
            <div></div>
          </div>
        </div>
      </div>
    </div>
  `;

  previewSection.scrollIntoView({ behavior: "smooth" });
}

function copyPublicLink() {
  const project = JSON.parse(localStorage.getItem("currentProject"));

  if (!project) {
    alert("Сначала сгенерируйте сайт");
    return;
  }

  navigator.clipboard.writeText(project.fullPublicUrl);
  alert("Ссылка скопирована");
}

function openPublicSite() {
  const project = JSON.parse(localStorage.getItem("currentProject"));

  if (!project) {
    alert("Сначала сгенерируйте сайт");
    return;
  }

  window.open(project.fullPublicUrl, "_blank");
}
