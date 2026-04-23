"""Core: i18n, embeds, game data, formulas, navigation helpers."""
import random
from dataclasses import dataclass

import discord

from .storage import get_locale, get_guild


# ============== EMBEDS ==============
DARK_COLOR = 0x1a0000
GOLD_COLOR = 0xc9a227
SHADOW_COLOR = 0x2f3136
KNIGHT_NAME = "🤺 Hiệp Sĩ Hắc Ám"


def knight_embed(text: str, *, title: str | None = None, color: int = DARK_COLOR) -> discord.Embed:
    """Embed lời thoại của Hiệp Sĩ Hắc Ám (KHÔNG dùng chữ in nghiêng)."""
    return discord.Embed(title=title or KNIGHT_NAME, description=text, color=color)


# ============== I18N ==============
# Each entry: (vi, en). Used for UI labels and bot dialogue.
TR = {
    # Lobby / nav
    "lobby_intro": ("Hỡi chiến binh dũng cảm, ta có thể giúp gì cho ngươi?",
                    "Brave warrior, how may I aid you?"),
    "exit_msg": ("🌕 Hẹn gặp lại ngươi trên chiến trường.",
                 "🌕 Farewell — until we meet again on the battlefield."),
    "btn_train": ("🛠 Luyện tập", "🛠 Train"),
    "btn_challenge": ("⚔️ Thách đấu", "⚔️ Challenge"),
    "btn_stats": ("📊 Xem thông tin cá nhân", "📊 My Stats"),
    "btn_board": ("🏆 Bảng xếp hạng", "🏆 Leaderboard"),
    "btn_chat": ("💬 Trò chuyện", "💬 Chat"),
    "btn_admin": ("🛡️ Quản lý (dành cho admin)", "🛡️ Admin Panel (admin only)"),
    "btn_exit": ("🚪 Thoát", "🚪 Exit"),
    "btn_lobby": ("🗿 Quay lại sảnh chờ", "🗿 Back to lobby"),
    "btn_back": ("◀ Quay lại", "◀ Back"),
    "btn_lang": ("🌐 EN / VI", "🌐 EN / VI"),
    # Stats
    "stats_rank": ("Hạng", "Rank"),
    "stats_wins": ("Số quái đã thắng", "Monsters defeated"),
    "stats_pvp_wins": ("Số trận PvP thắng", "PvP wins"),
    # Leaderboard
    "lb_pick": ("🏆 Ngươi muốn xem bảng xếp hạng nào?", "🏆 Which leaderboard do you wish to see?"),
    "lb_pve_btn": ("🐉 Bảng xếp hạng Diệt Quái", "🐉 Monster Slayer Leaderboard"),
    "lb_pvp_btn": ("⚔️ Bảng xếp hạng Đấu Sĩ", "⚔️ Duelist Leaderboard"),
    "btn_other_board": ("🏆 Bảng khác", "🏆 Other board"),
    "btn_pvp_challenge": ("⚔️ Thách đấu người chơi", "⚔️ Challenge Player"),
    "btn_pve_challenge": ("🐉 Thách đấu quái vật", "🐉 Challenge Monster"),
    "btn_tank_left":  ("◀️ Né trái",   "◀️ Dodge left"),
    "btn_tank_still": ("⏸️ Đứng yên",  "⏸️ Stand still"),
    "btn_tank_right": ("▶️ Né phải",   "▶️ Dodge right"),
    "msg_not_your_turn": ("Đây không phải lượt của ngươi.", "Not your turn."),
    "msg_only_summoner": ("Chỉ người triệu hồi ta mới có thể chọn.", "Only the one who summoned me may choose."),
    "msg_choose_train": ("Hãy chọn bài tập phù hợp:", "Choose your training:"),
    "msg_choose_next_foe": ("Hãy chọn đối thủ tiếp theo của ngươi:", "Choose your next opponent:"),
    "lb_pve_title": ("🐉 **Bảng xếp hạng Diệt Quái — Top 10**",
                     "🐉 **Monster Slayer Leaderboard — Top 10**"),
    "lb_pvp_title": ("⚔️ **Bảng xếp hạng Đấu Sĩ — Top 10**",
                     "⚔️ **Duelist Leaderboard — Top 10**"),
    "lb_empty": ("(Chưa có dữ liệu)", "(No data yet)"),
    # Challenge
    "challenge_intro": ("⚔️ Khát máu đã trỗi dậy trong ngươi. Hãy chọn đối thủ — đồng loại hay quái vật?",
                        "⚔️ Bloodlust stirs within you. Choose your foe — mortal or monster?"),
    "btn_pvp": ("⚔️ Thách đấu người chơi", "⚔️ Challenge a player"),
    "btn_pve": ("🐉 Thách đấu quái vật", "🐉 Challenge a monster"),
    "pve_pick_level": ("💀 Hãy chọn cấp bậc quái vật mà ngươi dám đối mặt. Càng cao… cái chết càng đến gần.",
                       "💀 Choose the level of monster you dare face. The higher you climb, the closer death draws."),
    "no_overrun": ("💀 Ngươi chưa đạt cấp tương ứng (chưa có role hạng) nên không thể thách đấu vượt cấp với quái. Hạng hiện tại của ngươi: **{rank}**.",
                   "💀 You have not yet earned the matching rank role, so you cannot challenge monsters above your rank. Your current rank: **{rank}**."),
    "no_rank_role_setup": ("💀 Server chưa thiết lập role thưởng cho hạng này. Hãy nhờ admin gắn role trước.",
                           "💀 The server has not configured a rank role yet. Ask an admin to set it up first."),
    # Chat
    "chat_intro": ("Ngươi muốn nói về điều gì?", "Of what do you wish to speak?"),
    "btn_chat_arena": ("🏛 Về đấu trường này", "🏛 About this arena"),
    "btn_chat_self": ("🌑 Về bản thân ngài", "🌑 About yourself"),
    "btn_chat_guide": ("📜 Hướng dẫn sử dụng đấu trường", "📜 Arena guide"),
    "btn_chat_again": ("💬 Hỏi điều khác", "💬 Ask something else"),
    # Rank up
    "rankup_title": ("🏆 THĂNG HẠNG!", "🏆 RANK UP!"),
    "rankup_text": ("🎉 {mention} vừa đạt hạng **{rank_name}**!\n\n_{speech}_\n\n🎁 **Phần thưởng:** Từ giờ mỗi lần luyện tập (Tank / DPS / Thần dược) sẽ nhận được điểm cộng nhiều hơn **+{bonus}%**.",
                    "🎉 {mention} has reached **{rank_name}**!\n\n_{speech}_\n\n🎁 **Reward:** From now on, each training session (Tank / DPS / Potion) grants **+{bonus}%** more points."),
    "rankup_top_text": ("✨🏆 @everyone — Hãy chiêm ngưỡng! {mention} đã đăng cơ ngôi vị **{rank_name}**! 🏆✨\n\n_{speech}_\n\n🎁 **Phần thưởng tối thượng:** Từ giờ mỗi lần luyện tập sẽ nhận được điểm cộng nhiều hơn **+{bonus}%**.",
                        "✨🏆 @everyone — Behold! {mention} has ascended to **{rank_name}**! 🏆✨\n\n_{speech}_\n\n🎁 **Supreme reward:** From now on, each training session grants **+{bonus}%** more points."),
    # Training menu
    "train_choose": ("Hãy chọn bài tập phù hợp:", "Choose your training:"),
    "btn_train_tank": ("Nâng chỉ số 🛡 Tank", "Raise 🛡 Tank"),
    "btn_train_dps": ("Nâng chỉ số 🗡 DPS", "Raise 🗡 DPS"),
    "btn_train_potion": ("Pha chế 💊 Thần dược", "Brew 💊 Potions"),
    # Training — Tank
    "tank_intro": (
        "🛡 Bài luyện tập sắp đầu. Đối thủ của ngươi là **☠️ Đấu sĩ xương khô**. Hãy chuẩn bị sẵn sàng!\n\n"
        "Hướng dẫn: Hãy chú ý **màu của chiêu thức** sắp được tung ra. "
        "Bấm nút 🛡 trùng màu với màu trong lời thoại để né đòn.\n"
        "Một lần luyện tập kéo dài **5 lượt**, mỗi lượt khoảng **3 giây**.",
        "🛡 Training begins. Your opponent: **☠️ Bone Duelist**. Prepare yourself!\n\n"
        "Guide: Watch the **color of the incoming strike**. "
        "Press the 🛡 button matching the color in the prompt to dodge.\n"
        "One session lasts **5 rounds**, roughly **3 seconds** each."
    ),
    "tank_ready_btn": ("💥 Đã rõ", "💥 Ready"),
    "tank_round": (
        "☠️ **Lượt {turn}/5** — Đấu sĩ xương khô sắp **{label} tấn công ngươi**, ngươi sẽ né phía nào?\n\nBấm nút trùng màu để né.",
        "☠️ **Round {turn}/5** — The Bone Duelist is about to strike with **{label}**. Which way do you dodge?\n\nPress the matching color to evade."
    ),
    "tank_result_great": ("🌟 Ngươi đã né hầu hết các đòn ({score}/5). **+{gain} 🛡 Tank**",
                          "🌟 You dodged most strikes ({score}/5). **+{gain} 🛡 Tank**"),
    "tank_result_ok": ("🛡 Tạm được, vẫn cần rèn thêm ({score}/5). **+{gain} 🛡 Tank**",
                       "🛡 Decent, but you need more practice ({score}/5). **+{gain} 🛡 Tank**"),
    "tank_result_fail": ("💀 Ngươi đã trúng quá nhiều đòn ({score}/5). **Không có điểm nào.**",
                         "💀 You took too many hits ({score}/5). **No points awarded.**"),
    "tank_result_title": ("**Kết quả luyện tập 🛡 Tank**", "**🛡 Tank Training Result**"),
    # Training — DPS
    "dps_intro": (
        "🗡 **🤺 Hiệp Sĩ Hắc Ám tự mình hướng dẫn chiêu thức cho ngươi. Hãy tập trung quan sát!**\n\n"
        "🔥 Đừng dừng lại. Chỉ một nhịp sai… và ngươi sẽ mất mạng.\n\n"
        "Ta sẽ ra một chuỗi 4 chiêu thức. Ngươi phải bấm **đúng thứ tự** trong **10 giây**.\n"
        "Một lần luyện tập kéo dài **5 lượt**.",
        "🗡 **🤺 The Dark Knight demonstrates the techniques himself. Pay close attention!**\n\n"
        "🔥 Do not falter. One wrong beat… and you will die.\n\n"
        "I will show you a sequence of 4 moves. You must press them **in exact order** within **10 seconds**.\n"
        "One session lasts **5 rounds**."
    ),
    "dps_ready_btn": ("💥 Đã rõ", "💥 Ready"),
    "dps_round": (
        "⚔️ **Lượt {turn}/5** — Hãy bấm theo đúng thứ tự sau đây:\n\n# {seq}\n\nNgươi có 10 giây.",
        "⚔️ **Round {turn}/5** — Press in exactly this order:\n\n# {seq}\n\nYou have 10 seconds."
    ),
    "dps_result_perfect": ("🌟 🤺 Chiêu thức hoàn mỹ.  **+{gain} 🗡 DPS**",
                           "🌟 🤺 Flawless technique.  **+{gain} 🗡 DPS**"),
    "dps_result_ok": ("🗡 Cần cải thiện thêm, nhưng vẫn được.  **+{gain} 🗡 DPS**",
                      "🗡 Needs improvement, but acceptable.  **+{gain} 🗡 DPS**"),
    "dps_result_fail": ("💀 Chiêu thức rối loạn. Ngươi đã thua.  **+0 🗡 DPS**",
                        "💀 Your technique crumbled. Defeated.  **+0 🗡 DPS**"),
    "dps_result_title": ("**Kết quả luyện tập 🗡 DPS** (sai {fails}/5 lượt)",
                         "**🗡 DPS Training Result** ({fails}/5 rounds failed)"),
    # Training — Potion
    "potion_intro": (
        "⚗️ 🤺 Hiệp sĩ ma dẫn ngươi vào **Lò giả kim**:\n\n"
        "Ngươi cần gom đúng **ba nguyên liệu** để pha chế mỗi mẻ Thần dược. "
        "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
        "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**\n"
        "Kẻ nào sở hữu càng nhiều Thần dược, tỉ lệ sinh tồn của hắn trên chiến trường càng cao.\n\n"
        "**Hãy chọn nguyên liệu:**",
        "⚗️ 🤺 The phantom knight leads you into the **Alchemy Forge**:\n\n"
        "You need exactly **three ingredients** to brew each batch of Potions. "
        "**Each ingredient affects the success chance, "
        "but the same ingredient may yield different quality each time — take note.**\n"
        "The more Potions you carry, the higher your odds of survival on the battlefield.\n\n"
        "**Choose your ingredients:**"
    ),
    "potion_alchemy_title": ("⚗️ **Lò giả kim**", "⚗️ **Alchemy Forge**"),
    "potion_alchemy_note": (
        "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
        "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**",
        "**Each ingredient affects the success chance, "
        "but the same ingredient may yield different quality — take note.**"
    ),
    "potion_chosen": ("**Đã chọn ({count}/3):**", "**Selected ({count}/3):**"),
    "potion_none_chosen": ("(Chưa chọn nguyên liệu nào)", "(No ingredients selected yet)"),
    "potion_brew_btn": ("⚗️ Bào chế", "⚗️ Brew"),
    "potion_reset_btn": ("↺ Làm lại", "↺ Reset"),
    "potion_warn_full": (
        "⚠️ **Cảnh báo:** Ngươi đã chọn đủ **3 nguyên liệu**. "
        "Một mẻ Thần dược chỉ chấp nhận đúng ba nguyên liệu — không thể thêm nữa. "
        "Hãy bấm **⚗️ Bào chế** hoặc làm lại từ đầu.",
        "⚠️ **Warning:** You have already chosen **3 ingredients**. "
        "A Potion batch only accepts exactly three — no more can be added. "
        "Press **⚗️ Brew** or reset to start over."
    ),
    "potion_result_fail": ("💔 Tổng điểm: **{total}** — Ngươi không chế được lọ thần dược nào.",
                           "💔 Total score: **{total}** — The brew yielded nothing."),
    "potion_result_2": ("⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **2 lọ thần dược**. **+{gain} 💊 Health**",
                        "⚗️⚗️ Total score: **{total}** — You brewed **2 potions**. **+{gain} 💊 Health**"),
    "potion_result_3": ("⚗️⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **3 lọ thần dược**. **+{gain} 💊 Health**",
                        "⚗️⚗️⚗️ Total score: **{total}** — You brewed **3 potions**. **+{gain} 💊 Health**"),
    "potion_result_5": ("⚗️⚗️⚗️⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **5 lọ thần dược**! **+{gain} 💊 Health**",
                        "⚗️⚗️⚗️⚗️⚗️ Total score: **{total}** — You brewed **5 potions**! **+{gain} 💊 Health**"),
    "potion_result_title": ("**Kết quả pha chế thần dược**", "**Potion Brewing Result**"),
    # Training — after
    "btn_train_again": ("🛠 Luyện tập tiếp", "🛠 Train again"),
    "train_bonus_note": ("_(Hạng **{rank}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_",
                         "_(Rank **{rank}** — training bonus applied: **+{bonus}%**.)_"),
    # PvE
    "pve_level_pick_title": ("**{label}** — Hãy chọn đối thủ:", "**{label}** — Choose your foe:"),
    "pve_ready_title": ("⚔️ **Chuẩn bị trận chiến**", "⚔️ **Battle Preparation**"),
    "pve_ready_body": (
        "**Đối thủ:** {monster_display} _(Cấp {level})_\n"
        "🛡 Tank `{m_tank}` | 🗡 DPS `{m_dps}` | 💊 HP `{m_hp}`\n\n"
        "**Ngươi:** {player_name}\n"
        "🛡 Tank `{p_tank}` | 🗡 DPS `{p_dps}` | 💊 HP `{p_hp}`\n\n"
        "_Hít một hơi sâu… và bấm **💥 Vào trận** khi đã sẵn sàng. Một khi đã ra khỏi sảnh chờ, sẽ không có đường lui._",
        "**Opponent:** {monster_display} _(Level {level})_\n"
        "🛡 Tank `{m_tank}` | 🗡 DPS `{m_dps}` | 💊 HP `{m_hp}`\n\n"
        "**You:** {player_name}\n"
        "🛡 Tank `{p_tank}` | 🗡 DPS `{p_dps}` | 💊 HP `{p_hp}`\n\n"
        "_Take a deep breath… then press **💥 Enter Battle** when you are ready. Once you leave the lobby, there is no turning back._"
    ),
    "btn_enter_battle": ("💥 Vào trận", "💥 Enter Battle"),
    "battle_turn": ("⚔️ **Lượt {turn}** — Hãy ra quyết định.", "⚔️ **Round {turn}** — Make your choice."),
    "battle_last_round": ("__**Lượt vừa rồi:**__", "__**Last round:**__"),
    "btn_attack": ("🗡 Tấn công", "🗡 Attack"),
    "btn_defend": ("🛡 Phòng thủ", "🛡 Defend"),
    "btn_flee": ("🚪 Bỏ trận", "🚪 Flee"),
    "pve_win": (
        "🌟 Ngươi là kẻ sống sót cuối cùng.\n\n"
        "⚔️ Hạ gục **{monster_display}** (Cấp {level}) — **+{bonus} điểm chiến công**\n"
        "💊 Máu còn lại: {hp}/{max_hp}",
        "🌟 You are the last one standing.\n\n"
        "⚔️ Defeated **{monster_display}** (Level {level}) — **+{bonus} merit points**\n"
        "💊 HP remaining: {hp}/{max_hp}"
    ),
    "pve_rankup_inline": ("\n\n🏆 **THĂNG HẠNG!** Giờ đây ngươi là **{rank_name}**\n{speech}",
                          "\n\n🏆 **RANK UP!** You are now **{rank_name}**\n{speech}"),
    "pve_lose": (
        "💀 💊 Sinh mệnh của ngươi… đã cạn.\n\nNgươi đã ngã xuống dưới tay **{monster_display}**.",
        "💀 💊 Your life force… has been extinguished.\n\nYou have fallen at the hands of **{monster_display}**."
    ),
    "pve_fled": (
        "🏃 Ngươi đã bỏ chạy khỏi trận đấu với **{monster_display}**. "
        "Một hiệp sĩ thực sự không bao giờ quay lưng…",
        "🏃 You fled from battle against **{monster_display}**. "
        "A true knight never turns their back…"
    ),
    "btn_fight_again": ("⚔️ Đấu tiếp", "⚔️ Fight again"),
    "post_battle_next": ("Hãy chọn đối thủ tiếp theo của ngươi:", "Choose your next opponent:"),
    # PvP
    "pvp_choose_next": ("Hãy chọn đối thủ tiếp theo của ngươi:", "Choose your next opponent:"),
    "pvp_invite_title": ("⚔️ **Thư mời thách đấu**", "⚔️ **Challenge Invitation**"),
    "pvp_invite_body": (
        "{target_mention}, **{challenger_name}** thách đấu ngươi 1v1!\n"
        "{target_name}, ngươi có dám chấp nhận?",
        "{target_mention}, **{challenger_name}** challenges you to a 1v1 duel!\n"
        "{target_name}, do you dare accept?"
    ),
    "pvp_no_target": ("💀 Không tìm được đối thủ. Hãy thử lại với @mention hoặc ID.",
                      "💀 Could not find that opponent. Try again with a @mention or ID."),
    "pvp_self": ("💀 Ngươi không thể thách đấu chính mình.", "💀 You cannot challenge yourself."),
    "pvp_not_found": ("💀 Kẻ đó không có mặt trong vương quốc này.",
                      "💀 That person is not present in this realm."),
    "pvp_is_bot": ("💀 Ngươi không thể thách đấu một bot.", "💀 You cannot challenge a bot."),
    "pvp_accept_btn": ("✅ Đồng ý", "✅ Accept"),
    "pvp_decline_btn": ("🚪 Từ chối", "🚪 Decline"),
    "pvp_declined": ("{target_name} đã từ chối thách đấu của {challenger_name}.",
                     "{target_name} has declined {challenger_name}'s challenge."),
    "pvp_ready_status": (
        "⚔️ **Cả hai đấu sĩ đã đối mặt nhau giữa đấu trường…**\n\n"
        "{c_mark} **{challenger_name}**\n"
        "{t_mark} **{target_name}**\n\n"
        "_Cả hai phải bấm **💥 Vào trận** thì trận tử chiến mới bắt đầu._",
        "⚔️ **Both warriors face each other in the arena…**\n\n"
        "{c_mark} **{challenger_name}**\n"
        "{t_mark} **{target_name}**\n\n"
        "_Both must press **💥 Enter Battle** for the deathmatch to begin._"
    ),
    "pvp_already_ready": ("Ngươi đã sẵn sàng rồi — chờ đối thủ.", "You are already ready — waiting for your opponent."),
    "pvp_not_combatant": ("Ngươi không phải là một trong hai đấu sĩ.", "You are not one of the two combatants."),
    "pvp_withdraw_btn": ("🚪 Rút lui", "🚪 Withdraw"),
    "pvp_withdrew": (
        "**{name}** đã rút lui khỏi đấu trường. Trận tử chiến không xảy ra.",
        "**{name}** has withdrawn from the arena. The deathmatch did not take place."
    ),
    "pvp_announce": (
        "@everyone ⚔️ **Đấu trường rung chuyển!** "
        "{c_mention} vs {t_mention} — hãy tới chứng kiến trận tử chiến 1vs1!",
        "@everyone ⚔️ **The arena trembles!** "
        "{c_mention} vs {t_mention} — witness the 1v1 deathmatch!"
    ),
    "pvp_spectator_title": (
        "👁 **Trực tiếp đấu trường — {n1} vs {n2}**",
        "👁 **Live from the arena — {n1} vs {n2}**"
    ),
    "pvp_spectator_waiting": (
        "_Hai đấu sĩ đang vào sân… (chỉ xem, không can thiệp được)_",
        "_The combatants are entering the field… (spectators only — no interference)_"
    ),
    "pvp_spectator_round": (
        "⚔️ **Lượt {turn}/{max_turns}** — đang diễn ra…",
        "⚔️ **Round {turn}/{max_turns}** — in progress…"
    ),
    "pvp_thread_intro": (
        "⚔️ **Phòng đấu riêng** — chỉ {c_mention} và {t_mention} thấy giao diện này.\n"
        "Người xem khác chỉ có thể theo dõi qua tin nhắn cập nhật ngoài kênh.",
        "⚔️ **Private duel room** — only {c_mention} and {t_mention} see this UI.\n"
        "Spectators follow the live status posted in the main channel."
    ),
    "pvp_final_announce": (
        "@everyone 🏆 **Kết thúc trận tử chiến** — {c_mention} vs {t_mention}",
        "@everyone 🏆 **The deathmatch has ended** — {c_mention} vs {t_mention}"
    ),
    "pvp_round_header": (
        "⚔️ **Lượt {turn}** — Cả hai hãy chọn (30 giây).\n\n"
        "**{s1_name}** 💊 `{s1_bar}` {s1_hp}/{s1_max_hp}\n"
        "**{s2_name}** 💊 `{s2_bar}` {s2_hp}/{s2_max_hp}",
        "⚔️ **Round {turn}** — Both choose (30 seconds).\n\n"
        "**{s1_name}** 💊 `{s1_bar}` {s1_hp}/{s1_max_hp}\n"
        "**{s2_name}** 💊 `{s2_bar}` {s2_hp}/{s2_max_hp}"
    ),
    "pvp_round_last": ("__**Lượt vừa rồi:**__", "__**Last round:**__"),
    "pvp_not_participating": ("Ngươi không tham chiến.", "You are not participating in this battle."),
    "pvp_already_chose": ("Ngươi đã chọn rồi.", "You have already made your choice."),
    "pvp_recorded_atk": ("Đã ghi nhận: 🗡 Tấn công", "Recorded: 🗡 Attack"),
    "pvp_recorded_def": ("Đã ghi nhận: 🛡 Phòng thủ", "Recorded: 🛡 Defend"),
    "pvp_result_draw": ("💀 Cả hai đều ngã xuống.", "💀 Both warriors have fallen."),
    "pvp_result_win": ("🏆 **{winner}** chiến thắng! 💀 {loser}, sinh mệnh của ngươi… đã cạn.",
                       "🏆 **{winner}** is victorious! 💀 {loser}, your life force… has been extinguished."),
    "pvp_result_stalemate": ("Trận đấu kết thúc trong bế tắc.", "The battle ends in a stalemate."),
    # Battle combat lines
    "battle_miss": ("💀 🗡 {name} đánh trượt!", "💀 🗡 {name} missed!"),
    "battle_block": ("🌟 🛡 {name} chặn đứng đòn đánh.", "🌟 🛡 {name} blocked the strike."),
    "battle_defense_broken": ("💀 🛡 Phòng thủ của {name} sụp đổ! 🗡 {attacker} gây **-{dmg} HP**.",
                               "💀 🛡 {name}'s defense crumbles! 🗡 {attacker} deals **-{dmg} HP**."),
    "battle_crit": ("🌟 🗡 {attacker} **CRIT** lên {name}! **-{dmg} HP**",
                    "🌟 🗡 {attacker} **CRIT** on {name}! **-{dmg} HP**"),
    "battle_overpow": ("🗡 {attacker} áp đảo {name}. **-{dmg} HP**",
                       "🗡 {attacker} overpowers {name}. **-{dmg} HP**"),
    "battle_parried": ("💀 Đòn của {attacker} bị {name} vượt qua.", "💀 {name} parries {attacker}'s blow."),
    "battle_heal": ("💊 Cả hai lùi lại… củng cố sinh lực. {p_name} **+{ph} HP**, {e_name} **+{eh} HP**.",
                    "💊 Both sides fall back… recovering. {p_name} **+{ph} HP**, {e_name} **+{eh} HP**."),
    "pvp_both_decide": ("⚔️ Cả hai đã ra quyết định…", "⚔️ Both have made their decisions…"),
    # Menu — only invite modal selector
    "pvp_modal_label": ("ID hoặc @mention của đối thủ", "Opponent's ID or @mention"),
    "pvp_modal_placeholder": ("Nhập user ID hoặc dán mention <@123...>",
                               "Enter user ID or paste a mention <@123...>"),
    # Achievements
    "ach_header_empty": ("🏅 **Thành tựu:** _(chưa có thành tựu nào — hãy ra trận!)_",
                         "🏅 **Achievements:** _(none yet — get out there and fight!)_"),
    "ach_header": ("🏅 **Thành tựu đã đạt:**", "🏅 **Achievements Unlocked:**"),
    "ach_new_header": ("🎖 **Thành tựu mới mở khoá!**", "🎖 **New Achievement Unlocked!**"),
    # Menu — train description
    "pick_train": ("Hãy chọn bài tập phù hợp:", "Choose your training:"),
    # Admin panel title (for menu.py)
    "admin_panel_title": (
        "🛡️ **Bảng quản trị (dành cho admin)** — chỉ dành cho quản trị viên server.",
        "🛡️ **Admin Panel** — for server administrators only."
    ),
}


