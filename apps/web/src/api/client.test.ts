import { describe, expect, it } from "vitest";

import { ApiError, friendlyMessage, readCookie } from "./client";

describe("readCookie", () => {
  it("читает значение по имени", () => {
    expect(readCookie("upskill_csrf", "a=1; upskill_csrf=tok%3D1; b=2")).toBe("tok=1");
  });
  it("возвращает пустую строку, если cookie нет", () => {
    expect(readCookie("nope", "a=1")).toBe("");
  });
});

describe("friendlyMessage", () => {
  it("переводит известные коды в понятные сообщения", () => {
    expect(friendlyMessage(new ApiError(401, "INVALID_CREDENTIALS", "x"))).toMatch(/Неверный email/);
    expect(friendlyMessage(new ApiError(429, "TOO_MANY_SESSIONS", "x"))).toMatch(/Остановите/);
  });
  it("не раскрывает неизвестные ошибки сети", () => {
    expect(friendlyMessage(new TypeError("boom"))).toMatch(/связаться с сервером/);
  });
});
