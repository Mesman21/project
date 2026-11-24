import "./styles.css";
import { ApiError, request } from "./api.js";
import { bindClassification, resetClassification } from "./classification.js";
import { feedback } from "./common.js";
import { bindExamples, loadExamples, resetExamples } from "./examples.js";
import { bindStatistics, loadStatistics, resetStatistics } from "./statistics.js";

const mock = import.meta.env.MODE === "mock";
const viewsByRole = {
  operator: ["classify"],
  coordinator: ["statistics"],
  maintainer: ["classify", "examples", "statistics"],
};
const roleNames = {
  operator: "Оператор",
  coordinator: "Координатор",
  maintainer: "Супровід",
};
const nav = document.querySelector("#app-navigation");
const links = [...nav.querySelectorAll("a")];
const views = [...document.querySelectorAll("[data-view]")];
const login = document.querySelector("#login-screen");
const loginForm = document.querySelector("#login-form");
const password = document.querySelector("#login-password");
const loginStatus = document.querySelector("#login-feedback");
const loginSubmit = document.querySelector("#login-submit");
const session = document.querySelector("#header-session");
const signOut = document.querySelector("#logout");
let account = null;

function showView() {
  const allowed = account ? viewsByRole[account.role] : [];
  const current = location.hash.slice(1);
  const active = allowed.includes(current) ? current : allowed[0];
  login.hidden = Boolean(account);
  nav.hidden = !account;
  session.hidden = mock || !account;
  for (const view of views) view.hidden = view.dataset.view !== active;
  for (const link of links) {
    const target = link.hash.slice(1);
    link.hidden = !allowed.includes(target);
    if (target === active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  if (active && current !== active) history.replaceState(null, "", "#" + active);
  if (active === "examples") loadExamples();
  if (active === "statistics") loadStatistics();
}

function setAccount(value) {
  account = value;
  if (value) {
    document.querySelector("#account-label").textContent = roleNames[value.role];
    loginForm.reset();
    feedback(loginStatus);
  } else {
    resetClassification();
    resetExamples();
    resetStatistics();
  }
  showView();
}

async function start() {
  if (mock) {
    document.querySelector("#demo-mode").hidden = false;
    setAccount({ role: "maintainer" });
    return;
  }
  try {
    setAccount(await request("/auth/me"));
  } catch (error) {
    setAccount(null);
    if (!(error instanceof ApiError && error.status === 401)) {
      feedback(loginStatus, error.message, "error");
    }
  }
}

loginForm.addEventListener("submit", async event => {
  event.preventDefault();
  loginSubmit.disabled = true;
  feedback(loginStatus, "Входимо…");
  try {
    setAccount(await request("/auth/login", {
      method: "POST",
      body: { username: document.querySelector("#login-name").value, password: password.value },
    }));
  } catch (error) {
    password.value = "";
    feedback(loginStatus, error.message, "error");
    password.focus();
  } finally {
    loginSubmit.disabled = false;
  }
});

signOut.addEventListener("click", async () => {
  signOut.disabled = true;
  try {
    await request("/auth/logout", { method: "POST" });
    setAccount(null);
  } catch (error) {
    document.querySelector("#account-label").textContent = error.message;
  } finally {
    signOut.disabled = false;
  }
});
window.addEventListener("session-expired", () => {
  setAccount(null);
  feedback(loginStatus, "Сеанс завершився. Увійдіть знову.", "error");
});
window.addEventListener("hashchange", showView);

bindClassification();
bindExamples();
bindStatistics();
start();
