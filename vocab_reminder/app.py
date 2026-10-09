"""Vocal Reminder Poke Version — Windows desktop UI."""

import os
import sqlite3
import sys
import time
from pathlib import Path

from PySide6.QtCore import QLockFile, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QSystemTrayIcon,
)

from .storage import Store, data_dir


ASSETS = Path(__file__).resolve().parents[1] / "assets"
ORBS = ("poke_ball", "great_ball", "ultra_ball", "master_ball", "premier_ball", "luxury_ball")
BALL_NAMES = {"poke_ball": "Poké Ball", "great_ball": "Great Ball", "ultra_ball": "Ultra Ball",
              "master_ball": "Master Ball", "premier_ball": "Premier Ball", "luxury_ball": "Luxury Ball"}
POKEMON = ("pikachu", "charmander", "bulbasaur", "squirtle", "eevee", "jigglypuff")


def picture(name, size):
    pix = QPixmap(str(ASSETS / name))
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw if pythonw.exists() else sys.executable}" "{Path(__file__).resolve().parents[1] / "main.py"}"'


def set_autostart(enabled):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                        winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "VocalReminderPoke", 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, "VocalReminderPoke")
            except FileNotFoundError:
                pass


class Orb(QWidget):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(94, 104)
        self.label = QLabel(self)
        self.label.setGeometry(7, 2, 80, 80)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hint = QLabel("+ TỪ MỚI", self)
        self.hint.setGeometry(0, 81, 94, 20)
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setStyleSheet("background:#15223c; color:#fff6df; border:2px solid #07132a; font:bold 10px Consolas")
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.drag_start = None
        self.start_pos = None

    def set_orb(self, name):
        self.label.setPixmap(picture(f"orb_{name}.png", 80))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.globalPosition().toPoint()
            self.start_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_start and event.buttons() & Qt.LeftButton:
            self.move(self.start_pos + event.globalPosition().toPoint() - self.drag_start)

    def mouseReleaseEvent(self, event):
        if self.drag_start:
            delta = event.globalPosition().toPoint() - self.drag_start
            self.drag_start = None
            if delta.manhattanLength() < 6:
                self.on_click()


class WordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bắt từ vựng mới")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        header = QLabel("✦ THÊM TỪ VÀO QUẢ CẦU")
        header.setObjectName("heading")
        layout.addWidget(header)
        form = QFormLayout()
        self.term = QLineEdit()
        self.kind = QComboBox()
        self.kind.setEditable(True)
        self.kind.addItems(["", "noun", "verb", "adjective", "adverb", "phrase", "other"])
        self.en = QLineEdit()
        self.vi = QLineEdit()
        self.example = QTextEdit()
        self.example.setFixedHeight(90)
        for label, widget in (("Từ vựng *", self.term), ("Loại từ", self.kind),
                              ("Ý nghĩa tiếng Anh", self.en), ("Ý nghĩa tiếng Việt *", self.vi),
                              ("Ví dụ", self.example)):
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("LƯU TỪ")
        save.clicked.connect(self.validate)
        cancel = QPushButton("HỦY")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def validate(self):
        if not self.term.text().strip() or not self.vi.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Hãy điền từ vựng và ý nghĩa tiếng Việt.")
            return
        self.accept()

    def values(self):
        return (self.term.text(), self.kind.currentText(), self.en.text(),
                self.vi.text(), self.example.toPlainText())


