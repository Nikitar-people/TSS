from flask import Flask, request, render_template, redirect, jsonify, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import(LoginManager, login_user, logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
import os, secrets
from dotenv import load_dotenv
import os

load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.Text, nullable = False)
    rank = db.Column(db.Text, nullable = False)
    time = db.Column(db.Text, nullable = False)
    status = db.Column(db.Text, nullable = False)
    notified_at = db.Column(db.DateTime, nullable = True)
    arrived_at = db.Column(db.DateTime, nullable = True)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default = datetime.utcnow)
    active = db.Column(db.Boolean, default = True)
    ended_at   = db.Column(db.DateTime, nullable=True)
    total_count   = db.Column(db.Integer, default=0)
    arrived_count = db.Column(db.Integer, default=0)




class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actor = db.Column(db.String(50), default="duty")  
    action = db.Column(db.String(50), nullable=False) 
    person_id = db.Column(db.Integer, nullable=True)   
    person_fio = db.Column(db.String(200), nullable=True)  
    details = db.Column(db.Text, nullable=True)        






class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="duty")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)




class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True, index=True)
    person_id   = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True, index=True)
    person_fio  = db.Column(db.String(200))
    person_rank = db.Column(db.String(100))
    notified_at = db.Column(db.DateTime, nullable=True)
    arrived_at  = db.Column(db.DateTime, nullable=True)
    final_status = db.Column(db.String(20), nullable=True)  
    delay_sec    = db.Column(db.Integer, nullable=True)








# with app.app_context():
#     db.create_all()




@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        u = User.query.filter_by(username="duty").first()

        if u and u.check_password(password):
            session["duty"] = True
            session["user_id"] = u.id
            log_action("login", details="Дежурный вошёл")
            db.session.commit()
        # if request.form.get("password") == PASSWORD:
            
            return redirect(url_for('index'))
        return render_template('login.html', error = "Неверный пароль")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))







# Главная 
@app.route('/')
def index():
    return render_template('index.html', role = 'duty' if session.get("duty") else "viewer")



#Журнал
ACTION_LABEL = {
    "start":  "▶ Объявление прибытия",
    "stop":   "■ Остановка учёта",
    "reset":  "↺ Сброс статусов",
    "notify": "📢 Оповещение",
    "arrive": "✅ Прибытие",
    "status_change": "🔄 Смена статуса",
    "person_delete": "🗑 Удаление сотрудника",
    "person_edit":     "✏ Редактирование сотрудника",
    "journal_clear":   "🧹 Очистка журнала",
    "reports_clear":   "🧹 Очистка отчётов",
    "person_clear_history": "🧽 Очистка истории сотрудника",
    "history_clear_all":    "🧽 Очистка всей истории",
    "login":  "🔑 Вход",
    "logout": "🚪 Выход",
}

@app.route("/api/journal")
def api_journal():
    limit = int(request.args.get("limit", 200))
    rows = Action.query.order_by(Action.timestamp.desc()).limit(limit).all()
    return jsonify({
        "rows": [{
            "id": a.id,
            "time": a.timestamp.strftime("%d.%m.%Y %H:%M:%S"),
            "action": a.action,
            "action_label": ACTION_LABEL.get(a.action, a.action),
            "person_fio": a.person_fio,
            "details": a.details,
        } for a in rows]
    })


@app.route('/journal')
def journal():
    if not session.get("duty"):
        return redirect(url_for('login'))
    return render_template('journal.html')








#Настройки
@app.route('/settings')
def settings():
    if not session.get("duty"):
        return redirect(url_for('login'))
    return render_template('settings.html')


















#api
@app.route("/api/state")
def api_state():
    s = Session.query.filter_by(active=True).first()
    rows = Person.query.order_by(Person.id).all()
    return jsonify({
        "active": bool(s),
        "started": s.started_at.isoformat() if s else None,
        "rows": [{
            "id": p.id,
            "rank": p.rank,
            "fio": p.fio,
            "status": p.status,
            "notified_at": p.notified_at,
            "arrived_at": p.arrived_at,
        } for p in rows]
    })





def _duty():
    return session.get("duty")



def log_action(action, person=None, details=None):
    """Записать событие в журнал."""
    a = Action(
        action=action,
        person_id=person.id if person else None,
        person_fio=person.fio if person else None,
        details=details,
    )
    db.session.add(a)