def t(guild_id, user_id, key: str, **fmt) -> str:
    locale = get_locale(guild_id, user_id) if guild_id else "vi"
    vi, en = TR.get(key, (key, key))
    s = en if locale == "en" else vi
    if fmt:
        try:
            s = s.format(**fmt)
        except Exception:
            pass
    return s


# ============== MONSTERS ==============
@dataclass
class Monster:
    name: str
    emoji: str
    level: int
    tank: int
    dps: int
    hp: int

    @property
    def display(self) -> str:
        return f"{self.emoji} {self.name}"


def _dict_to_monster(d: dict) -> Monster:
    return Monster(
        name=str(d.get("name", "?")),
        emoji=str(d.get("emoji", "❓")),
        level=int(d.get("level", 1)),
        tank=int(d.get("tank", 0)),
        dps=int(d.get("dps", 0)),
        hp=int(d.get("hp", 1)),
    )


def monsters_by_level(level: int) -> list[Monster]:
    from .storage import get_monsters_by_level
    return [_dict_to_monster(d) for d in get_monsters_by_level(level)]


# ============== RANKS ==============
RANKS = ["I", "II", "III", "IV", "V"]
RANK_INFO = {
    "I": {
        "name": "🕯 Kẻ Tập Sự",
        "name_en": "🕯 The Apprentice",
        "speech": "🕯 Ngươi đã đặt chân lên một con đường đẫm máu. Nguyện cầu cho linh hồn của những kẻ bại trận dưới tay ngươi sẽ được siêu thoát.",
        "speech_en": "🕯 You have set foot on a path drenched in blood. May the souls of those who fall before you find peace.",
    },
    "II": {
        "name": "⚔️ Chiến Binh Tập Luyện",
        "name_en": "⚔️ The Seasoned Warrior",
        "speech": "⚔️ Máu làm ngươi say, và âm thanh hò reo vang lên từ khán đài làm ngươi mê muội.",
        "speech_en": "⚔️ Blood intoxicates you, and the roar of the crowd from the stands blinds your senses.",
    },
    "III": {
        "name": "🩸 Kẻ Săn Linh Hồn",
        "name_en": "🩸 The Soul Hunter",
        "speech": "🩸 Ngươi đã trở thành một đối thủ đáng gờm. Tất cả mọi sinh vật trong đấu trường bắt đầu nhìn ngươi bằng ánh mắt e sợ.",
        "speech_en": "🩸 You have become a formidable adversary. Every creature in this arena now watches you with fearful eyes.",
    },
    "IV": {
        "name": "👁 Kỵ Sĩ Hắc Ấn",
        "name_en": "👁 The Dark Seal Knight",
        "speech": "👁 Hãy dẫm lên xác của kẻ thua cuộc và tiến về phía trước. Vong hồn của bọn ta dõi theo người.",
        "speech_en": "👁 Tread upon the fallen and march forward. The spirits of our kin watch over you.",
    },
    "V": {
        "name": "👑 Chúa Tể Hắc Ám",
        "name_en": "👑 The Dark Lord",
        "speech": "🏆✨ Tại đấu trường này, giờ đây ngươi là Kẻ thống trị. ✨🏆",
        "speech_en": "🏆✨ In this arena, you are now the Sovereign. ✨🏆",
    },
}


