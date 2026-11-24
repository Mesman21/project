export const categories = {
  information_request: "Інформаційний запит",
  incident_report: "Повідомлення про збій",
  suggestion: "Пропозиція",
};

export const maxLength = 2000;

export function lengthOf(text) {
  return [...text.trim()].length;
}

export function validationError(text) {
  if (!text.trim()) return "Введіть текст повідомлення.";
  if (lengthOf(text) > maxLength) return "Введіть до 2000 символів.";
  if (text.includes("\0")) return "Текст містить недопустимий символ.";
  return "";
}

export function feedback(element, text = "", state = "") {
  element.textContent = text;
  element.dataset.state = state;
}

export function categoryTag(code, name) {
  const tag = document.createElement("span");
  tag.className = "tag";
  if (Object.hasOwn(categories, code)) tag.classList.add(code);
  tag.textContent = name;
  return tag;
}
