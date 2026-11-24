import { request } from "./api.js";
import { categoryTag, feedback, lengthOf, maxLength, validationError } from "./common.js";

const form = document.querySelector("#classify-form");
const message = document.querySelector("#message");
const count = document.querySelector("#message-count");
const status = document.querySelector("#classify-feedback");
const submit = document.querySelector("#classify-submit");
const clear = document.querySelector("#clear-message");
const example = document.querySelector("#insert-example");
const result = document.querySelector("#prediction");
const emptyResult = [...result.children].map(node => node.cloneNode(true));

function resetPrediction() {
  result.replaceChildren(...emptyResult.map(node => node.cloneNode(true)));
}

function updateInput() {
  count.textContent = lengthOf(message.value) + " / " + maxLength;
  message.removeAttribute("aria-invalid");
  feedback(status);
  resetPrediction();
}

export function resetClassification() {
  message.value = "";
  updateInput();
}

export function bindClassification() {
  message.addEventListener("input", updateInput);
  example.addEventListener("click", () => {
    message.value = "Де можна переглянути розклад занять?";
    updateInput();
    message.focus();
  });
  clear.addEventListener("click", () => {
    message.value = "";
    updateInput();
    message.focus();
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const error = validationError(message.value);
    if (error) {
      message.setAttribute("aria-invalid", "true");
      feedback(status, error, "error");
      message.focus();
      return;
    }

    resetPrediction();
    for (const control of [message, submit, clear, example]) control.disabled = true;
    feedback(status, "Класифікуємо…");
    form.setAttribute("aria-busy", "true");
    try {
      const prediction = await request("/classify", {
        method: "POST",
        body: { text: message.value.trim() },
      });
      const icon = document.createElement("span");
      icon.className = "result-mark";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "✓";
      const name = document.createElement("strong");
      name.textContent = "Категорію визначено";
      result.replaceChildren(icon, name, categoryTag(
        prediction.category_code, prediction.category_name,
      ));
      feedback(status);
    } catch (error) {
      feedback(status, error.message, "error");
    } finally {
      for (const control of [message, submit, clear, example]) control.disabled = false;
      form.removeAttribute("aria-busy");
    }
  });
}
