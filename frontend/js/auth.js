import {apiFetch, getToken, setBusy, setSession, showMessage} from "/app/js/api.js";

if (getToken()) window.location.replace("/app/dashboard.html");

const message = document.querySelector("#form-message");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = loginForm.querySelector("button[type='submit']");
  setBusy(button, true, "Logging in…");
  const body = new URLSearchParams({username: loginForm.email.value.trim(), password: loginForm.password.value});
  try {
    const data = await apiFetch("/auth/login", {method: "POST", body});
    setSession(data);
    window.location.replace("/app/dashboard.html");
  } catch (error) {
    showMessage(message, error.message);
    setBusy(button, false);
  }
});

registerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = registerForm.querySelector("button[type='submit']");
  setBusy(button, true, "Creating account…");
  const body = JSON.stringify({full_name: registerForm.full_name.value.trim(), email: registerForm.email.value.trim(), password: registerForm.password.value});
  try {
    const data = await apiFetch("/auth/register", {method: "POST", body});
    setSession(data);
    window.location.replace("/app/dashboard.html");
  } catch (error) {
    showMessage(message, error.message);
    setBusy(button, false);
  }
});
