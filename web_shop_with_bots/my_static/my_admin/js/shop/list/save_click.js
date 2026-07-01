/**
 * save_click.js
 *
 * Верхняя кнопка "Сохранить" для changelist.
 *
 * Логика:
 * 1. Если есть стандартный блок .actions -> встраиваем кнопку туда справа.
 * 2. Если .actions нет -> вставляем кнопку в строку поиска (#changelist-search) справа.
 *
 * Работает только если на странице есть list_editable поля.
 */

document.addEventListener("DOMContentLoaded", function () {
  var formset = document.getElementById("changelist-form");
  if (!formset) return;

  var editableFields = formset.querySelectorAll(
    'td input:not([type="hidden"]):not([name="_selected_action"]), td select'
  );
  if (!editableFields.length) return;

  var realSaveButton = document.querySelector('#changelist-form input[name="_save"]');
  if (!realSaveButton) return;

  if (document.getElementById("save-action-button")) return;

  function buildSaveButton() {
    var btn = document.createElement("input");
    btn.id = "save-action-button";
    btn.type = "button";
    btn.className = "default";
    btn.value = "Сохранить";

    btn.addEventListener("click", function () {
      realSaveButton.click();
    });

    return btn;
  }

  var actionsDiv = document.querySelector(".actions");

  // Вариант 1: actions есть -> старое поведение
  if (actionsDiv) {
    actionsDiv.style.display = "flex";
    actionsDiv.style.alignItems = "center";
    actionsDiv.style.justifyContent = "space-between";
    actionsDiv.style.padding = "5px 0";
    actionsDiv.style.gap = "10px";

    var leftContainer = document.createElement("div");
    leftContainer.style.display = "flex";
    leftContainer.style.alignItems = "center";
    leftContainer.style.gap = "6px";

    var rightContainer = document.createElement("div");
    rightContainer.style.display = "flex";
    rightContainer.style.alignItems = "center";
    rightContainer.style.gap = "6px";

    var label = actionsDiv.querySelector("label");
    var goButton = actionsDiv.querySelector('button[name="index"]');
    var selectAcross = actionsDiv.querySelector('input[name="select_across"]');

    if (label) leftContainer.appendChild(label);
    if (selectAcross) leftContainer.appendChild(selectAcross);
    if (goButton) {
      goButton.style.display = "inline-block";
      leftContainer.appendChild(goButton);
    }

    rightContainer.appendChild(buildSaveButton());

    actionsDiv.innerHTML = "";
    actionsDiv.appendChild(leftContainer);
    actionsDiv.appendChild(rightContainer);
    return;
  }

  // Вариант 2: actions нет -> вставляем кнопку в строку поиска справа
  var searchForm = document.getElementById("changelist-search");
  if (!searchForm) return;

  var searchInner = searchForm.querySelector("div");
  if (!searchInner) return;

  searchForm.style.width = "100%";

  searchInner.style.display = "flex";
  searchInner.style.alignItems = "center";
  searchInner.style.justifyContent = "space-between";
  searchInner.style.gap = "10px";
  searchInner.style.width = "100%";

  var leftContainer = document.createElement("div");
  leftContainer.style.display = "flex";
  leftContainer.style.alignItems = "center";
  leftContainer.style.gap = "8px";
  leftContainer.style.flexWrap = "wrap";
  leftContainer.style.minWidth = "0";
  leftContainer.style.flex = "1";

  var rightContainer = document.createElement("div");
  rightContainer.style.display = "flex";
  rightContainer.style.alignItems = "center";
  rightContainer.style.flexShrink = "0";
  rightContainer.appendChild(buildSaveButton());

  Array.from(searchInner.childNodes).forEach(function (node) {
    leftContainer.appendChild(node);
  });

  searchInner.appendChild(leftContainer);
  searchInner.appendChild(rightContainer);
});