class ReviewDialog(QDialog):
    def __init__(self, store, words, orb, pokemon, parent=None):
        super().__init__(parent)
        self.store, self.words, self.index = store, words, 0
        self.orb, self.pokemon = orb, pokemon
        self.setWindowTitle("Poké Review • ôn từ")
        self.setMinimumSize(520, 460)
        layout = QVBoxLayout(self)
        self.mascot = QLabel()
        self.mascot.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mascot)
        self.progress = QLabel()
        self.progress.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress)
        self.term = QLabel()
        self.term.setObjectName("cardTerm")
        self.term.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.term)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignCenter)
        self.details.setMinimumHeight(130)
        layout.addWidget(self.details)
        self.button = QPushButton("LẬT THẺ")
        self.button.clicked.connect(self.advance)
        layout.addWidget(self.button)
        self.revealed = False
        self.render()

    def render(self):
        word = self.words[self.index]
        self.mascot.setPixmap(picture(f"pokemon_{self.pokemon}.png", 155))
        self.progress.setText(f"THẺ {self.index + 1} / {len(self.words)}")
        self.term.setText(word["term"])
        self.details.setText("Hãy thử nhớ nghĩa trước khi lật thẻ ✦")
        self.button.setText("LẬT THẺ")
        self.revealed = False

    def advance(self):
        word = self.words[self.index]
        if not self.revealed:
            details = [f"[{word['part_of_speech']}]" if word["part_of_speech"] else "",
                       word["meaning_en"], word["meaning_vi"],
                       f"Ví dụ: {word['example']}" if word["example"] else ""]
            self.details.setText("\n".join(s for s in details if s))
            self.button.setText("HOÀN THÀNH" if self.index == len(self.words) - 1 else "TỪ TIẾP THEO →")
            self.revealed = True
            return
        self.store.record_review(word["id"])
        self.index += 1
        if self.index == len(self.words):
            self.mascot.setPixmap(picture(f"orb_{self.orb}.png", 155))
            QMessageBox.information(self, "Hoàn thành!", "Ôn xong rồi! Linh vật đã trở về quả cầu.")
            self.accept()
        else:
            self.render()


