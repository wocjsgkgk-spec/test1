const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const baseUrl = process.env.TASKFLOW_BASE_URL || "http://127.0.0.1:8000";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let todos = [];
  let nextId = 1;

  await page.route("**/login", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }) });
  });

  await page.route("**/signup", async (route) => {
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }) });
  });

  // 인증이 필요한 API 대신, 브라우저 UI 흐름만 재현 가능한 메모리 API를 사용한다.
  await page.route("**/todos", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(todos) });
      return;
    }
    if (method === "POST") {
      const payload = route.request().postDataJSON();
      const todo = { id: nextId++, title: payload.title, due: payload.due, done: false };
      todos.unshift(todo);
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(todo) });
      return;
    }
    await route.fallback();
  });

  await page.route("**/todos/*/toggle", async (route) => {
    const id = Number(route.request().url().match(/todos\/(\d+)\/toggle$/)[1]);
    const todo = todos.find((item) => item.id === id);
    todo.done = !todo.done;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(todo) });
  });

  await page.goto(baseUrl, { waitUntil: "networkidle" });

  await page.getByLabel("이메일").fill("ui@example.com");
  await page.getByLabel("비밀번호").fill("password123");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: "로그아웃" }).waitFor();

  await page.getByPlaceholder("지금 해야 할 일을 적어보세요").fill("브라우저 완료 흐름 검증");
  await page.getByRole("button", { name: "추가" }).click();

  const item = page.locator(".todo-item", { hasText: "브라우저 완료 흐름 검증" });
  await item.waitFor();
  assert.equal(await item.locator(".todo-title").textContent(), "브라우저 완료 흐름 검증");

  await item.getByRole("button", { name: "완료 처리" }).click();
  await item.locator(".todo-title").waitFor();
  assert.equal(await item.evaluate((element) => element.classList.contains("is-done")), true);

  const decoration = await item.locator(".todo-title").evaluate(
    (element) => getComputedStyle(element).textDecorationLine,
  );
  assert.match(decoration, /line-through/);

  await browser.close();
  console.log("TaskFlow UI E2E passed: add todo and complete todo.");
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