def rank_name(rank: str, locale: str = "vi") -> str:
    info = RANK_INFO.get(rank, {})
    return info.get("name_en" if locale == "en" else "name", rank)


def rank_speech(rank: str, locale: str = "vi") -> str:
    info = RANK_INFO.get(rank, {})
    return info.get("speech_en" if locale == "en" else "speech", "")


TRAINING_BONUS_PCT = {"I": 0, "II": 10, "III": 20, "IV": 35, "V": 60}


def training_bonus_pct(rank: str) -> int:
    return TRAINING_BONUS_PCT.get(rank, 0)


def apply_training_bonus(gain: int, rank: str) -> int:
    """Nhân điểm luyện tập với hệ số thưởng theo rank. gain=0 thì giữ nguyên."""
    if gain <= 0:
        return gain
    pct = training_bonus_pct(rank)
    return int(round(gain * (1 + pct / 100)))


def compute_rank(player) -> str:
    wins = player.get("wins", 0)
    wbl = player.get("wins_by_level", {})

    def w(lv: int) -> int:
        return int(wbl.get(str(lv), 0))

    if w(5) >= 1:
        return "V"
    if w(3) >= 50:
        return "IV"
    if w(2) >= 30:
        return "III"
    if w(1) >= 20:
        return "II"
    return "I"


