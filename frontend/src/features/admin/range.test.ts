import { describe, expect, it } from "vitest";
import { barPercents, rangeParams, shortDate } from "./range";

describe("rangeParams", () => {
  it("n ngày gần nhất gồm cả hai đầu", () => {
    expect(rangeParams(7, new Date(2026, 9, 5))).toEqual({
      date_from: "2026-09-29",
      date_to: "2026-10-05",
    });
    expect(rangeParams(1, new Date(2026, 9, 5))).toEqual({
      date_from: "2026-10-05",
      date_to: "2026-10-05",
    });
  });

  it("lùi qua ranh giới tháng đúng", () => {
    expect(rangeParams(30, new Date(2026, 2, 1)).date_from).toBe("2026-01-31");
  });

  it("dùng ngày theo giờ máy, không lệch sang UTC", () => {
    expect(rangeParams(1, new Date(2026, 9, 5, 0, 30)).date_to).toBe("2026-10-05");
  });
});

describe("shortDate", () => {
  it("đổi YYYY-MM-DD sang DD/MM", () => {
    expect(shortDate("2026-10-05")).toBe("05/10");
  });
});

describe("barPercents", () => {
  it("cột lớn nhất là 100%, ngày không có doanh thu là 0", () => {
    expect(barPercents([0, 50, 100])).toEqual([0, 50, 100]);
  });

  it("giá trị dương rất nhỏ vẫn có cột nhìn thấy được", () => {
    expect(barPercents([1, 1000])).toEqual([2, 100]);
  });

  it("toàn số 0 hoặc rỗng thì không chia cho 0", () => {
    expect(barPercents([0, 0, 0])).toEqual([0, 0, 0]);
    expect(barPercents([])).toEqual([]);
  });
});