"""
主爬蟲執行腳本：抓取四家影城場次並更新 movie_rows.json
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from crawlers import vscinemas, showtimes, skcinemas, ambassador


def run_all(days=14):
    all_rows = []
    errors = []

    for name, module in [
        ("威秀", vscinemas),
        ("秀泰", showtimes),
        ("新光", skcinemas),
        ("國賓", ambassador),
    ]:
        try:
            rows = module.crawl(days=days)
            all_rows.extend(rows)
            print(f"[{name}] ✓ {len(rows)} 筆")
        except Exception as e:
            print(f"[{name}] ✗ 失敗: {e}")
            errors.append(f"{name}: {e}")

    print(f"\n總計: {len(all_rows)} 筆場次")
    if errors:
        print("錯誤:", errors)
    return all_rows


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14, help="抓取未來幾天")
    parser.add_argument("--output", default="movie_rows.json", help="輸出檔案")
    args = parser.parse_args()

    rows = run_all(days=args.days)

    out_path = os.path.join(os.path.dirname(__file__), args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n已寫入 {out_path} ({len(rows)} 筆)")