def rank_progress_text(player, guild_id=None, user_id=None) -> str:
    wbl = player.get("wins_by_level", {})
    label = t(guild_id, user_id, "stats_wins") if guild_id else "Số trận thắng"
    return (
        f"{label}: **{player.get('wins', 0)}**\n"
        f"🪨 Cấp I: {wbl.get('1', 0)} | 🌲 Cấp II: {wbl.get('2', 0)} | "
        f"🔥 Cấp III: {wbl.get('3', 0)} | 🌑 Cấp IV: {wbl.get('4', 0)} | 👑 Cấp V: {wbl.get('5', 0)}"
    )


def can_fight_monster(player, monster: "Monster", has_rank_role: bool = False) -> bool:
    rank = player.get("rank", "I")
    rank_lv = RANKS.index(rank) + 1
    if monster.level <= rank_lv:
        return True
    if rank_lv == 4 and monster.level == 5:
        return True
    return False


# ============== BATTLE FORMULAS ==============
def attack_chance(dps_p: int, dps_e: int) -> float:
    c = 0.5 + (dps_p - dps_e) * 0.02
    return max(0.2, min(0.8, c))


def block_chance(tank_p: int, dps_e: int) -> float:
    c = 0.3 + (tank_p - dps_e) * 0.02
    return max(0.1, min(0.7, c))


