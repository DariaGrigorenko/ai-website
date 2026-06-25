const API_URL = "https://ai-website-exwx.onrender.com";

const themeToggle = document.getElementById("themeToggle");

const stage1 = document.getElementById("stage1");
const stage2 = document.getElementById("stage2");
const stage3 = document.getElementById("stage3");
const stage4 = document.getElementById("stage4");
const stage5 = document.getElementById("stage5");

const indicators = [
  document.getElementById("step1Indicator"),
  document.getElementById("step2Indicator"),
  document.getElementById("step3Indicator"),
  document.getElementById("step4Indicator"),
  document.getElementById("step5Indicator")
];

const sitePreview = document.getElementById("sitePreview");
const statusBox = document.getElementById("statusBox");
const publicLinkBox = document.getElementById("publicLinkBox");

const projectDescription = document.getElementById("projectDescription");
const siteType = document.getElementById("siteType");

const backgroundDescription = document.getElementById("backgroundDescription");
const backgroundStyle = document.getElementById("backgroundStyle");
const backgroundRating = document.getElementById("backgroundRating");

const layoutType = document.getElementById("layoutType");
const buttonPlace = document.getElementById("buttonPlace");
const layoutRating = document.getElementById("layoutRating");

const mainTitle = document.getElementById("mainTitle");
const mainText = document.getElementById("mainText");
const buttonText = document.getElementById("buttonText");
const extraInfo = document.getElementById("extraInfo");

let generatedPublicLink = "";

const state = {
  description: "",
  siteType: "",
  backgroundDescription: "",
  backgroundStyleText: "",
  backgroundClass: "bg-dark-red",
  layoutClass: "generated-layout-center",
  layoutText: "Центрированное размещение",
  buttonClass: "",
  buttonPlaceText: "Под главным текстом",
  title: "Будущий сайт",
  text: "Описание сайта появится здесь после добавления информации.",
  button: "Оставить заявку",
  extra: "Дополнительная информация появится здесь."
};

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
  const stages = [stage1, stage2, stage3, stage4, stage5];

  stages.forEach(stage => {
    stage.classList.remove("active");
  });

  stages[number - 1].classList.add("active");

  indicators.forEach((indicator, index) => {
    indicator.classList.remove("active");
    indicator.classList.remove("done");

    if (index + 1 < number) {
      indicator.classList.add("done");
    }

    if (index + 1 === number) {
      indicator.classList.add("active");
    }
  });
}