@app.route('/api/start', methods=["POST"])
def api_start():
    if not _duty():
        return jsonify({"ok": False}), 403 
    if Session.query.filter_by(active=True).first():
        return jsonify({"ok": False, "error": "уже заполнено"}), 400
    

    working = [p for p in Person.query.all()
            if p.status not in ('vacation', 'trip', 'duty', 'sick')]


    s = Session(started_at = datetime.utcnow(), active = True)
    db.session.add(s)
    db.session.flush() 
    for p in Person.query.all():
        #################################################################################################################
        n = Notification(
            session_id=s.id,
            person_id=p.id,
            person_fio=p.fio,
            person_rank=p.rank,
            final_status=p.status if p.status in ('vacation','trip','duty','sick') else None,
        )
        db.session.add(n)
        #################################################################################################################
        # p.status = "present"
        p.notified_at = None
        p.arrived_at = None
    log_action("start", details=f"Объявлено прибытие. Всего: {len(working)}")
    db.session.commit()
    return jsonify({"ok": True, "started_at": s.started_at.isoformat()})


@app.route('/api/stop', methods=["POST"]) 
def api_stop():
    if not _duty():
        return jsonify({"ok": False}), 403
    # Session.query.filter_by(active = True).update({"active": False})
    s = Session.query.filter_by(active=True).first()
    if s:
        s.active = False
        s.ended_at = datetime.utcnow()
        s.arrived_count = Person.query.filter_by(status="arrived").count()
        ############################################################
        for n in Notification.query.filter_by(session_id=s.id).all():
            if not n.final_status:
                n.final_status = "absent"
        ############################################################
        log_action("stop", details=f"Учёт остановлен. Прибыло: {s.arrived_count}")
    db.session.commit()
    return jsonify({"ok": True})


@app.route('/api/reset', methods=["POST"])
def api_reset():
    if not _duty():
        return jsonify({"ok": False}), 403
    for p in Person.query.all():
        if p.status == "notified" or p.status == "arrived":
            p.status = "present"
        p.notified_at = None
        p.arrived_at = None
    log_action("reset", details="Статусы сброшены")
    db.session.commit() 
    return jsonify({"ok": True})



@app.route("/api/notify", methods=["POST"])
def api_notify():
    if not _duty(): return jsonify({"ok": False}), 403
    pid = request.json.get("person_id")
    p = db.session.get(Person, pid)
    if p and p.status == "present":
        #######################################################
        now = datetime.utcnow()
        ###################################################
        p.status = "notified"
        p.notified_at = datetime.utcnow()   
        #################################################
        s = Session.query.filter_by(active=True).first()
        if s:
            n = Notification.query.filter_by(session_id=s.id, person_id=p.id).first()
            if n:
                n.notified_at = now
        #############################################################
        log_action("notify", person=p)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/arrive", methods=["POST"])
def api_arrive():
    if not _duty(): return jsonify({"ok": False}), 403
    pid = request.json.get("person_id")

    p = db.session.get(Person, pid)
    if p and p.status == "notified":
        now = datetime.utcnow()
        p.status = "arrived"
        p.arrived_at = datetime.utcnow()  
        ########################################################
        s = Session.query.filter_by(active=True).first()
        if s:
            n = Notification.query.filter_by(session_id=s.id, person_id=p.id).first()
            if n:
                n.arrived_at = now
                n.final_status = "arrived"
                if n.notified_at:
                    n.delay_sec = int((now - n.notified_at).total_seconds())
        ############################################################### 
        log_action("arrive", person=p)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/location", methods=["POST"])
def api_location():
    if not _duty(): return jsonify({"ok": False}), 403
    data = request.json
    p = db.session.get(Person, data["person_id"])
    if p:
        old = p.status
        p.status = data["status"]
        p.notified_at = None
        p.arrived_at = None
        ###########################################
        s = Session.query.filter_by(active=True).first()
        if s:
            n = Notification.query.filter_by(session_id=s.id, person_id=p.id).first()
            if n:
                n.final_status = data["status"]
        ###################################################
        log_action("status_change", person=p, details=f"{old} → {data['status']}")

    db.session.commit()
    return jsonify({"ok": True})






@app.route("/api/people")
def api_people():
    if not _duty():
        return jsonify({"ok": False}), 403
    rows = Person.query.order_by(Person.id).all()
    return jsonify({"rows": [{
        "id": p.id,
        "rank": p.rank,
        "fio": p.fio,
        "status": p.status,
    } for p in rows]})


@app.route("/api/people/add", methods=["POST"])
def api_people_add():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    d = request.json or {}
    rank = (d.get("rank") or "").strip()
    fio  = (d.get("fio")  or "").strip()
    status = d.get("status") or "present"

    if not rank or not fio:
        return jsonify({"ok": False, "error": "Заполните звание и ФИО"}), 400

    if status not in ("present", "notified", "arrived",
                      "vacation", "trip", "duty", "sick"):
        return jsonify({"ok": False, "error": "Неверный статус"}), 400

    p = Person(rank=rank, fio=fio, time="1", status=status)
    db.session.add(p)
    db.session.flush()   # получаем p.id до коммита
    log_action("person_add", person=p, details=f"Добавлен: {rank} {fio}")
    db.session.commit()

    return jsonify({"ok": True, "id": p.id})


