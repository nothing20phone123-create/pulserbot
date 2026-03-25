from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

def db():
    return sqlite3.connect("users.db")

TRC = "TSd1kwMavFDHJNXXqioSXWjywrEJW5Dt3U"
ERC = "0x3ae6c6ca3a0cdd54d93f605284a423b572caca72"

ADMIN_ID = "8671125457"
BOT_USERNAME = "pulseofficialsbot"

# ====================== TELEGRAM MINI APP UI ======================
def ui():
    return """
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- ✅ AUTO LOGIN ADDED -->
    <script>
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.ready();

    const user = tg.initDataUnsafe?.user;

    // Telegram user auto redirect
    if (user && !window.location.search.includes("id=")) {
        window.location.href = `/?id=${user.id}&username=${user.username || "unknown"}`;
    }
    </script>

    <style>
    body {background: linear-gradient(135deg, #0a0c10, #1a1f2e); color: #e0f0ff; font-family: 'Inter', system-ui;}
    .card {background: rgba(19, 23, 31, 0.95); border: 1px solid #334155; padding: 20px; border-radius: 20px; margin-bottom: 16px; box-shadow: 0 10px 30px -10px rgba(234, 179, 8, 0.4);}
    .btn {padding: 16px; border-radius: 16px; text-align: center; display: block; font-weight: 700; transition: all 0.3s ease;}
    .neon {box-shadow: 0 0 20px #facc15;}
    .glow {animation: glow 2s ease-in-out infinite alternate;}
    .marquee {overflow: hidden; white-space: nowrap;}
    .marquee-content {display: inline-block; animation: marquee 35s linear infinite;}
    @keyframes glow { from {text-shadow: 0 0 10px #facc15;} to {text-shadow: 0 0 25px #facc15;} }
    @keyframes marquee { from {transform: translateX(100%);} to {transform: translateX(-100%);} }
    .welcome {animation: welcomeAnim 3s ease-in-out infinite;}
    @keyframes welcomeAnim { 0%, 100% {transform: scale(1);} 50% {transform: scale(1.05);} }
    </style>
    """