def player_max_hp(player) -> int:
    return 50 + int(player.get("health", 5)) * 12


def heal_amount(player) -> int:
    h = player.get("health", 5)
    return max(2, int(h * random.uniform(1.0, 2.0)))


def damage_value(dps: int) -> int:
    """Legacy flat damage (kept for backward compatibility / fallbacks)."""
    return max(1, int(dps * random.uniform(0.8, 1.2)))


def damage_pct(atk_dps: int, def_tank: int, def_max_hp: int) -> int:
    """Percentage-based damage so a 10-round duel can drain ~80-110% of a player's HP.

    Each landing strike deals ~6-11% of the defender's max HP, modulated by the
    attacker DPS / defender Tank ratio (clamped). With ~50-70% landing rate per
    round across both fighters, displayed HP (normalised to 100) typically falls
    from 100 to roughly 20…-10 by round 10.
    """
    if def_max_hp <= 0:
        return damage_value(atk_dps)
    ratio = max(1, atk_dps) / max(1, def_tank)
    factor = max(0.55, min(1.8, ratio ** 0.5))
    pct = 0.085 * factor * random.uniform(0.85, 1.20)
    return max(1, int(round(def_max_hp * pct)))


def compute_power(tank: int, dps: int, max_hp: int) -> float:
    """Rough total power score, used for scaling HP-bar visual length."""
    return float(tank) + float(dps) + float(max_hp) / 5.0