@app.route("/api/people/update", methods=["POST"])
def api_people_update():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    d = request.json or {}
    p = db.session.get(Person, d.get("id"))
    if not p:
        return jsonify({"ok": False, "error": "Не найден"}), 404

    old = f"{p.rank} {p.fio}"
    if "rank" in d and d["rank"]:
        p.rank = d["rank"].strip()
    if "fio" in d and d["fio"]:
        p.fio = d["fio"].strip()
    if "status" in d and d["status"]:
        p.status = d["status"]

    log_action("person_edit", person=p, details=f"{old} → {p.rank} {p.fio}")
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/people/delete", methods=["POST"])
def api_people_delete():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    d = request.json or {}
    p = db.session.get(Person, d.get("id"))
    if not p:
        return jsonify({"ok": False, "error": "Не найден"}), 404

    s = Session.query.filter_by(active=True).first()
    if s and p.status in ("notified", "arrived"):
        return jsonify({
            "ok": False,
            "error": "Нельзя удалить: человек уже оповещён или прибыл"
        }), 400

    log_action("person_delete", person=p, details=f"Удалён: {p.rank} {p.fio}")
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})










@app.route("/api/people/clear_history", methods=["POST"])
def api_people_clear_history():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    d = request.json or {}
    p = db.session.get(Person, d.get("id"))
    if not p:
        return jsonify({"ok": False, "error": "Не найден"}), 404

    # не удаляем записи активной сессии — иначе карточка на главной потеряет время
    s = Session.query.filter_by(active=True).first()
    q = Notification.query.filter_by(person_id=p.id)
    if s:
        q = q.filter(Notification.session_id != s.id)

    count = q.delete(synchronize_session=False)
    log_action("person_clear_history", person=p,
               details=f"Очищена история: {count} записей")
    db.session.commit()
    return jsonify({"ok": True, "deleted": count})


@app.route("/api/clear_all_history", methods=["POST"])
def api_clear_all_history():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    s = Session.query.filter_by(active=True).first()
    q = Notification.query
    if s:
        q = q.filter(Notification.session_id != s.id)

    count = q.delete(synchronize_session=False)
    log_action("history_clear_all", details=f"Очищена вся история: {count} записей")
    db.session.commit()
    return jsonify({"ok": True, "deleted": count})




















# ---------- API настроек: пароль ----------

@app.route("/api/password", methods=["POST"])
def api_password():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403

    u = User.query.filter_by(username="duty").first()
    if not u:
        return jsonify({"ok": False, "error": "Пользователь не найден"}), 404
    d = request.json or {}
    if not u.check_password(d.get("old", "")):
        return jsonify({"ok": False, "error": "Неверный текущий пароль"}), 400
    new = d.get("new") or "".strip()
    if len(new) < 4:
        return jsonify({"ok": False, "error": "Минимум 4 символа"}), 400


    u.set_password(new)                     # ← хеш пересчитывается
    log_action("password_change", details="Пароль изменён")
    db.session.commit()
    return jsonify({"ok": True})


# ---------- API настроек: опасные действия ----------

@app.route("/api/clear_journal", methods=["POST"])
def api_clear_journal():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403
    Action.query.delete()
    log_action("journal_clear", details="Журнал очищен")
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/clear_reports", methods=["POST"])
def api_clear_reports():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403
    Session.query.delete()
    log_action("reports_clear", details="История сессий очищена")
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/factory_reset", methods=["POST"])
def api_factory_reset():
    if not _duty():
        return jsonify({"ok": False, "error": "Нет прав"}), 403
    Person.query.delete()
    Session.query.delete()
    Action.query.delete()
    db.session.commit()
    return jsonify({"ok": True})











@app.route("/api/reports/sessions")
def api_reports_sessions():
    sessions = Session.query.order_by(Session.started_at.desc()).all()

    def fmt_dt(dt):  return dt.strftime("%d.%m.%Y %H:%M") if dt else None
    def fmt_dur(sec):
        if sec is None or sec < 0: return None
        h, r = divmod(sec, 3600); m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    rows = []
    for s in sessions:
        dur = int((s.ended_at - s.started_at).total_seconds()) if s.ended_at else None

        # считаем текущее число прибывших по живой БД,
        # чтобы для активной сессии тоже было актуально
        arrived = Person.query.filter_by(status="arrived").count()
        total   = Person.query.filter(
            Person.status.notin_(("vacation", "trip", "duty", "sick"))
        ).count()

        # для завершённых берём снимок
        if not s.active:
            arrived = s.arrived_count if s.arrived_count else arrived
            total   = s.total_count   if s.total_count   else total

        pct = round(arrived / total * 100) if total else 0

        rows.append({
            "id": s.id,
            "started_at": fmt_dt(s.started_at),
            "ended_at":   fmt_dt(s.ended_at),
            "duration":   fmt_dur(dur),
            "total":      total,
            "arrived":    arrived,
            "percent":    pct,
            "active":     s.active,
        })
    return jsonify({"rows": rows})