# ====================== DATABASE SETUP ======================
def init_db():
    conn = db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, type TEXT, balance REAL DEFAULT 0,
                    profit REAL DEFAULT 0, total_profit REAL DEFAULT 0, vip_level INTEGER DEFAULT 0,
                    reward_balance REAL DEFAULT 0, reward_timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, amount REAL, network TEXT, txid TEXT, status TEXT DEFAULT 'pending', reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdraws (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, amount REAL, address TEXT, network TEXT, status TEXT DEFAULT 'pending', reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, type TEXT, msg TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ====================== VIP LEVEL + BONUS ======================
def get_vip_level(balance):
    if balance >= 50000: return 7
    if balance >= 20000: return 6
    if balance >= 10000: return 5
    if balance >= 5000: return 4
    if balance >= 2000: return 3
    if balance >= 1000: return 2
    if balance >= 500: return 1
    return 0

def get_vip_bonus(level):
    bonuses = {1: 50, 2: 100, 3: 200, 4: 500, 5: 1000, 6: 2000, 7: 5000}
    return bonuses.get(level, 0)

# ====================== USER HOME (Telegram Verification) ======================
@app.route("/")
def home():
    uid = request.args.get("id")
    username = request.args.get("username") or "unknown"

    if not uid:
        return f"""{ui()}
        <div class="max-w-md mx-auto p-5 min-h-screen flex items-center justify-center text-center">
            <div class="card">
                <h2 class="text-red-400 text-2xl mb-4">⚠️ Access Denied</h2>
                <p class="text-xl mb-6">Please start the bot first to use this Mini App.</p>
                <a href="https://t.me/{BOT_USERNAME}" target="_blank" class="btn bg-green-500 text-white text-lg">🚀 Start Bot Now</a>
            </div>
        </div>"""

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", (uid, "user", 0, 0, 0, 0, 0, None))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
        user = c.fetchone()

    # Auto VIP + Reward
    current_vip = get_vip_level(user[2])
    if current_vip > user[5]:
        bonus = get_vip_bonus(current_vip)
        now = datetime.now().isoformat()
        c.execute("UPDATE users SET vip_level=?, reward_balance=reward_balance+?, reward_timestamp=? WHERE id=?", (current_vip, bonus, now, uid))
        c.execute("INSERT INTO messages VALUES(NULL,?,?)", (uid, f"Congratulations! You are now VIP {current_vip} - {bonus} USDT reward added!"))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
        user = c.fetchone()

    # 24 hours reward transfer
    if user[7] and user[6] > 0:
        reward_time = datetime.fromisoformat(user[7])
        if datetime.now() - reward_time >= timedelta(hours=24):
            c.execute("UPDATE users SET balance=balance+?, reward_balance=0, reward_timestamp=NULL WHERE id=?", (user[6], uid))
            c.execute("INSERT INTO messages VALUES(NULL,?,?)", (uid, f"{user[6]} USDT Reward Balance has been added to your Main Balance after 24 hours!"))
            conn.commit()
            c.execute("SELECT * FROM users WHERE id=?", (uid,))
            user = c.fetchone()

    c.execute("SELECT message FROM messages WHERE user_id=?", (uid,))
    msgs = c.fetchall()
    conn.close()

    badge = f'<span class="ml-auto bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full">{len(msgs)}</span>' if msgs else ''
    vip_text = f"You are now VIP {user[5]} tier - Welcome to VIP{user[5]}" if user[5] > 0 else "Regular Member"

    messages_html = "".join([f'<div class="bg-[#252a31] p-4 rounded-2xl"><strong>From Admin/Support:</strong><br>{m[0]}</div>' for m in msgs])

    html = f"""{ui()}
    <div class="max-w-md mx-auto p-5 min-h-screen">
    <div class="text-center mb-4 welcome">
        <h1 class="text-amber-300 text-2xl font-bold glow">Make Your Day Happy with PulseForge!</h1>
    </div>

    <div class="flex justify-center items-center gap-2 mb-8">
        <span class="text-4xl">🚀</span>
        <h2 class="text-amber-400 text-3xl font-bold tracking-widest glow">PulseForge</h2>
    </div>

    <div class="flex justify-end mb-3">
        <span class="bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-sm font-bold px-5 py-1 rounded-full">{vip_text}</span>
    </div>

    <div class="card neon text-center">
        <h1 class="text-5xl font-bold text-amber-300">{user[2]} USD</h1>
    </div>

    <div class="card">
        📈 Daily Profit: <span class="text-emerald-400 font-semibold">{user[3]}</span><br>
        💰 Total Profit: <span class="text-emerald-400 font-semibold">{user[4]}</span><br>
        🌟 Reward Balance: <span class="text-purple-400 font-semibold">{user[6]} USD</span>
    </div>

    <a href='/deposit?id={uid}' class='btn bg-gradient-to-r from-amber-400 to-yellow-500 text-black neon text-lg'>Deposit</a>
    <a href='/withdraw?id={uid}' class='btn bg-gradient-to-r from-red-500 to-rose-600 text-white text-lg'>Withdraw</a>
    <a href='/support?id={uid}&username={username}' class='btn bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-lg'>Support</a>

    <div onclick="openMessagesModal()" class="card mt-6 flex items-center justify-between cursor-pointer hover:bg-[#1f2937]">
        <h3 class="text-amber-400 text-xl flex items-center gap-2">📩 Messages</h3>
        {badge}
    </div>

    <div onclick="openVipModal()" class="card mt-6 flex items-center justify-between cursor-pointer hover:bg-[#1f2937]">
        <h3 class="text-amber-400 text-xl flex items-center gap-2">🌟 VIP System</h3>
        <span class="text-yellow-400">→</span>
    </div>

    <div class="card mt-6 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-center py-3 overflow-hidden">
        <div class="marquee">
            <div class="marquee-content text-sm font-semibold">
                🎁 VIP Rewards Program &nbsp;&nbsp;&nbsp; 
                VIP1 → 500 USDT (50 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP2 → 1000 USDT (100 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP3 → 2000 USDT (200 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP4 → 5000 USDT (500 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP5 → 10000 USDT (1000 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP6 → 20000 USDT (2000 USDT add) &nbsp;&nbsp;&nbsp; 
                VIP7 → 50000 USDT (5000 USDT add) &nbsp;&nbsp;&nbsp; 
                Upgrade your VIP level to earn more rewards!
            </div>
        </div>
    </div>
    </div>

    <!-- Messages Modal -->
    <div id="messagesModal" onclick="if(event.target===this)closeMessagesModal()" class="hidden fixed inset-0 bg-black/90 flex items-end z-[9999]">
      <div onclick="event.stopImmediatePropagation()" class="bg-[#13171f] w-full max-w-md mx-auto rounded-3xl max-h-[88vh] overflow-hidden flex flex-col shadow-2xl mb-3">
        <div class="w-14 h-1.5 bg-gray-400 rounded-full mx-auto mt-4 mb-1"></div>
        <div class="px-6 pb-4 text-center text-xl font-semibold">Messages</div>
        <div class="flex-1 overflow-y-auto px-5 pb-5 space-y-4">
            {messages_html or '<div class="text-center text-gray-400 py-10">No messages yet</div>'}
        </div>
      </div>
    </div>

    <!-- VIP Modal -->
    <div id="vipModal" onclick="if(event.target===this)closeVipModal()" class="hidden fixed inset-0 bg-black/90 flex items-end z-[9999]">
      <div onclick="event.stopImmediatePropagation()" class="bg-[#13171f] w-full max-w-md mx-auto rounded-3xl max-h-[88vh] overflow-hidden flex flex-col shadow-2xl mb-3">
        <div class="w-14 h-1.5 bg-gray-400 rounded-full mx-auto mt-4 mb-1"></div>
        <div class="px-6 pb-4 text-center text-xl font-semibold">🎁 VIP Rewards Program</div>
        <div class="flex-1 overflow-y-auto px-6 pb-6 space-y-6 text-white text-sm">
          <div class="text-center text-amber-300 text-lg font-bold">Upgrade your VIP level to earn more rewards!</div>
          <div>🌟 <strong>VIP1</strong> - 500 USDT reward (50 USDT add)</div>
          <div>🌟 <strong>VIP2</strong> - 1000 USDT reward (100 USDT add)</div>
          <div>🌟 <strong>VIP3</strong> - 2000 USDT reward (200 USDT add)</div>
          <div>🌟 <strong>VIP4</strong> - 5000 USDT reward (500 USDT add)</div>
          <div>🌟 <strong>VIP5</strong> - 10000 USDT reward (1000 USDT add)</div>
          <div>🌟 <strong>VIP6</strong> - 20000 USDT reward (2000 USDT add)</div>
          <div>🌟 <strong>VIP7</strong> - 50000 USDT reward (5000 USDT add)</div>
        </div>
      </div>
    </div>

    <script>
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.ready();
    function openMessagesModal() {{ document.getElementById('messagesModal').classList.remove('hidden'); document.getElementById('messagesModal').classList.add('flex'); }}
    function closeMessagesModal() {{ document.getElementById('messagesModal').classList.add('hidden'); document.getElementById('messagesModal').classList.remove('flex'); }}
    function openVipModal() {{ document.getElementById('vipModal').classList.remove('hidden'); document.getElementById('vipModal').classList.add('flex'); }}
    function closeVipModal() {{ document.getElementById('vipModal').classList.add('hidden'); document.getElementById('vipModal').classList.remove('flex'); }}
    </script>
    """
    return html

# ====================== SUPPORT (username সেভ হয়) ======================
@app.route("/support")
def support():
    uid = request.args.get("id")
    username = request.args.get("username") or "unknown"
    return f"""{ui()}
    <div class="max-w-md mx-auto p-4">
    <div class="card">
    <form action='/send_support'>
    <input type='hidden' name='uid' value='{uid}'>
    <input type='hidden' name='username' value='{username}'>
    <input name='msg' placeholder='Type your message...' class='text-black w-full p-3 rounded mb-3'>
    <button class='btn bg-blue-500'>Send</button>
    </form>
    </div>
    </div>
    """

@app.route("/send_support")
def send_support():
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO support VALUES(NULL,?,?,?,?)", (request.args.get("uid"), request.args.get("username"), "user", request.args.get("msg")))
    conn.commit()
    conn.close()
    return "Support Sent"

# ====================== ADMIN PANEL (শুধু অ্যাডমিনের জন্য) ======================
@app.route("/admin")
def admin():
    uid = request.args.get("id")
    if uid != ADMIN_ID:
        return f"""{ui()}
        <div class="max-w-md mx-auto p-5 min-h-screen flex items-center justify-center text-center">
            <div class="card">
                <h2 class="text-red-400 text-3xl mb-4">🚫 Access Denied</h2>
                <p class="text-xl">Only Admin can access this panel.</p>
            </div>
        </div>"""

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    c.execute("SELECT * FROM support")
    sup = c.fetchall()
    conn.close()

    badge = f'<span class="ml-auto bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full">{len(sup)}</span>' if sup else ''

    support_html = ""
    for s in sup:
        support_html += f"""
        <div class="card p-5">
            <p><strong>From:</strong> @{s[2]} (ID: {s[1]})</p>
            <p class="mt-2">{s[4]}</p>
            <form action='/reply_support' class="mt-4">
                <input type='hidden' name='uid' value='{s[1]}'>
                <input name='reply' placeholder="Reply to user..." class='text-black w-full p-3 rounded mb-3'>
                <button class='btn bg-blue-500 w-full'>Send Reply</button>
            </form>
        </div>
        """

    html = f"""{ui()}
    <div class="max-w-md mx-auto p-4">
    <h2 class="text-amber-400 text-center text-3xl mb-6 glow">🔐 Admin Panel</h2>

    <a href='/deposits' class='btn bg-gradient-to-r from-amber-400 to-yellow-500 text-black neon text-lg'>Pending Deposits</a>
    <a href='/withdraws' class='btn bg-gradient-to-r from-red-500 to-rose-600 text-white text-lg'>Pending Withdraws</a>

    <div class="card mt-6">
        <h3 class="text-amber-400 mb-3">Broadcast to All Users</h3>
        <form action='/broadcast'>
            <textarea name='m' placeholder="Type message here..." rows="4" class='text-black w-full p-3 rounded mb-3'></textarea>
            <button class='btn bg-blue-500 w-full'>Send Broadcast</button>
        </form>
    </div>

    <div class="card mt-4">
        <h3 class="text-amber-400 mb-3">All Users</h3>
        <div class="space-y-3">
    """

    for u in users:
        html += f"""
        <div class="bg-[#252a31] p-4 rounded-2xl flex justify-between items-center">
            <div>
                <span class="font-medium text-white">{u[0]}</span><br>
                <span class="text-emerald-400 text-sm">{u[2]} USD</span>
            </div>
            <a href='/manage?uid={u[0]}' class="text-amber-400 font-medium">Manage</a>
        </div>
        """

    html += f"""
        </div>
    </div>

    <div onclick="openSupportModal()" class="card mt-4 flex items-center justify-between cursor-pointer hover:bg-[#1f2937]">
        <h3 class="text-amber-400 text-lg flex items-center gap-2">📩 Support Inbox</h3>
        {badge}
    </div>
    </div>

    <!-- Support Modal -->
    <div id="supportModal" onclick="if(event.target===this)closeSupportModal()" class="hidden fixed inset-0 bg-black/90 flex items-end z-[9999]">
      <div onclick="event.stopImmediatePropagation()" class="bg-[#13171f] w-full max-w-md mx-auto rounded-3xl max-h-[88vh] overflow-hidden flex flex-col shadow-2xl mb-3">
        <div class="w-14 h-1.5 bg-gray-400 rounded-full mx-auto mt-4 mb-1"></div>
        <div class="px-6 pb-4 text-center text-xl font-semibold">Support Inbox</div>
        <div class="flex-1 overflow-y-auto px-5 pb-5 space-y-4">
            {support_html or '<div class="text-center text-gray-400 py-10">No support messages yet</div>'}
        </div>
      </div>
    </div>

    <script>
    function openSupportModal() {{ document.getElementById('supportModal').classList.remove('hidden'); document.getElementById('supportModal').classList.add('flex'); }}
    function closeSupportModal() {{ document.getElementById('supportModal').classList.add('hidden'); document.getElementById('supportModal').classList.remove('flex'); }}
    </script>
    """
    return html

# ====================== বাকি সব রুট (সব আগের মতোই) ======================
# deposit, withdraw, deposits, withdraws, manage, actions, approve/reject, reply_support ইত্যাদি সব আছে।

@app.route("/deposit")
def deposit():
    uid = request.args.get("id")
    return f"""{ui()}<div class="max-w-md mx-auto p-4"><div class="card"><form action='/dep2'><input type='hidden' name='uid' value='{uid}'><input name='amount' placeholder='Amount' class='text-black w-full p-3 rounded mb-3'><select name='network' class='text-black w-full p-3 rounded mb-3'><option>TRC20</option><option>ERC20</option></select><button class='btn bg-gradient-to-r from-amber-400 to-yellow-500 text-black neon'>Next</button></form></div></div>"""

@app.route("/dep2")
def dep2():
    uid = request.args.get("uid")
    net = request.args.get("network")
    amount = request.args.get("amount")
    addr = TRC if net == "TRC20" else ERC
    return f"""{ui()}<div class="max-w-md mx-auto p-4"><div class="card">Send {amount} to:<br><span class="text-emerald-400 break-all">{addr}</span><form action='/dep3'><input type='hidden' name='uid' value='{uid}'><input type='hidden' name='amount' value='{amount}'><input type='hidden' name='network' value='{net}'><input name='txid' placeholder='TXID' class='text-black w-full p-3 rounded mt-4'><button class='btn bg-gradient-to-r from-amber-400 to-yellow-500 text-black neon'>Submit</button></form></div></div>"""

@app.route("/dep3")
def dep3():
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO deposits VALUES(NULL,?,?,?,?,?,?)", (request.args.get("uid"), request.args.get("amount"), request.args.get("network"), request.args.get("txid"), "pending", ""))
    conn.commit()
    conn.close()
    return "Deposit Pending"

@app.route("/withdraw")
def withdraw():
    uid = request.args.get("id")
    return f"""{ui()}<div class="max-w-md mx-auto p-4"><div class="card"><form action='/w2'><input type='hidden' name='uid' value='{uid}'><input name='amount' placeholder='Amount' class='text-black w-full p-3 rounded mb-3'><input name='address' placeholder='Wallet Address' class='text-black w-full p-3 rounded mb-3'><select name='network' class='text-black w-full p-3 rounded mb-3'><option>TRC20</option><option>ERC20</option></select><button class='btn bg-gradient-to-r from-red-500 to-rose-600 text-white'>Submit</button></form></div></div>"""

@app.route("/w2")
def w2():
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO withdraws VALUES(NULL,?,?,?,?,?,?)", (request.args.get("uid"), request.args.get("amount"), request.args.get("address"), request.args.get("network"), "pending", ""))
    conn.commit()
    conn.close()
    return "Withdraw Pending"

@app.route("/deposits")
def deposits():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, user_id, amount, network, txid FROM deposits WHERE status='pending'")
    data = c.fetchall()
    conn.close()

    html = f"""{ui()}
    <div class="max-w-md mx-auto p-4">
        <h2 class="text-amber-400 text-center text-xl mb-4">Pending Deposits</h2>
        <div class="space-y-4">
    """
    if not data:
        html += "<div class='text-center py-10 text-gray-400'>No pending deposits yet</div>"
    else:
        for d in data:
            html += f"""
            <div class="card p-5">
                <p class="text-white"><strong>User ID:</strong> {d[1]}</p>
                <p class="text-emerald-400"><strong>Amount:</strong> {d[2]} USD</p>
                <p><strong>Network:</strong> {d[3]}</p>
                <p><strong>TXID:</strong> {d[4]}</p>
                <div class="mt-5 flex gap-3">
                    <a href='/approve_dep?id={d[0]}' class='btn bg-green-500 flex-1'>Approve</a>
                    <form action='/reject_dep' class="flex-1">
                        <input type='hidden' name='id' value='{d[0]}'>
                        <input name='reason' placeholder="Reject reason..." class='text-black w-full mb-3 p-3 rounded'>
                        <button type='submit' class='btn bg-red-500 w-full'>Reject</button>
                    </form>
                </div>
            </div>
            """
    html += "</div></div>"
    return html

@app.route("/withdraws")
def withdraws():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, user_id, amount, address, network FROM withdraws WHERE status='pending'")
    data = c.fetchall()
    conn.close()

    html = f"""{ui()}
    <div class="max-w-md mx-auto p-4">
        <h2 class="text-amber-400 text-center text-xl mb-4">Pending Withdraws</h2>
        <div class="space-y-4">
    """
    if not data:
        html += "<div class='text-center py-10 text-gray-400'>No pending withdraws yet</div>"
    else:
        for d in data:
            html += f"""
            <div class="card p-5">
                <p class="text-white"><strong>User ID:</strong> {d[1]}</p>
                <p class="text-emerald-400"><strong>Amount:</strong> {d[2]} USD</p>
                <p><strong>Address:</strong> {d[3]}</p>
                <p><strong>Network:</strong> {d[4]}</p>
                <div class="mt-5 flex gap-3">
                    <a href='/approve_w?id={d[0]}' class='btn bg-green-500 flex-1'>Approve</a>
                    <form action='/reject_w' class="flex-1">
                        <input type='hidden' name='id' value='{d[0]}'>
                        <input name='reason' placeholder="Reject reason..." class='text-black w-full mb-3 p-3 rounded'>
                        <button type='submit' class='btn bg-red-500 w-full'>Reject</button>
                    </form>
                </div>
            </div>
            """
    html += "</div></div>"
    return html

@app.route("/manage")
def manage():
    uid = request.args.get("uid")
    return f"""{ui()}
    <div class="max-w-md mx-auto p-4">
    <h2 class="text-amber-400 text-center text-xl mb-6">Manage User {uid}</h2>

    <div class="card">
        <form action='/add'>
            <input type='hidden' name='uid' value='{uid}'>
            <input name='amount' placeholder='Add Main Balance' class='text-black w-full p-3 rounded mb-3'>
            <button class='btn bg-green-500 w-full'>Add Main Balance</button>
        </form>
    </div>

    <div class="card mt-3">
        <form action='/add_reward'>
            <input type='hidden' name='uid' value='{uid}'>
            <input name='amount' placeholder='Add Reward Balance' class='text-black w-full p-3 rounded mb-3'>
            <button class='btn bg-purple-500 w-full'>Add Reward Balance</button>
        </form>
    </div>

    <div class="card mt-3">
        <form action='/remove'>
            <input type='hidden' name='uid' value='{uid}'>
            <input name='amount' placeholder='Remove Main Balance' class='text-black w-full p-3 rounded mb-3'>
            <button class='btn bg-red-500 w-full'>Remove Main Balance</button>
        </form>
    </div>

    <div class="card mt-3">
        <form action='/profit'>
            <input type='hidden' name='uid' value='{uid}'>
            <input name='p' placeholder='Profit % (e.g. 5)' class='text-black w-full p-3 rounded mb-3'>
            <button class='btn bg-blue-500 w-full'>Add Profit %</button>
        </form>
    </div>

    <div class="card mt-3">
        <form action='/msg'>
            <input type='hidden' name='uid' value='{uid}'>
            <textarea name='m' placeholder="Type message for user..." rows="3" class='text-black w-full p-3 rounded mb-3'></textarea>
            <button class='btn bg-yellow-500 text-black w-full'>Send Message</button>
        </form>
    </div>
    </div>
    """

@app.route("/add")
def add():
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance=balance+? WHERE id=?", (request.args.get("amount"), request.args.get("uid")))
    conn.commit()
    conn.close()
    return "Main Balance Added"

@app.route("/add_reward")
def add_reward():
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET reward_balance=reward_balance+? WHERE id=?", (request.args.get("amount"), request.args.get("uid")))
    conn.commit()
    conn.close()
    return "Reward Balance Added"

@app.route("/remove")
def remove():
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance=balance-? WHERE id=?", (request.args.get("amount"), request.args.get("uid")))
    conn.commit()
    conn.close()
    return "Main Balance Removed"

@app.route("/profit")
def profit():
    uid = request.args.get("uid")
    p = float(request.args.get("p"))
    conn = db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = c.fetchone()[0]
    pr = bal * (p / 100)
    c.execute("UPDATE users SET balance=balance+?, profit=?, total_profit=total_profit+? WHERE id=?", (pr, pr, pr, uid))
    conn.commit()
    conn.close()
    return "Profit Added"

@app.route("/msg")
def msg():
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (request.args.get("uid"), request.args.get("m")))
    conn.commit()
    conn.close()
    return "Message Sent"

