import { request } from "./api.js";
import { categoryTag, feedback } from "./common.js";

const status = document.querySelector("#statistics-status");
const content = document.querySelector("#statistics-data");
const refresh = document.querySelector("#refresh-statistics");
const list = document.querySelector("#statistics-list");
const total = document.querySelector("#statistics-total");
const percent = new Intl.NumberFormat("uk", { style: "percent", maximumFractionDigits: 1 });

export function resetStatistics() {
  list.replaceChildren();
  total.textContent = "";
  content.hidden = true;
  feedback(status);
}

export async function loadStatistics() {
  if (refresh.disabled) return;
  refresh.disabled = true;
  content.hidden = true;
  feedback(status, "Завантажуємо статистику…");
  try {
    const data = await request("/statistics");
    if (!data.total) {
      feedback(status, "Зведення ще не сформовано.");
      return;
    }
    total.textContent = data.total;
    list.replaceChildren();
    for (const category of data.categories) {
      const row = document.createElement("li");
      const label = document.createElement("div");
      label.className = "stat-row";
      const value = document.createElement("strong");
      value.className = "small";
      value.textContent = category.count + " · " + percent.format(category.share);
      label.append(categoryTag(category.category_code, category.category_name), value);
      const bar = document.createElement("progress");
      bar.max = 1;
      bar.value = category.share;
      bar.setAttribute("aria-label", category.category_name);
      row.append(label, bar);
      list.append(row);
    }
    feedback(status);
    content.hidden = false;
  } catch (error) {
    feedback(status, error.message, "error");
  } finally {
    refresh.disabled = false;
  }
}

export function bindStatistics() {
  refresh.addEventListener("click", loadStatistics);
}