class MainWindow(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setWindowTitle("Vocal Reminder Poke Version")
        self.setWindowIcon(QIcon(str(ASSETS / "app_icon.ico")))
        self.resize(900, 670)
        self.setup_ui()
        self.orb = Orb(self.add_word)
        self.orb.move(self.store.settings("orb_x", 45), self.store.settings("orb_y", 220))
        self.orb.show()
        self.tray = QSystemTrayIcon(QIcon(str(ASSETS / "app_icon.ico")), self)
        menu = QMenu()
        for title, callback in (("Mở bảng điều khiển", self.show_main), ("Thêm từ", self.add_word),
                                ("Ôn ngay", self.review_now), ("Thoát", self.quit_app)):
            action = QAction(title, self)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_main() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        self.refresh_all()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(15000)
        now = time.time()
        if self.store.settings("next_review") is None:
            self.store.set_setting("next_review", now + self.interval.value() * 3600)
        if self.store.settings("next_water") is None:
            self.store.set_setting("next_water", now + 1800)
        if not self.store.settings("onboarded", False):
            QTimer.singleShot(0, self.first_setup)

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        heading = QLabel("◈  VOCAL REMINDER  /  POKE VERSION")
        heading.setObjectName("heading")
        outer.addWidget(heading)
        tagline = QLabel("Thu thập từ • Gặp lại đúng lúc • Học từng thẻ")
        outer.addWidget(tagline)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)

        home = QWidget()
        h = QVBoxLayout(home)
        row = QHBoxLayout()
        row.addWidget(QLabel("QUẢ CẦU ĐANG DÙNG"))
        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self.select_deck)
        row.addWidget(self.deck_combo, 1)
        create = QPushButton("+ TẠO QUẢ CẦU")
        create.clicked.connect(self.create_deck)
        row.addWidget(create)
        h.addLayout(row)
        art_row = QHBoxLayout()
        self.deck_art = QLabel()
        self.deck_art.setAlignment(Qt.AlignCenter)
        self.pokemon_art = QLabel()
        self.pokemon_art.setAlignment(Qt.AlignCenter)
        art_row.addStretch()
        art_row.addWidget(self.deck_art)
        art_row.addWidget(QLabel("→"))
        art_row.addWidget(self.pokemon_art)
        art_row.addStretch()
        h.addLayout(art_row)
        self.deck_summary = QLabel()
        self.deck_summary.setAlignment(Qt.AlignCenter)
        h.addWidget(self.deck_summary)
        actions = QHBoxLayout()
        for title, callback in (("+ THÊM TỪ", self.add_word), ("▶ ÔN NGAY", self.review_now)):
            btn = QPushButton(title)
            btn.clicked.connect(callback)
            actions.addWidget(btn)
        h.addLayout(actions)
        h.addStretch()
        self.tabs.addTab(home, "Quả cầu")

        words_tab = QWidget()
        w = QVBoxLayout(words_tab)
        self.word_table = QTableWidget(0, 5)
        self.word_table.setHorizontalHeaderLabels(["Từ", "Loại", "Nghĩa EN", "Nghĩa VI", "Ví dụ"])
        self.word_table.horizontalHeader().setStretchLastSection(True)
        self.word_table.setSelectionBehavior(QTableWidget.SelectRows)
        w.addWidget(self.word_table)
        delete = QPushButton("XÓA TỪ ĐÃ CHỌN")
        delete.clicked.connect(self.delete_word)
        w.addWidget(delete)
        self.tabs.addTab(words_tab, "Từ vựng")

        stats_tab = QWidget()
        s = QVBoxLayout(stats_tab)
        self.stats_label = QLabel()
        self.stats_label.setObjectName("stats")
        self.stats_label.setAlignment(Qt.AlignCenter)
        s.addWidget(self.stats_label)
        self.tabs.addTab(stats_tab, "Dashboard")

        settings_tab = QWidget()
        form = QFormLayout(settings_tab)
        self.interval = QDoubleSpinBox()
        self.interval.setRange(0.1, 24.0)
        self.interval.setSingleStep(0.5)
        self.interval.setValue(float(self.store.settings("interval", 1.0)))
        self.interval.setSuffix(" giờ")
        self.batch = QSpinBox()
        self.batch.setRange(1, 50)
        self.batch.setValue(int(self.store.settings("batch", 5)))
        self.water = QCheckBox("Nhắc uống nước và đi lại mỗi 30 phút")
        self.water.setChecked(bool(self.store.settings("water", True)))
        self.autostart = QCheckBox("Chạy cùng Windows khi đăng nhập")
        self.autostart.setChecked(bool(self.store.settings("autostart", False)))
        form.addRow("Chu kỳ ôn tập", self.interval)
        form.addRow("Số từ mỗi lần", self.batch)
        form.addRow(self.water)
        form.addRow(self.autostart)
        save = QPushButton("LƯU CÀI ĐẶT")
        save.clicked.connect(lambda: self.save_settings())
        form.addRow(save)
        self.tabs.addTab(settings_tab, "Cài đặt")

    def current_deck(self):
        return self.deck_combo.currentData()

    def refresh_all(self):
        selected = self.store.settings("selected_deck")
        self.deck_combo.blockSignals(True)
        self.deck_combo.clear()
        for deck in self.store.decks():
            self.deck_combo.addItem(deck["name"], deck["id"])
        match = self.deck_combo.findData(selected)
        self.deck_combo.setCurrentIndex(max(0, match))
        self.deck_combo.blockSignals(False)
        self.refresh_deck()

    def refresh_deck(self):
        deck_id = self.current_deck()
        if deck_id is None:
            return
        deck = next(d for d in self.store.decks() if d["id"] == deck_id)
        self.store.set_setting("selected_deck", deck_id)
        self.deck_art.setPixmap(picture(f"orb_{deck['orb']}.png", 190))
        self.pokemon_art.setPixmap(picture(f"pokemon_{deck['pokemon']}.png", 190))
        self.orb.set_orb(deck["orb"])
        total, reviewed, sessions, today = self.store.stats(deck_id)
        self.deck_summary.setText(f"{deck['name']}  •  {deck['pokemon'].title()}  •  {total} từ đã thu thập")
        self.stats_label.setText(f"{total}  TỪ ĐÃ LƯU\n\n{reviewed}  TỪ ĐÃ GẶP LẠI\n\n{sessions}  LƯỢT ÔN TẬP\n\n{today}  THẺ HÔM NAY")
        words = self.store.words(deck_id)
        self.word_table.setRowCount(len(words))
        for row, word in enumerate(words):
            for col, key in enumerate(("term", "part_of_speech", "meaning_en", "meaning_vi", "example")):
                item = QTableWidgetItem(word[key])
                item.setData(Qt.UserRole, word["id"])
                self.word_table.setItem(row, col, item)
        self.word_table.resizeColumnsToContents()

    def select_deck(self):
        self.refresh_deck()

    def create_deck(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Tạo quả cầu mới")
        layout = QFormLayout(dialog)
        name = QLineEdit()
        name.setPlaceholderText("Ví dụ: Tiếng Anh công sở")
        orb = QComboBox()
        for key in ORBS:
            orb.addItem(QIcon(str(ASSETS / f"orb_{key}.png")), BALL_NAMES[key], key)
        pokemon = QComboBox()
        for name in POKEMON:
            pokemon.addItem(QIcon(str(ASSETS / f"pokemon_{name}.png")), name.title(), name)
        layout.addRow("Tên bộ từ", name)
        layout.addRow("Quả cầu", orb)
        layout.addRow("Pokémon", pokemon)
        button = QPushButton("TẠO")
        button.clicked.connect(dialog.accept)
        layout.addRow(button)
        if dialog.exec() != QDialog.Accepted:
            return
        if not name.text().strip():
            QMessageBox.warning(self, "Thiếu tên", "Hãy đặt tên cho bộ từ.")
            return
        try:
            deck_id = self.store.add_deck(name.text(), orb.currentData(), pokemon.currentData())
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Tên đã có", "Một quả cầu đã dùng tên này.")
            return
        self.store.set_setting("selected_deck", deck_id)
        self.refresh_all()

    def first_setup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Thiết lập lần đầu")
        dialog.setMinimumWidth(430)
        layout = QFormLayout(dialog)
        title = QLabel("CHÀO MỪNG ĐẾN POKE REVIEW ✦")
        title.setObjectName("heading")
        layout.addRow(title)
        name = QLineEdit("Bộ từ đầu tiên")
        orb = QComboBox()
        for key in ORBS:
            orb.addItem(QIcon(str(ASSETS / f"orb_{key}.png")), BALL_NAMES[key], key)
        pokemon = QComboBox()
        for name in POKEMON:
            pokemon.addItem(QIcon(str(ASSETS / f"pokemon_{name}.png")), name.title(), name)
        hours = QDoubleSpinBox()
        hours.setRange(0.1, 24)
        hours.setValue(1)
        hours.setSuffix(" giờ")
        count = QSpinBox()
        count.setRange(1, 50)
        count.setValue(5)
        water = QCheckBox("Nhắc uống nước và đi lại mỗi 30 phút")
        water.setChecked(True)
        autostart = QCheckBox("Chạy cùng Windows khi đăng nhập")
        autostart.setChecked(True)
        for label, widget in (("Tên quả cầu đầu tiên", name), ("Loại quả cầu", orb),
                              ("Pokémon đi cùng", pokemon),
                              ("Chu kỳ ôn", hours), ("Số từ mỗi lần", count)):
            layout.addRow(label, widget)
        layout.addRow(water)
        layout.addRow(autostart)
        start = QPushButton("BẮT ĐẦU")
        start.clicked.connect(dialog.accept)
        layout.addRow(start)
        if dialog.exec() != QDialog.Accepted:
            return
        if not name.text().strip():
            name.setText("Bộ từ đầu tiên")
        self.store.update_deck(self.current_deck(), name.text(), orb.currentData(), pokemon.currentData())
        self.interval.setValue(hours.value())
        self.batch.setValue(count.value())
        self.water.setChecked(water.isChecked())
        self.autostart.setChecked(autostart.isChecked())
        if self.save_settings(show_message=False):
            self.store.set_setting("onboarded", True)
        self.refresh_all()

    def add_word(self):
        dialog = WordDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                self.store.add_word(self.current_deck(), *dialog.values())
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Từ đã có", "Từ này đã nằm trong quả cầu hiện tại.")
                return
            self.refresh_deck()
            self.tray.showMessage("Đã bắt được từ mới!", dialog.term.text(), QSystemTrayIcon.Information, 3000)

    def delete_word(self):
        row = self.word_table.currentRow()
        if row < 0:
            return
        item = self.word_table.item(row, 0)
        if QMessageBox.question(self, "Xóa từ", f"Xóa “{item.text()}” khỏi bộ từ?") == QMessageBox.Yes:
            self.store.delete_word(item.data(Qt.UserRole))
            self.refresh_deck()

    def review_now(self):
        deck_id = self.current_deck()
        words = self.store.next_batch(deck_id, self.batch.value())
        if not words:
            QMessageBox.information(self, "Chưa có từ", "Hãy thêm từ vựng vào quả cầu trước nhé.")
            return
        deck = next(d for d in self.store.decks() if d["id"] == deck_id)
        self.review = ReviewDialog(self.store, words, deck["orb"], deck["pokemon"], self)
        self.review.finished.connect(lambda _: self.refresh_deck())
        self.review.show()
        self.review.raise_()
        self.review.activateWindow()

    def tick(self):
        now = time.time()
        if now >= self.store.settings("next_review", now + 1):
            self.store.set_setting("next_review", now + self.interval.value() * 3600)
            if self.store.words(self.current_deck()):
                self.review_now()
        if self.water.isChecked() and now >= self.store.settings("next_water", now + 1):
            self.store.set_setting("next_water", now + 1800)
            self.tray.showMessage("Nghỉ một chút nhé!", "Uống nước và đứng dậy đi lại vài phút 💧",
                                  QSystemTrayIcon.Information, 10000)

    def save_settings(self, show_message=True):
        try:
            set_autostart(self.autostart.isChecked())
        except OSError as exc:
            QMessageBox.warning(self, "Không thể lưu khởi động cùng Windows", str(exc))
            return False
        self.store.set_setting("interval", self.interval.value())
        self.store.set_setting("batch", self.batch.value())
        self.store.set_setting("water", self.water.isChecked())
        self.store.set_setting("autostart", self.autostart.isChecked())
        self.store.set_setting("next_review", time.time() + self.interval.value() * 3600)
        self.store.set_setting("next_water", time.time() + 1800)
        if show_message:
            QMessageBox.information(self, "Đã lưu", "Cài đặt mới đã được áp dụng.")
        return True

    def show_main(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def quit_app(self):
        self.store.set_setting("orb_x", self.orb.x())
        self.store.set_setting("orb_y", self.orb.y())
        self.tray.hide()
        self.orb.close()
        self.store.close()
        QApplication.instance().quit()


STYLE = """
QWidget { background:#14213b; color:#f5eddb; font: 12px 'Consolas'; }
QMainWindow { background:#14213b; }
QLabel#heading { font:bold 22px 'Consolas'; color:#ffd56b; padding:12px 0; }
QLabel#cardTerm { font:bold 32px 'Consolas'; color:#ffd56b; padding:16px; background:#243858; border:3px solid #08142a; }
QLabel#stats { font:bold 22px 'Consolas'; color:#ffd56b; background:#243858; border:3px solid #08142a; padding:25px; }
QPushButton { background:#ed786e; color:#101b32; border:3px solid #08142a; padding:9px 14px; font:bold 12px 'Consolas'; }
QPushButton:hover { background:#ffd56b; }
QLineEdit,QTextEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTableWidget { background:#243858; color:#fff8e8; border:2px solid #08142a; padding:5px; selection-background-color:#ee796e; }
QTabWidget::pane { border:3px solid #08142a; padding:14px; }
QTabBar::tab { background:#243858; padding:10px 18px; border:2px solid #08142a; }
QTabBar::tab:selected { background:#ed786e; color:#101b32; }
QHeaderView::section { background:#334e70; color:#fff8e8; padding:7px; border:1px solid #08142a; }
QMessageBox QLabel { min-width:280px; }
"""


def run():
    app = QApplication(sys.argv)
    lock = QLockFile(str(data_dir() / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Đang chạy", "Vocal Reminder Poke đã chạy trên máy này.")
        return 0
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(str(ASSETS / "app_icon.ico")))
    window = MainWindow(Store())
    window.show()
    result = app.exec()
    lock.unlock()
    return result