def hp_bar_widths(power_a: float, power_b: float,
                  base_max: int = 18, base_min: int = 6) -> tuple[int, int]:
    """Stronger side gets a longer bar; weaker side shrinks proportionally.

    Returns (width_for_a, width_for_b)."""
    pa = max(1.0, power_a)
    pb = max(1.0, power_b)
    if pa >= pb:
        ratio = pb / pa
        wa = base_max
        wb = max(base_min, int(round(base_max * ratio)))
    else:
        ratio = pa / pb
        wb = base_max
        wa = max(base_min, int(round(base_max * ratio)))
    return wa, wb


def hp_pct_display(cur: int, mx: int) -> int:
    """Always show a 0-100 normalised HP value (can dip below 0 to expose how
    badly a fighter was beaten — clamped at -20 for sanity)."""
    if mx <= 0:
        return 0
    pct = int(round(100 * cur / mx))
    if pct < -20:
        pct = -20
    if pct > 100:
        pct = 100
    return pct


def crit_check() -> bool:
    return random.random() < 0.2


def miss_check() -> bool:
    return random.random() < 0.15


# ============== LORE ==============
DEFAULT_LORE = {
    "intro": "Hỡi chiến binh dũng cảm, ta có thể giúp gì cho ngươi?",
    "outro": "🌕 Hẹn gặp lại ngươi trên chiến trường.",
    "arena": (
        "💀 Ngươi có từng nghe về việc vùng đất này từng thuộc về thế lực Thiên Đường "
        "trước khi bị ác quỷ chiếm đóng? Những cột đá trắng muốt và nền gạch sạch bong "
        "trông rất đẹp đẽ, nhưng ta thích phiên bản của đấu trường ở thời điểm hiện tại hơn — "
        "khi nó ngày ngày bị bao phủ bởi mùi máu và tiếng thét gào."
    ),
    "self": (
        "🌑 Trước khi sa ngã thành ma quỷ, ta từng là một tướng lĩnh của các thiên thần. "
        "Cánh của ta đã bị bẻ gãy bởi chính những người mà ta từng tin tưởng, "
        "nhưng tinh thần hiệp sĩ của ta thì tuyệt đối sẽ không lung lay. "
        "Ta không quỳ gối trước bất kì thần linh hay vua chúa. "
        "Tín ngưỡng duy nhất của ta chính là thanh gươm đẫm máu mà ta nắm trong tay."
    ),
}

DEFAULT_LORE_EN = {
    "intro": "Brave warrior, how may I aid you?",
    "outro": "🌕 Farewell — until we meet again on the battlefield.",
    "arena": (
        "💀 Have you ever heard that this land once belonged to the forces of Heaven "
        "before the demons seized it? The white stone pillars and spotless brick floors "
        "were beautiful once — but I prefer the arena as it stands today, "
        "drenched each day in the scent of blood and the sound of screaming."
    ),
    "self": (
        "🌑 Before my fall into darkness, I was once a general among the angels. "
        "My wings were broken by the very ones I trusted, "
        "yet the spirit of a knight within me shall never waver. "
        "I kneel before no god, no king. "
        "The only faith I hold is this blood-soaked sword in my hand."
    ),
}


def get_lore_text(guild_id, topic: str, locale: str | None = None) -> str:
    """Random pool: luôn có câu mặc định + tất cả câu admin nhập.
    Câu admin luôn giữ nguyên ngôn ngữ admin nhập; chỉ câu mặc định được dịch."""
    g = get_guild(guild_id)
    msgs = list(g["lore"].get(topic, {}).get("messages", []))
    if locale is None:
        locale = "vi"
    default = DEFAULT_LORE_EN.get(topic, DEFAULT_LORE[topic]) if locale == "en" else DEFAULT_LORE[topic]
    pool = [default] + msgs
    return random.choice(pool)