function updateStatus(text) {
  statusBox.textContent = text;
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderPreview() {
  sitePreview.innerHTML = `
    <div class="generated-site ${state.backgroundClass}">
      <div class="generated-inner ${state.layoutClass}">
        <div>
          <h2 class="generated-title">${escapeHtml(state.title)}</h2>
          <p class="generated-text">${escapeHtml(state.text)}</p>
          <button class="generated-button ${state.buttonClass}">
            ${escapeHtml(state.button)}
          </button>
        </div>

        <div class="generated-blocks">
          <div class="generated-block">
            <strong>О проекте</strong>
            <p>${escapeHtml(state.description || "Здесь будет описание проекта.")}</p>
          </div>

          <div class="generated-block">
            <strong>Преимущества</strong>
            <p>${escapeHtml(state.extra || "Здесь появятся преимущества или услуги.")}</p>
          </div>

          <div class="generated-block">
            <strong>Контакты</strong>
            <p>Здесь можно разместить адрес, телефон или форму заявки.</p>
          </div>
        </div>
      </div>
    </div>
  `;
}

document.getElementById("analyzeProjectBtn").addEventListener("click", async function () {
  const description = projectDescription.value.trim();

  if (!description || description.length < 10) {
    updateStatus("Введите описание проекта минимум 10 символов.");
    return;
  }

  this.disabled = true;
  this.textContent = "Чтение описания...";

  await wait(700);

  state.description = description;
  state.siteType = siteType.value;
  state.title = "Сайт по вашему описанию";
  state.text = "Описание проекта прочитано. Теперь можно настроить фон сайта.";

  renderPreview();

  updateStatus("Описание проекта прочитано. Теперь настрой фон сайта.");
  this.disabled = false;
  this.textContent = "Прочитать описание";

  showStage(2);
});

document.getElementById("generateBackgroundBtn").addEventListener("click", async function () {
  const description = backgroundDescription.value.trim();

  if (!description) {
    updateStatus("Опиши, каким должен быть фон сайта.");
    return;
  }

  this.disabled = true;
  this.textContent = "Генерация фона...";

  await wait(700);

  state.backgroundDescription = description;
  state.backgroundStyleText = backgroundStyle.options[backgroundStyle.selectedIndex].text;

  if (backgroundStyle.value === "dark-red") {
    state.backgroundClass = "bg-dark-red";
  }

  if (backgroundStyle.value === "minimal-light") {
    state.backgroundClass = "bg-minimal-light";
  }

  if (backgroundStyle.value === "business-dark") {
    state.backgroundClass = "bg-business-dark";
  }

  if (backgroundStyle.value === "creative") {
    state.backgroundClass = "bg-creative";
  }

  renderPreview();

  backgroundRating.classList.add("visible");
  updateStatus("Фон создан. Оцени его: подходит или нужно переделать.");

  this.disabled = false;
  this.textContent = "Сгенерировать фон";
});

document.getElementById("likeBackgroundBtn").addEventListener("click", function () {
  updateStatus("Фон принят. Теперь можно разместить кнопки и блоки.");
  showStage(3);
});

document.getElementById("remakeBackgroundBtn").addEventListener("click", function () {
  updateStatus("Измени описание или вариант фона и нажми “Сгенерировать фон” ещё раз.");
});

document.getElementById("generateLayoutBtn").addEventListener("click", async function () {
  this.disabled = true;
  this.textContent = "Размещение блоков...";

  await wait(700);

  state.layoutText = layoutType.options[layoutType.selectedIndex].text;
  state.buttonPlaceText = buttonPlace.options[buttonPlace.selectedIndex].text;

  if (layoutType.value === "center") {
    state.layoutClass = "generated-layout-center";
  }

  if (layoutType.value === "left") {
    state.layoutClass = "generated-layout-left";
  }

  if (layoutType.value === "cards") {
    state.layoutClass = "generated-layout-cards";
  }

  if (buttonPlace.value === "under-title") {
    state.buttonClass = "";
  }

  if (buttonPlace.value === "center") {
    state.buttonClass = "center-button";
  }

  if (buttonPlace.value === "bottom") {
    state.buttonClass = "bottom-button";
  }

  renderPreview();

  layoutRating.classList.add("visible");
  updateStatus("Кнопки и блоки размещены. Оцени расположение.");

  this.disabled = false;
  this.textContent = "Разместить блоки и кнопки";
});

document.getElementById("likeLayoutBtn").addEventListener("click", function () {
  updateStatus("Размещение принято. Теперь добавь информацию на сайт.");
  showStage(4);
});

document.getElementById("remakeLayoutBtn").addEventListener("click", function () {
  updateStatus("Измени расположение блоков или кнопки и нажми “Разместить блоки и кнопки” ещё раз.");
});

document.getElementById("addContentBtn").addEventListener("click", async function () {
  if (!mainTitle.value.trim() || !mainText.value.trim()) {
    updateStatus("Добавь хотя бы главный заголовок и основное описание.");
    return;
  }

  this.disabled = true;
  this.textContent = "Добавление информации...";

  await wait(700);

  state.title = mainTitle.value.trim();
  state.text = mainText.value.trim();
  state.button = buttonText.value.trim() || "Оставить заявку";
  state.extra = extraInfo.value.trim() || "Информация будет дополнена позже.";

  renderPreview();

  updateStatus("Информация добавлена. Теперь можно создать ссылку на финальный сайт.");

  this.disabled = false;
  this.textContent = "Добавить информацию";

  showStage(5);
});

document.getElementById("createLinkBtn").addEventListener("click", async function () {
  this.disabled = true;
  this.textContent = "Создание ссылки...";

  publicLinkBox.classList.add("visible");
  publicLinkBox.innerHTML = `
    <p>Отправляем финальный сайт в backend и создаём временную публичную ссылку...</p>
  `;

  updateStatus("Идёт создание публичной ссылки через backend.");

  try {
    const finalDescription = `
Описание проекта: ${state.description}

Тип сайта: ${state.siteType}

Фон:
${state.backgroundDescription}
Выбранный фон: ${state.backgroundStyleText}

Размещение:
${state.layoutText}
Кнопка: ${state.buttonPlaceText}

Информация:
Главный заголовок: ${state.title}
Основной текст: ${state.text}
Текст кнопки: ${state.button}
Дополнительная информация: ${state.extra}
    `;

    const response = await fetch(`${API_URL}/api/projects/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        description: finalDescription,
        siteType: state.siteType,
        goal: "Создать сайт по этапам",
        style: state.backgroundStyleText || "Пользовательский стиль"
      })
    });

    if (!response.ok) {
      throw new Error("Backend вернул ошибку");
    }

    const project = await response.json();

    generatedPublicLink = project.fullPublicUrl;
    localStorage.setItem("currentProject", JSON.stringify(project));
    localStorage.setItem("generatedPublicLink", generatedPublicLink);

    publicLinkBox.innerHTML = `
      <strong>Ссылка на сайт создана</strong>

      <p>
        Эту ссылку можно открыть в браузере или отправить другому человеку.
      </p>

      <a href="${generatedPublicLink}" target="_blank" class="public-link">
        ${generatedPublicLink}
      </a>

      <div class="public-link-actions">
        <button class="small-btn" onclick="copyGeneratedLink()">
          Скопировать ссылку
        </button>

        <button class="small-btn secondary-small" onclick="openGeneratedLink()">
          Открыть сайт
        </button>
      </div>
    `;

    updateStatus("Финальный сайт создан. Ссылка готова.");

  } catch (error) {
    publicLinkBox.innerHTML = `
      <strong>Ссылку создать не удалось</strong>
      <p>
        Проверь, что backend запущен по адресу ${API_URL}.
      </p>
    `;

    updateStatus("Ошибка: backend недоступен или вернул ошибку.");
  }

  this.disabled = false;
  this.textContent = "Создать ссылку на сайт";
});

document.getElementById("restartBtn").addEventListener("click", function () {
  location.reload();
});

function copyGeneratedLink() {
  const link = generatedPublicLink || localStorage.getItem("generatedPublicLink");

  if (!link) {
    alert("Сначала создай ссылку");
    return;
  }

  navigator.clipboard.writeText(link)
    .then(() => {
      alert("Ссылка скопирована");
    })
    .catch(() => {
      prompt("Скопируй ссылку вручную:", link);
    });
}

function openGeneratedLink() {
  const link = generatedPublicLink || localStorage.getItem("generatedPublicLink");

  if (!link) {
    alert("Сначала создай ссылку");
    return;
  }

  window.open(link, "_blank");
}

applySavedTheme();
