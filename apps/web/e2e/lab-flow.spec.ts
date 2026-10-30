import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

// ожидаемые числа берём из контента, чтобы тест не ломался при добавлении заданий
const LABS_DIR = join(fileURLToPath(new URL(".", import.meta.url)), "..", "..", "..", "content", "labs");
const ALL = readdirSync(LABS_DIR);
const BLOCKED = ALL.filter((d) => /availability: (requires_|manual_review)/.test(readFileSync(join(LABS_DIR, d, "manifest.yaml"), "utf8"))).length;
const RUNNABLE = ALL.length - BLOCKED;

const PASSWORD = "correct-horse-battery";

async function register(page: Page) {
  const email = `e2e-${Date.now()}-${Math.floor(Math.random() * 1e5)}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Пароль/).fill(PASSWORD);
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(page.getByRole("heading", { name: /Привет/ })).toBeVisible();
  return email;
}

async function startLab(page: Page, labId: string) {
  await page.goto("/catalog");
  await page.getByTestId(`lab-${labId}`).click();
  await page.getByTestId("start-lab").click();
  await expect(page).toHaveURL(/\/workspace\//);
  await expect(page.getByTestId("terminal")).toHaveAttribute("data-state", "connected", { timeout: 60_000 });
}

async function typeInTerminal(page: Page, command: string) {
  await page.getByTestId("terminal").click();
  await page.keyboard.type(command, { delay: 5 });
  await page.keyboard.press("Enter");
}

// не оставляем запущенные песочницы после теста
test.afterEach(async ({ page }) => {
  const m = /\/workspace\/([0-9a-f-]{36})/.exec(page.url());
  if (!m) return;
  await page.evaluate(async (id) => {
    const csrf = document.cookie.split("; ").find((c) => c.startsWith("upskill_csrf="))?.split("=")[1] ?? "";
    await fetch(`/api/v1/sessions/${id}`, { method: "DELETE", credentials: "include", headers: { "X-CSRF-Token": csrf } });
  }, m[1]);
});

test("каталог показывает всю программу: запускаемые и описанные задания", async ({ page }) => {
  await register(page);
  await page.goto("/catalog");
  await expect(page.locator('[data-testid^="lab-"]')).toHaveCount(RUNNABLE);
  await expect(page.getByRole("heading", { name: "Этап 4. Синьор" })).toBeVisible();
  await page.getByLabel("Доступность").selectOption("");
  await expect(page.locator('[data-testid^="lab-"]')).toHaveCount(ALL.length);
  await page.getByLabel("Доступность").selectOption("unavailable");
  await expect(page.locator('[data-testid^="lab-"]')).toHaveCount(BLOCKED);
  await page.getByLabel("Доступность").selectOption("available");
  await page.getByLabel("Режим").selectOption("incident");
  const incidents = await page.locator('[data-testid^="lab-"]').count();
  expect(incidents).toBeGreaterThanOrEqual(5);
});

test("недоступное задание описано, но не запускается", async ({ page }) => {
  await register(page);
  await page.goto("/catalog");
  await page.getByLabel("Доступность").selectOption("unavailable");
  await page.locator('[data-availability="requires_vm"]').first().click();
  await expect(page.getByTestId("unavailable-reason")).toContainText("Запуск отключён");
  await expect(page.getByTestId("start-lab")).toBeDisabled();
});

test("новое задание программы проходит через UI (nb-001)", async ({ page }) => {
  await register(page);
  await page.goto("/labs/nb-001");
  await expect(page.getByText("Перед терминалом")).toBeVisible();
  await page.getByTestId("start-lab").click();
  await expect(page.getByTestId("terminal")).toHaveAttribute("data-state", "connected", { timeout: 60_000 });
  await typeInTerminal(page, "pwd > ~/answer.txt");
  await page.getByTestId("check").click();
  await expect(page).toHaveURL(/\/result\//, { timeout: 60_000 });
  await expect(page.getByTestId("result-xp")).toHaveText("+50 XP");
});

test("полный путь: регистрация → запуск → терминал → проверка → XP → повторный вход", async ({ page }) => {
  const email = await register(page);
  await startLab(page, "linux-001");

  // неверное состояние: проверка не проходит, подсказка и критерии видны
  await page.getByTestId("check").click();
  await expect(page.getByTestId("check-result")).toContainText("Пока не всё готово");
  await expect(page.getByTestId("check-result")).toContainText("✗");

  // реальный shell внутри песочницы
  await typeInTerminal(page, "echo RESULT=$((6*7)) && whoami");
  await expect(page.getByTestId("terminal")).toContainText("RESULT=42");
  await expect(page.getByTestId("terminal")).toContainText("student");

  // состояние шелла живёт в сессии: после перезагрузки страницы терминал переподключается к тому же PTY
  await typeInTerminal(page, "export MARK=survives");
  await page.reload();
  await expect(page.getByTestId("terminal")).toHaveAttribute("data-state", "connected", { timeout: 30_000 });
  await typeInTerminal(page, "echo AFTER=$MARK");
  await expect(page.getByTestId("terminal")).toContainText("AFTER=survives");

  // решение: любое корректное — проверяется итоговое состояние, а не команды
  await typeInTerminal(page, "cd ~/lab/src/app && pwd > ~/lab/answer.txt && mkdir ~/lab/notes");
  await page.getByTestId("check").click();
  await expect(page).toHaveURL(/\/result\//, { timeout: 60_000 });
  await expect(page.getByTestId("result-score")).toHaveText("100%");
  await expect(page.getByTestId("result-xp")).toHaveText("+50 XP");

  await page.getByRole("button", { name: "Выйти" }).click();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Пароль/).fill(PASSWORD);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByTestId("dash-xp")).toHaveText("50 XP");
  await page.goto("/profile");
  await expect(page.getByRole("link", { name: "Навигация по файловой системе" })).toBeVisible();
});

test("пользователь A не получает доступ к сессии пользователя B", async ({ page, browser }) => {
  await register(page);
  await startLab(page, "linux-001");
  const url = page.url();

  const other = await browser.newContext();
  const p2 = await other.newPage();
  await register(p2);
  await p2.goto(url);
  await expect(p2.getByRole("alert")).toBeVisible();
  await expect(p2.getByTestId("terminal")).toHaveCount(0);
  await other.close();
});

test("остановка лаборатории освобождает окружение", async ({ page }) => {
  await register(page);
  await startLab(page, "linux-001");
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Остановить" }).click();
  await expect(page.getByTestId("session-status")).toHaveAttribute("data-status", /STOPPING|STOPPED/, { timeout: 30_000 });
  await expect(page.getByTestId("session-status")).toHaveAttribute("data-status", "STOPPED", { timeout: 30_000 });
});

test("мобильная раскладка: вкладки «Задание / Терминал»", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await register(page);
  await startLab(page, "linux-001");
  await expect(page.getByRole("tab", { name: "Задание" })).toBeVisible();
  await page.getByRole("tab", { name: "Терминал" }).click();
  await expect(page.getByTestId("terminal")).toBeVisible();
});