@app.route("/broadcast")
def broadcast():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id FROM users")
    for u in c.fetchall():
        c.execute("INSERT INTO messages VALUES(NULL,?,?)", (u[0], request.args.get("m")))
    conn.commit()
    conn.close()
    return "Broadcast Done"

@app.route("/approve_dep")
def approve_dep():
    conn = db()
    c = conn.cursor()
    id_ = request.args.get("id")
    c.execute("SELECT user_id, amount FROM deposits WHERE id=?", (id_,))
    d = c.fetchone()
    c.execute("UPDATE users SET balance=balance+? WHERE id=?", (d[1], d[0]))
    c.execute("UPDATE deposits SET status='approved' WHERE id=?", (id_,))
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (d[0], f"Deposit Approved {d[1]} USD"))
    conn.commit()
    conn.close()
    return "✅ Deposit Approved"

@app.route("/reject_dep")
def reject_dep():
    conn = db()
    c = conn.cursor()
    id_ = request.args.get("id")
    reason = request.args.get("reason") or "No reason given"
    c.execute("SELECT user_id FROM deposits WHERE id=?", (id_,))
    uid = c.fetchone()[0]
    c.execute("UPDATE deposits SET status='rejected', reason=? WHERE id=?", (reason, id_))
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (uid, f"Deposit Rejected: {reason}"))
    conn.commit()
    conn.close()
    return "❌ Deposit Rejected"