ARENA_GUIDE = (
    "📜 **Hướng dẫn sử dụng đấu trường**\n\n"
    "🛠 **Luyện tập** — 3 bài tập giúp ngươi tăng chỉ số:\n"
    "• 🛡 **Tank** — né đòn theo màu (5 lượt).\n"
    "• 🗡 **DPS** — bấm chuỗi nút theo đúng thứ tự (5 lượt).\n"
    "• 💊 **Pha chế thần dược** — chọn 3 nguyên liệu trong Lò giả kim.\n\n"
    "⚔️ **Thách đấu** — chọn 1 trong 2:\n"
    "• 🐉 **PvE** — đấu quái vật (5 cấp). Mỗi quái hạ gục cho điểm chiến công.\n"
    "• ⚔️ **PvP** — gửi thư mời 1vs1 đến người chơi khác.\n"
    "• Cơ chế: Tấn công / Phòng thủ với HP, đòn chí mạng, chặn, đánh trượt.\n\n"
    "📊 **Xem thông tin cá nhân** — kiểm tra chỉ số 🛡 🗡 💊, hạng, số trận thắng.\n"
    "🏆 **Bảng xếp hạng** — top 10 chiến binh trong server.\n\n"
    "👑 **Hệ thống hạng** — I → II → III → IV → V (Kẻ Tập Sự → Chúa Tể Hắc Ám).\n"
    "Khi đạt hạng mới, ta sẽ chúc mừng ngươi trước toàn thể chiến binh."
)
ARENA_GUIDE_EN = (
    "📜 **Arena Guide**\n\n"
    "🛠 **Train** — 3 mini-games to raise your stats:\n"
    "• 🛡 **Tank** — dodge by matching colors (5 rounds).\n"
    "• 🗡 **DPS** — press the buttons in the correct order (5 rounds).\n"
    "• 💊 **Brew potions** — pick 3 ingredients in the alchemy chamber.\n\n"
    "⚔️ **Challenge** — pick one:\n"
    "• 🐉 **PvE** — fight monsters (5 tiers). Each kill grants merit points.\n"
    "• ⚔️ **PvP** — send a 1v1 invitation to another player.\n"
    "• System: Attack / Defend with HP, crits, blocks, and misses.\n\n"
    "📊 **My stats** — check 🛡 🗡 💊, rank, and total wins.\n"
    "🏆 **Leaderboard** — top 10 warriors of the server.\n\n"
    "👑 **Rank system** — I → II → III → IV → V (Apprentice → Dark Lord).\n"
    "When you reach a new rank, I will honor you before all warriors."
)


def arena_guide(guild_id, user_id) -> str:
    return ARENA_GUIDE_EN if get_locale(guild_id, user_id) == "en" else ARENA_GUIDE


# ============== ACHIEVEMENTS ==============
ACHIEVEMENTS = {
    "pve_10":       {"icon": "🗡",  "name": "Diệt Quái x10",      "name_en": "Monster Slayer x10",   "desc": "Hạ gục 10 quái vật.",          "desc_en": "Defeat 10 monsters."},
    "pve_100":      {"icon": "⚔️", "name": "Diệt Quái x100",     "name_en": "Monster Slayer x100",  "desc": "Hạ gục 100 quái vật.",         "desc_en": "Defeat 100 monsters."},
    "pve_200":      {"icon": "🩸", "name": "Diệt Quái x200",     "name_en": "Monster Slayer x200",  "desc": "Hạ gục 200 quái vật.",         "desc_en": "Defeat 200 monsters."},
    "pve_300":      {"icon": "💀", "name": "Diệt Quái x300",     "name_en": "Monster Slayer x300",  "desc": "Hạ gục 300 quái vật.",         "desc_en": "Defeat 300 monsters."},
    "pve_400":      {"icon": "🔥", "name": "Diệt Quái x400",     "name_en": "Monster Slayer x400",  "desc": "Hạ gục 400 quái vật.",         "desc_en": "Defeat 400 monsters."},
    "pve_500":      {"icon": "👹", "name": "Diệt Quái x500",     "name_en": "Monster Slayer x500",  "desc": "Hạ gục 500 quái vật.",         "desc_en": "Defeat 500 monsters."},
    "boss_slayer":  {"icon": "🐉", "name": "Đồ Tể Của Boss",     "name_en": "Boss Butcher",         "desc": "Hạ gục được boss cấp V (Rồng Hắc Ám).", "desc_en": "Defeat the Tier V boss (Dark Dragon)."},
    "pvp_unbeaten": {"icon": "🏅", "name": "Bất Bại",            "name_en": "Unbeaten",             "desc": "Thắng 10 trận PvP liên tiếp.", "desc_en": "Win 10 PvP battles in a row."},
    "rank_II":      {"icon": "⚔️", "name": "Đăng cơ Hạng II",   "name_en": "Ascend to Rank II",    "desc": "Trở thành ⚔️ Chiến Binh Tập Luyện và nhận role thưởng.", "desc_en": "Become ⚔️ The Seasoned Warrior and receive your rank role."},
    "rank_III":     {"icon": "🩸", "name": "Đăng cơ Hạng III",  "name_en": "Ascend to Rank III",   "desc": "Trở thành 🩸 Kẻ Săn Linh Hồn và nhận role thưởng.",     "desc_en": "Become 🩸 The Soul Hunter and receive your rank role."},
    "rank_IV":      {"icon": "👁",  "name": "Đăng cơ Hạng IV",   "name_en": "Ascend to Rank IV",    "desc": "Trở thành 👁 Kỵ Sĩ Hắc Ấn và nhận role thưởng.",        "desc_en": "Become 👁 The Dark Seal Knight and receive your rank role."},
    "rank_V":       {"icon": "👑", "name": "Đăng cơ Hạng V",    "name_en": "Ascend to Rank V",     "desc": "Đăng cơ 👑 Chúa Tể Hắc Ám và nhận role thưởng.",         "desc_en": "Ascend to 👑 The Dark Lord and receive your rank role."},
}
ACHIEVEMENT_ORDER = list(ACHIEVEMENTS.keys())


def _qualifies(aid: str, p) -> bool:
    wins = int(p.get("wins", 0))
    rank = p.get("rank", "I")
    streak = int(p.get("pvp_streak", 0))
    boss_kills = int(p.get("wins_by_level", {}).get("5", 0))
    if aid == "pve_10":  return wins >= 10
    if aid == "pve_100": return wins >= 100
    if aid == "pve_200": return wins >= 200
    if aid == "pve_300": return wins >= 300
    if aid == "pve_400": return wins >= 400
    if aid == "pve_500": return wins >= 500
    if aid == "boss_slayer":  return boss_kills >= 1
    if aid == "pvp_unbeaten": return streak >= 10
    if aid.startswith("rank_"):
        target = aid.split("_", 1)[1]
        if target not in RANKS or rank not in RANKS:
            return False
        return RANKS.index(rank) >= RANKS.index(target)
    return False


