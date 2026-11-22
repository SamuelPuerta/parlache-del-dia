"""Almacen en memoria con la misma interfaz y las mismas condiciones que DynamoStore."""
import copy


class FakeStore:
    def __init__(self):
        self.words, self.daily, self.players = {}, {}, {}
        self.attempts, self.results = {}, {}

    def seed_words(self, keys):
        for k in keys:
            self.words[k] = {"word_key": k, "display": k, "meaning": "m", "example": "e",
                             "region": "r", "source": "s"}

    @staticmethod
    def _c(v):
        return copy.deepcopy(v)

    def get_daily(self, d):
        return self._c(self.daily.get(d))

    def get_word(self, k):
        return self._c(self.words.get(k))

    def get_player(self, p):
        return self._c(self.players.get(p))

    def get_attempt(self, p, d):
        return self._c(self.attempts.get(f"{p}#{d}"))

    def scan_words(self):
        return [{k: v for k, v in w.items() if k in ("word_key", "used_on")}
                for w in self.words.values()]

    def create_daily(self, d, word_key, puzzle_number, created_at):
        if d in self.daily:
            return False
        self.daily[d] = {"date": d, "word_key": word_key, "puzzle_number": puzzle_number,
                         "created_at": created_at}
        self.words[word_key]["used_on"] = d
        return True

    def clear_used_on(self, keys):
        for k in keys:
            self.words[k].pop("used_on", None)

    def create_player(self, pid, alias, created_at):
        if pid in self.players:
            return False, self._c(self.players[pid])
        self.players[pid] = {"player_id": pid, "alias": alias, "current_streak": 0,
                             "best_streak": 0, "wins": 0, "played": 0, "gsi_pk": "ALL",
                             "created_at": created_at}
        return True, self._c(self.players[pid])

    def _attempt_ok(self, pid, d, prev_n):
        att = self.attempts.get(f"{pid}#{d}")
        return att is None or (att["n_attempts"] == prev_n and att["status"] == "playing")

    def _write_attempt(self, pid, d, entry, prev_n, status, now_iso, ttl):
        att = self.attempts.setdefault(f"{pid}#{d}", {"guesses": [], "started_at": now_iso})
        att.update({"player_id": pid, "date": d, "n_attempts": prev_n + 1, "status": status,
                    "ttl": ttl})
        att["guesses"].append(entry)
        if status != "playing":
            att["finished_at"] = now_iso

    def save_progress(self, pid, d, entry, prev_n, now_iso, ttl):
        if not self._attempt_ok(pid, d, prev_n):
            return False
        self._write_attempt(pid, d, entry, prev_n, "playing", now_iso, ttl)
        return True

    def finish_game(self, *, player_id, date_iso, entry, prev_n, status, now_iso, ttl,
                    current_streak, best_streak, alias):
        p = self.players[player_id]
        if not self._attempt_ok(player_id, date_iso, prev_n) or p.get("last_win_date") == date_iso:
            return False
        self._write_attempt(player_id, date_iso, entry, prev_n, status, now_iso, ttl)
        p["played"] += 1
        if status == "won":
            p.update(wins=p["wins"] + 1, current_streak=current_streak,
                     best_streak=best_streak, last_win_date=date_iso)
            n = prev_n + 1
            self.results[(date_iso, player_id)] = {
                "date": date_iso, "player_id": player_id, "alias": alias, "attempts": n,
                "finished_at": now_iso, "score_key": f"{n:02d}#{now_iso}"}
        else:
            p["current_streak"] = 0
        return True

    def ranking_daily(self, d, limit):
        rows = [r for (day, _), r in self.results.items() if day == d]
        return self._c(sorted(rows, key=lambda r: r["score_key"])[:limit])

    def ranking_streak(self, limit):
        rows = sorted(self.players.values(), key=lambda p: -p["current_streak"])
        return self._c(rows[:limit])

    def put_words(self, items):
        for it in items:
            old = self.words.get(it["word"], {})
            rec = {"word_key": it["word"], "display": it["display"], "meaning": it["meaning"],
                   "example": it.get("example", ""), "region": it["region"], "source": it["source"]}
            if old.get("used_on"):
                rec["used_on"] = old["used_on"]
            self.words[it["word"]] = rec
        return len(items)