@app.route("/approve_w")
def approve_w():
    conn = db()
    c = conn.cursor()
    id_ = request.args.get("id")
    c.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (id_,))
    w = c.fetchone()
    c.execute("UPDATE users SET balance=balance-? WHERE id=?", (w[1], w[0]))
    c.execute("UPDATE withdraws SET status='approved' WHERE id=?", (id_,))
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (w[0], f"Withdraw Approved {w[1]} USD"))
    conn.commit()
    conn.close()
    return "✅ Withdraw Approved"

@app.route("/reject_w")
def reject_w():
    conn = db()
    c = conn.cursor()
    id_ = request.args.get("id")
    reason = request.args.get("reason") or "No reason given"
    c.execute("SELECT user_id FROM withdraws WHERE id=?", (id_,))
    uid = c.fetchone()[0]
    c.execute("UPDATE withdraws SET status='rejected', reason=? WHERE id=?", (reason, id_))
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (uid, f"Withdraw Rejected: {reason}"))
    conn.commit()
    conn.close()
    return "❌ Withdraw Rejected"

@app.route("/reply_support")
def reply_support():
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES(NULL,?,?)", (request.args.get("uid"), "Admin: " + request.args.get("reply")))
    conn.commit()
    conn.close()
    return "Reply Sent"

# ====================== RUN ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)