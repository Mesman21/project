import { request } from "./api.js";
import { categories, feedback, validationError } from "./common.js";

const form = document.querySelector("#example-form");
const text = document.querySelector("#example-text");
const category = document.querySelector("#example-category");
const split = document.querySelector("#example-split");
const save = document.querySelector("#save-example");
const cancel = document.querySelector("#cancel-edit");
const formHeading = document.querySelector("#example-form-heading");
const formStatus = document.querySelector("#example-feedback");
const listStatus = document.querySelector("#examples-status");
const search = document.querySelector("#example-search");
const count = document.querySelector("#examples-count");
const list = document.querySelector("#example-list");
const template = document.querySelector("#example-row");
const dialog = document.querySelector("#delete-dialog");

let examples = [];
let editing = null;
let deleting = null;
let pending = false;
let requestNumber = 0;

function renderExamples() {
  const query = search.value.trim().toLocaleLowerCase("uk");
  const filtered = examples.filter(example =>
    example.text.toLocaleLowerCase("uk").includes(query),
  );
  count.textContent = examples.length ? filtered.length + " / " + examples.length : "";
  list.replaceChildren();
  for (const example of filtered) {
    const row = template.content.firstElementChild.cloneNode(true);
    row.dataset.id = example.message_id;
    row.querySelector(".example-text").textContent = example.text;
    const tag = row.querySelector(".tag");
    if (Object.hasOwn(categories, example.category_code)) {
      tag.classList.add(example.category_code);
    }
    tag.textContent = categories[example.category_code] ?? example.category_code;
    row.querySelector(".split").textContent = example.dataset_split === "train"
      ? "Навчальна" : "Перевірна";
    const actions = row.querySelector(".row-actions");
    if (example.locked) {
      const note = document.createElement("span");
      note.className = "small muted";
      note.textContent = "Використано в оцінюванні";
      actions.replaceChildren(note);
    }
    list.append(row);
  }
  if (!filtered.length) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = query ? "За цим запитом прикладів немає." : "Прикладів ще немає.";
    list.append(empty);
  }
}

export function resetExamples() {
  requestNumber++;
  examples = [];
  search.value = "";
  list.replaceChildren();
  count.textContent = "";
  feedback(listStatus);
  setEditing(null);
}

export async function loadExamples() {
  const number = ++requestNumber;
  feedback(listStatus, "Завантажуємо приклади…");
  list.replaceChildren();
  count.textContent = "";
  try {
    const data = await request("/examples");
    if (number !== requestNumber) return;
    examples = data;
    feedback(listStatus);
    renderExamples();
  } catch (error) {
    if (number !== requestNumber) return;
    examples = [];
    feedback(listStatus, error.message, "error");
  }
}

function setEditing(example) {
  editing = example?.message_id ?? null;
  text.value = example?.text ?? "";
  category.value = example?.category_code ?? "information_request";
  split.value = example?.dataset_split ?? "train";
  formHeading.textContent = editing ? "Редагувати приклад" : "Додати приклад";
  save.textContent = editing ? "Зберегти" : "Додати";
  cancel.hidden = editing === null;
  text.removeAttribute("aria-invalid");
  feedback(formStatus);
}

function setPending(value) {
  pending = value;
  for (const control of [text, category, split, save, cancel]) control.disabled = value;
}

export function bindExamples() {
  search.addEventListener("input", renderExamples);
  text.addEventListener("input", () => {
    text.removeAttribute("aria-invalid");
    feedback(formStatus);
  });
  cancel.addEventListener("click", () => setEditing(null));
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (pending) return;
    const error = validationError(text.value);
    if (error) {
      text.setAttribute("aria-invalid", "true");
      feedback(formStatus, error, "error");
      text.focus();
      return;
    }

    const body = {
      text: text.value.trim(),
      category_code: category.value,
      dataset_split: split.value,
    };
    const id = editing;
    setPending(true);
    feedback(formStatus, "Зберігаємо…");
    try {
      await request(id === null ? "/examples" : "/examples/" + id, {
        method: id === null ? "POST" : "PUT",
        body,
      });
      setEditing(null);
      feedback(formStatus, id === null ? "Приклад додано." : "Зміни збережено.", "success");
      await loadExamples();
    } catch (error) {
      feedback(formStatus, error.message, "error");
    } finally {
      setPending(false);
    }
  });
  list.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || pending) return;
    const item = examples.find(example =>
      example.message_id === Number(button.closest(".example-row").dataset.id),
    );
    if (!item || item.locked) return;
    if (button.classList.contains("edit-example")) {
      setEditing(item);
      text.focus();
    } else {
      deleting = item;
      dialog.returnValue = "cancel";
      document.querySelector("#delete-text").textContent = item.text;
      dialog.showModal();
    }
  });
  dialog.addEventListener("close", async () => {
    const item = deleting;
    deleting = null;
    if (dialog.returnValue !== "confirm" || !item) return;

    setPending(true);
    try {
      await request("/examples/" + item.message_id, { method: "DELETE" });
      if (editing === item.message_id) setEditing(null);
      await loadExamples();
      if (listStatus.dataset.state !== "error") {
        feedback(listStatus, "Приклад видалено.", "success");
      }
    } catch (error) {
      feedback(listStatus, error.message, "error");
    } finally {
      setPending(false);
    }
  });
}