def unlock_achievements(player) -> list[str]:
    """Quét lại điều kiện, thêm các thành tựu mới vào player['achievements']
    và trả về danh sách ID vừa mở khoá (để công bố)."""
    have = set(player.get("achievements", []))
    newly = []
    for aid in ACHIEVEMENT_ORDER:
        if aid not in have and _qualifies(aid, player):
            newly.append(aid)
    if newly:
        player.setdefault("achievements", [])
        player["achievements"].extend(newly)
    return newly


def format_achievements(player, locale: str = "vi") -> str:
    have = set(player.get("achievements", []))
    if not have:
        if locale == "en":
            return "🏅 **Achievements:** _(none yet — get out there and fight!)_"
        return "🏅 **Thành tựu:** _(chưa có thành tựu nào — hãy ra trận!)_"
    if locale == "en":
        lines = ["🏅 **Achievements Unlocked:**"]
    else:
        lines = ["🏅 **Thành tựu đã đạt:**"]
    for aid in ACHIEVEMENT_ORDER:
        if aid in have:
            a = ACHIEVEMENTS[aid]
            if locale == "en":
                lines.append(f"{a['icon']} **{a['name_en']}** — {a['desc_en']}")
            else:
                lines.append(f"{a['icon']} **{a['name']}** — {a['desc']}")
    return "\n".join(lines)


def announce_unlocks(new_ids: list[str], locale: str = "vi") -> str:
    if not new_ids:
        return ""
    if locale == "en":
        lines = ["", "🎖 **New Achievement Unlocked!**"]
        for aid in new_ids:
            a = ACHIEVEMENTS[aid]
            lines.append(f"• {a['icon']} **{a['name_en']}** — {a['desc_en']}")
    else:
        lines = ["", "🎖 **Thành tựu mới mở khoá!**"]
        for aid in new_ids:
            a = ACHIEVEMENTS[aid]
            lines.append(f"• {a['icon']} **{a['name']}** — {a['desc']}")
    return "\n".join(lines)


async def announce_achievements_public(channel: discord.abc.Messageable,
                                       member: discord.abc.User,
                                       new_ids: list[str],
                                       locale: str = "vi"):
    """Post a public celebration message when a player unlocks new achievements."""
    if not new_ids or channel is None:
        return
    if locale == "en":
        lines = [f"🎖 **{member.display_name} has unlocked a new achievement!**"]
        for aid in new_ids:
            a = ACHIEVEMENTS[aid]
            lines.append(f"• {a['icon']} **{a['name_en']}** — {a['desc_en']}")
        title = "🎖 Achievement Unlocked"
    else:
        lines = [f"🎖 **{member.display_name} đã mở khoá thành tựu mới!**"]
        for aid in new_ids:
            a = ACHIEVEMENTS[aid]
            lines.append(f"• {a['icon']} **{a['name']}** — {a['desc']}")
        title = "🎖 Mở khoá thành tựu"
    embed = discord.Embed(
        title=title,
        description="\n".join(lines),
        color=GOLD_COLOR,
    )
    try:
        await channel.send(
            content=member.mention,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


# ============== NAVIGATION ==============
async def go_lobby(interaction: discord.Interaction, user: discord.User):
    from .menu import MainView
    locale = get_locale(interaction.guild_id, user.id) if interaction.guild_id else "vi"
    await interaction.response.edit_message(
        embed=knight_embed(get_lore_text(interaction.guild_id, "intro", locale=locale)),
        view=MainView(user, interaction.guild),
    )


async def exit_bot(interaction: discord.Interaction):
    from .storage import get_locale as _get_locale
    locale = _get_locale(interaction.guild_id, interaction.user.id) if interaction.guild_id else "vi"
    lore = get_lore_text(interaction.guild_id, "outro", locale=locale)
    await interaction.response.edit_message(
        embed=knight_embed(lore),
        view=None,
    )


# ============== RANK UP ANNOUNCE ==============
async def announce_rank_up(channel: discord.abc.Messageable, member: discord.abc.User, new_rank: str, guild_id):
    """Khi user đạt 1 rank mới: chúc mừng. Rank V (cao nhất): tag @everyone."""
    locale = get_locale(guild_id, member.id)
    rinfo = RANK_INFO[new_rank]
    rname = rinfo["name_en"] if locale == "en" else rinfo["name"]
    rspeech = rinfo["speech_en"] if locale == "en" else rinfo["speech"]
    is_top = new_rank == "V"
    bonus = training_bonus_pct(new_rank)
    if is_top:
        text = t(guild_id, member.id, "rankup_top_text",
                 mention=member.mention, rank_name=rname, speech=rspeech, bonus=bonus)
        embed = discord.Embed(
            title="✨👑🏆 ĐĂNG CƠ — CHÚA TỂ ĐẤU TRƯỜNG 🏆👑✨" if locale != "en" else "✨👑🏆 ASCENSION — LORD OF THE ARENA 🏆👑✨",
            description=text,
            color=GOLD_COLOR,
        )
        embed.set_footer(text="🌑 Một huyền thoại đã được khắc tên vào sổ đẫm máu." if locale != "en"
                         else "🌑 A legend has been etched into the blood-soaked ledger.")
    else:
        text = t(guild_id, member.id, "rankup_text",
                 mention=member.mention, rank_name=rname, speech=rspeech, bonus=bonus)
        embed = discord.Embed(
            title=f"🎉🏆 {t(guild_id, member.id, 'rankup_title')} 🏆🎉",
            description=text,
            color=GOLD_COLOR,
        )
    try:
        await channel.send(
            content=("@everyone" if is_top else None),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=is_top, users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


async def maybe_grant_rank_role(interaction, user, new_rank):
    """Cấp role thưởng nếu admin đã thiết lập."""
    try:
        g = get_guild(interaction.guild_id)
        role_id = g["config"]["rank_roles"].get(new_rank)
        if not role_id:
            return False
        guild = interaction.guild
        member = guild.get_member(user.id) or await guild.fetch_member(user.id)
        role = guild.get_role(int(role_id))
        if member and role:
            await member.add_roles(role, reason=f"Lên hạng {new_rank}")
            return True
    except Exception:
        pass
    return False


def has_rank_role(member: discord.Member | None, guild_id, rank: str) -> bool:
    if not member:
        return False
    g = get_guild(guild_id)
    role_id = g["config"]["rank_roles"].get(rank)
    if not role_id:
        return False
    return any(str(r.id) == str(role_id) for r in member.roles)