@app.route("/api/reports/summary")
def api_reports_summary():
    total_sessions = Session.query.count()
    closed = Session.query.filter_by(active=False).count()

    # считаем по всем закрытым сессиям с сохранёнными снимками
    total_people  = 0
    total_arrived = 0
    for s in Session.query.filter_by(active=False).all():
        total_people  += s.total_count   or 0
        total_arrived += s.arrived_count or 0

    avg_pct = round(total_arrived / total_people * 100) if total_people else 0

    return jsonify({
        "sessions": total_sessions,
        "closed":   closed,
        "people":   total_people,
        "arrived":  total_arrived,
        "avg_pct":  avg_pct,
    })


@app.route("/api/reports/people")
def api_reports_people():
    rows = []
    for p in Person.query.order_by(Person.rank, Person.fio).all():
        delay_sec = None
        if p.notified_at and p.arrived_at:
            delay_sec = int((p.arrived_at - p.notified_at).total_seconds())
            if delay_sec < 0: delay_sec = 0

        def fmt_dur(s):
            if s is None: return None
            h, r = divmod(s, 3600); m, ss = divmod(r, 60)
            return f"{h:02d}:{m:02d}:{ss:02d}"

        rows.append({
            "fio": p.fio,
            "rank": p.rank,
            "status": p.status,
            "notified_at": p.notified_at.strftime("%H:%M:%S") if p.notified_at else None,
            "arrived_at":  p.arrived_at.strftime("%H:%M:%S")  if p.arrived_at  else None,
            "delay": fmt_dur(delay_sec),
        })
    return jsonify({"rows": rows})



@app.route("/api/reports/people_all")
def api_reports_people_all():
    rows = []

    for p in Person.query.order_by(Person.rank, Person.fio).all():
        ns = Notification.query.filter_by(person_id=p.id).all()

        total     = len(ns)
        arrived   = sum(1 for n in ns if n.final_status == "arrived")
        absent    = sum(1 for n in ns if n.final_status == "absent")
        vacation  = sum(1 for n in ns if n.final_status == "vacation")
        trip      = sum(1 for n in ns if n.final_status == "trip")
        duty      = sum(1 for n in ns if n.final_status == "duty")
        sick      = sum(1 for n in ns if n.final_status == "sick")

        delays = [n.delay_sec for n in ns if n.delay_sec is not None]
        avg_delay = int(sum(delays) / len(delays)) if delays else None
        min_delay = min(delays) if delays else None
        max_delay = max(delays) if delays else None

        invited = total - vacation - trip - duty - sick
        pct = round(arrived / invited * 100) if invited else 0

        def fmt(sec):
            if sec is None: return None
            h, r = divmod(sec, 3600); m, s = divmod(r, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        rows.append({
            "id": p.id,
            "fio": p.fio,
            "rank": p.rank,
            "current_status": p.status,
            "total":    total,
            "invited":  invited,
            "arrived":  arrived,
            "absent":   absent,
            "vacation": vacation,
            "trip":     trip,
            "duty":     duty,
            "sick":     sick,
            "pct":      pct,
            "avg_delay": fmt(avg_delay),
            "min_delay": fmt(min_delay),
            "max_delay": fmt(max_delay),
        })

    return jsonify({"rows": rows})
















@app.route('/reports')
def reports():
    if not session.get("duty"):
        return redirect(url_for('login'))
    return render_template('reports.html')






























# ---------- ЗАПУСК ----------
def init_db():
    with app.app_context():
        db.create_all()



        if User.query.count() == 0:
            initial = os.environ.get("DUTY_PASSWORD")
            if not initial:
                raise RuntimeError(
                    "Задайте DUTY_PASSWORD перед первым запуском:\n"
                    "  Windows:  set DUTY_PASSWORD=12345\n"
                    "  Linux:    export DUTY_PASSWORD=12345"
                )
            u = User(username="duty", role="duty")
            u.set_password(initial)    
            db.session.add(u)
            print("[init] Пользователь duty создан")







        if Person.query.count() == 0:
            demo = [
                ("полковник", "Иванов Иван Иванович", "1", "present"),
    ("майор",     "Петров Пётр Петрович", "1", "present"),
    ("капитан",   "Сидоров Семён Семёнович", "1", "present"),
    ("лейтенант", "Кузнецов Алексей Игоревич", "1", "present"),
    ("сержант",   "Смирнов Николай Петрович", "1", "present")
            ]
            for rank, fio, time, status in demo:
                db.session.add(Person(rank=rank, fio=fio, time = time, status = status))
            db.session.commit()













if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
    





