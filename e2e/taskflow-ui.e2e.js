const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const baseUrl = process.env.TASKFLOW_BASE_URL || "http://127.0.0.1:8000";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let todos = [];
  let nextId = 1;
  const protectedRequests = [];

  await page.route("**/signup", async (route) => {
    const payload = route.request().postDataJSON();
    assert.equal(payload.email, "ui@example.com");
    assert.equal(payload.password, "password123");
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "signup-token",
        token_type: "bearer",
      }),
    });
  });

  await page.route("**/login", async (route) => {
    const payload = route.request().postDataJSON();
    assert.equal(payload.email, "ui@example.com");
    assert.equal(payload.password, "password123");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "login-token",
        token_type: "bearer",
      }),
    });
  });

  // 인증이 필요한 API 대신, 브라우저 UI 흐름만 재현 가능한 메모리 API를 사용한다.
  await page.route("**/todos", async (route) => {
    const method = route.request().method();
    protectedRequests.push(route.request().headers().authorization);
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
    protectedRequests.push(route.request().headers().authorization);
    const id = Number(route.request().url().match(/todos\/(\d+)\/toggle$/)[1]);
    const todo = todos.find((item) => item.id === id);
    todo.done = !todo.done;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(todo) });
  });

  await page.route("**/recommendations", async (route) => {
    protectedRequests.push(route.request().headers().authorization);
    assert.equal(route.request().method(), "POST");
    const pendingTodos = todos.filter((todo) => !todo.done);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        recommendations: pendingTodos.map((todo, index) => ({
          priority: index + 1,
          todo_id: todo.id,
          title: todo.title,
          due: todo.due,
          reason: "E2E 테스트용 추천입니다.",
        })),
      }),
    });
  });

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: "networkidle" });

  await page.getByLabel("이메일").fill("ui@example.com");
  await page.getByLabel("비밀번호").fill("password123");
  await page.getByRole("button", { name: "회원가입" }).click();
  await page.getByRole("button", { name: "로그아웃" }).waitFor();
  await page.getByText("가입 후 로그인했어요.").waitFor();

  await page.getByRole("button", { name: "로그아웃" }).click();
  await page.getByText("로그아웃했어요.").waitFor();

  await page.getByLabel("이메일").fill("ui@example.com");
  await page.getByLabel("비밀번호").fill("password123");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: "로그아웃" }).waitFor();
  await page.getByText("로그인했어요.").waitFor();

  await page.getByPlaceholder("지금 해야 할 일을 적어보세요").fill("브라우저 완료 흐름 검증");
  await page.getByRole("button", { name: "추가" }).click();

  const item = page.locator(".todo-item", { hasText: "브라우저 완료 흐름 검증" });
  await item.waitFor();
  assert.equal(await item.locator(".todo-title").textContent(), "브라우저 완료 흐름 검증");

  await page.getByRole("button", { name: "오늘 뭐부터?" }).click();
  const recommendation = page.locator(".recommendation-card", {
    hasText: "브라우저 완료 흐름 검증",
  });
  await recommendation.waitFor();
  assert.match(
    await recommendation.locator(".recommendation-reason").textContent(),
    /E2E 테스트용 추천/,
  );

  await item.getByRole("button", { name: "완료 처리" }).click();
  await item.locator(".todo-title").waitFor();
  assert.equal(await item.evaluate((element) => element.classList.contains("is-done")), true);

  const decoration = await item.locator(".todo-title").evaluate(
    (element) => getComputedStyle(element).textDecorationLine,
  );
  assert.match(decoration, /line-through/);
  assert.ok(
    protectedRequests.includes("Bearer signup-token"),
    "회원가입 직후 API 호출에 signup-token이 사용되어야 합니다.",
  );
  assert.ok(
    protectedRequests.includes("Bearer login-token"),
    "로그인 후 API 호출에 login-token이 사용되어야 합니다.",
  );

  await browser.close();
  console.log("TaskFlow UI E2E passed: signup, login, add todo, AI recommendation, complete todo.");
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
