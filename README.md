# 🤺 Hiệp Sĩ Hắc Ám — Discord Bot

Discord bot game (RPG đấu trường) viết bằng Python + discord.py 2.7. Sẵn sàng deploy lên **Railway** từ **GitHub**.

---

## 🚀 Triển khai lên Railway (qua GitHub)

### Bước 1 — Đẩy code lên GitHub

```bash
cd knight-of-darkness-bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo>.git
git push -u origin main
```

### Bước 2 — Tạo project trên Railway

1. Vào https://railway.app → **New Project** → **Deploy from GitHub repo** → chọn repo vừa push.
2. Railway tự nhận diện Python qua `requirements.txt` + `.python-version` (Python 3.11) và đọc cấu hình ở `railway.toml` / `Procfile`.
3. Vào tab **Variables** → thêm biến:
   - `DISCORD_BOT_TOKEN` = token của bot (lấy từ Discord Developer Portal → Bot → Reset Token).
4. Bot sẽ tự build và start. Log hiện ra `Bot logged in as ...` là thành công.

### Bước 3 — Lưu data lâu dài (quan trọng!)

Filesystem của Railway **bị reset mỗi lần deploy**. File `data/data.json` (chỉ số người chơi, lore, quái) sẽ mất. Để giữ lại:

1. Trong project Railway → service của bot → tab **Settings** → **Volumes** → **+ New Volume**.
2. **Mount path**: `/app/data`
3. Save → redeploy. Từ giờ data sẽ persist qua mọi lần deploy.

### Bước 4 — Mời bot vào server Discord

1. Discord Developer Portal → Application của bạn → **OAuth2 → URL Generator**.
2. Scopes: `bot`, `applications.commands`.
3. Bot Permissions: `Send Messages`, `Embed Links`, `Manage Roles`, `Mention Everyone`.
4. Copy URL sinh ra → mở trên trình duyệt → chọn server → Authorize.
5. Trong Discord, gõ `/knightofdarkness` để mở sảnh chờ.

---

## 💻 Chạy thử local (tuỳ chọn)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Sửa .env, dán DISCORD_BOT_TOKEN
export DISCORD_BOT_TOKEN="..."     # hoặc dùng python-dotenv

python run_bot.py
```

---

## 📋 Lệnh trong Discord

- `/knightofdarkness` — triệu hồi sảnh chờ chính của Hiệp Sĩ Hắc Ám.

---

## 🎮 Tính năng

- **Hệ thống hạng I → V** (🕯 Tập Sự → ⚔️ Chiến Binh → 🩸 Săn Linh Hồn → 👁 Kỵ Sĩ Hắc Ấn → 👑 Chúa Tể Hắc Ám). Admin gắn role thưởng theo từng hạng. Lên hạng V → bot tag `@everyone`.
- **🛠 Luyện tập** — 3 mini-game: 🛡 Tank né đòn theo màu / 🗡 DPS bấm đúng thứ tự / 💊 Pha chế thần dược. Càng cao hạng càng được nhân điểm thưởng.
- **⚔️ PvE** — 5 cấp quái; chỉ đấu được cấp tương ứng với hạng (cho phép Hạng IV thách Boss V).
- **⚔️ PvP** — thư mời 1v1, cả channel xem trận, có cơ chế Tấn công / Phòng thủ / Crit / Block / Miss.
- **💬 Trò chuyện lore** — 4 chủ đề (lời chào mở đầu, lời chào kết thúc, đấu trường, bản thân). Random từ pool gồm câu mặc định + câu admin nhập.
- **🏅 Hệ thống thành tựu** (12 mốc): diệt 10/100/200/300/400/500 quái, hạ Boss, thắng 10 PvP liên tiếp ("Bất Bại"), đăng cơ Hạng II/III/IV/V.
- **🌐 Toggle ngôn ngữ EN/VI** lưu theo từng user.
- **🛡️ Bảng quản trị (admin only)**: thiết lập role thưởng, quản lý lore (4 chủ đề), quản lý quái vật, chỉnh sửa data người chơi, reset chỉ số người chơi về 0, reset toàn server.

---

## 📁 Cấu trúc dự án

```
knight-of-darkness-bot/
├── run_bot.py            # entry point
├── requirements.txt      # discord.py>=2.7.1
├── Procfile              # worker: python run_bot.py  (Railway/Heroku)
├── railway.toml          # config Railway
├── .python-version       # 3.11
├── .env.example
├── .gitignore
├── README.md
└── bot/
    ├── __init__.py
    ├── main.py           # khởi tạo bot, on_ready, slash command
    ├── core.py           # i18n, embed, monsters, ranks, công thức, lore, achievements
    ├── menu.py           # sảnh chờ + chat + bảng xếp hạng + thông tin cá nhân
    ├── combat.py         # PvE + PvP
    ├── training.py       # 3 mini-game luyện tập
    ├── admin.py          # bảng quản trị
    └── storage.py        # đọc/ghi data/data.json
```

> **Lưu ý:** thư mục `data/` sẽ tự được tạo khi bot chạy lần đầu. Trên Railway hãy mount Volume vào `/app/data` để giữ lại dữ liệu giữa các lần deploy (xem Bước 3 ở trên).
