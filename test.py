import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkcalendar import DateEntry
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import webbrowser
import urllib.parse
from docx import Document
import logging
import hashlib
from functools import partial
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine



# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='repair_app.log'
)

# Константы
DB_NAME = "repairs.db"
TEMPLATE_PATH = "template.docx"
BACKUP_DIR = "backups"
ACTS_DIR = "Акты"

FIELDS = [
    "Серийный номер", "Серийный номер 2", "Номер HD", "Тип ремонта",
    "Виды работ", "Взятые запчасти", "Дата взятия", "Кол-во исследований",
    "Дата готовности", "Кол-во после ремонта", "Квартал", "Статус", "Модель", "Клиент"
]

REPAIR_TYPES = {"B": 0.6, "C": 1, "D": 1.5}

class AuthManager:
    """Менеджер аутентификации пользователей"""
    def __init__(self):
        self.conn_params = {
            'host': 'aws-0-eu-north-1.pooler.supabase.com',
            'port': 5432,
            'dbname': 'postgres',
            'user': 'postgres.njhjquehihrdauasqfvj',
            'password': '44238',
            'sslmode': 'require'
        }
        self.current_user = None
        self.create_users_table()
    
    def init_column_widths_table(self):
        try:
            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS column_widths (
                    username TEXT,
                    column_name TEXT,
                    width INTEGER,
                    PRIMARY KEY (username, column_name)
                );
            """)
            conn.commit()
        except psycopg2.Error as e:
            print("Ошибка при создании таблицы column_widths:", e)
        finally:
            if conn:
                conn.close()
    
    
    @contextmanager
    def _get_cursor(self):
        """Контекстный менеджер для работы с БД"""
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            logging.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_users_table(self):
        """Создает таблицу пользователей"""
        try:
            with self._get_cursor() as c:
                c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE
                )''')
                
                # Проверяем наличие администратора
                c.execute("SELECT 1 FROM users WHERE username = %s", ('admin',))
                if not c.fetchone():
                    self._create_default_admin(c)
        except Exception as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
            raise
    
    def _create_default_admin(self, cursor):
        """Создает администратора по умолчанию"""
        default_user = "admin"
        default_pass = "admin123"
        pass_hash = generate_password_hash(default_pass)
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, is_admin) VALUES (%s, %s, %s, %s)",
            (default_user, pass_hash, "Администратор", True)
        )
        logging.info("Создан пользователь admin по умолчанию")
    
    def register_user(self, username, password, full_name, is_admin=False):
        """Регистрирует нового пользователя"""
        if not username or not password:
            return False, "Логин и пароль не могут быть пустыми"
            
        try:
            with self._get_cursor() as c:
                # Проверяем существование пользователя
                c.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                if c.fetchone():
                    return False, "Пользователь уже существует"
                
                # Хешируем пароль
                pass_hash = generate_password_hash(password)
                
                # Создаем пользователя
                c.execute(
                    "INSERT INTO users (username, password_hash, full_name, is_admin) VALUES (%s, %s, %s, %s)", 
                    (username, pass_hash, full_name, is_admin)
                )
                
                return True, "Пользователь успешно зарегистрирован"
        except psycopg2.Error as e:
            logging.error(f"Ошибка регистрации: {e}")
            return False, f"Ошибка регистрации: {e}"
    
    def login(self, username, password):
        """Аутентификация пользователя"""
        try:
            with self._get_cursor() as c:
                c.execute(
                    "SELECT id, username, password_hash, full_name, is_admin FROM users WHERE username = %s",
                    (username,)
                )
                user_data = c.fetchone()
                
                if not user_data:
                    return False, "Пользователь не найден"
                
                user_id, db_username, stored_hash, full_name, is_admin = user_data
                
                if check_password_hash(stored_hash, password):
                    self.current_user = {
                        "id": user_id,
                        "username": db_username,
                        "full_name": full_name,
                        "is_admin": is_admin
                    }
                    return True, "Успешный вход"
                return False, "Неверный пароль"
        except Exception as e:
            logging.error(f"Ошибка входа: {e}")
            return False, f"Ошибка при входе: {e}"
    
    def logout(self):
        """Выход из системы"""
        self.current_user = None
        logging.info("Пользователь вышел из системы")
    
    def get_current_user(self):
        """Возвращает текущего пользователя"""
        return self.current_user

class LoginWindow(tk.Toplevel):
    """Окно входа в систему"""
    def __init__(self, master, auth_manager, on_success_callback):
        super().__init__(master)
        self.auth_manager = auth_manager
        self.on_success_callback = on_success_callback
        
        self.title("Вход в систему")
        self.geometry("300x200")
        self.resizable(False, False)
        
        self.create_widgets()
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        ttk.Label(self, text="Логин:").pack(pady=(10, 0))
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(pady=5)
        
        ttk.Label(self, text="Пароль:").pack()
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Войти", 
            command=self.attempt_login
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame, 
            text="Регистрация", 
            command=self.show_register_window
        ).pack(side="left", padx=5)
    
    def attempt_login(self):
        """Попытка входа пользователя"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Ошибка", "Введите логин и пароль")
            return
        
        success, message = self.auth_manager.login(username, password)
        if success:
            messagebox.showinfo("Успех", f"Добро пожаловать, {username}!")
            self.on_success_callback()
            self.destroy()
        else:
            messagebox.showerror("Ошибка", message)
    
    def show_register_window(self):
        """Показывает окно регистрации"""
        RegisterWindow(self, self.auth_manager)

class RegisterWindow(tk.Toplevel):
    """Окно регистрации нового пользователя"""
    def __init__(self, master, auth_manager):
        super().__init__(master)
        self.auth_manager = auth_manager
        
        self.title("Регистрация")
        self.geometry("350x250")
        self.resizable(False, False)
        
        self.create_widgets()
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        ttk.Label(self, text="Логин:").pack(pady=(10, 0))
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(pady=5)
        self.app.add_context_menu(self.username_entry)  # <- добавили меню копировать/вставить

        ttk.Label(self, text="Пароль:").pack()
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(pady=5)
        self.app.add_context_menu(self.password_entry)  # <- добавили меню

        ttk.Label(self, text="ФИО:").pack()
        self.fullname_entry = ttk.Entry(self)
        self.fullname_entry.pack(pady=5)
        self.app.add_context_menu(self.fullname_entry)  # <- добавили меню

        self.is_admin_var = tk.BooleanVar()
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Зарегистрироваться", 
            command=self.attempt_register
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame, 
            text="Отмена", 
            command=self.destroy
        ).pack(side="left", padx=5)
    
    def attempt_register(self):
        """Попытка регистрации пользователя"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        full_name = self.fullname_entry.get()
        is_admin = self.is_admin_var.get()
        
        if not username or not password or not full_name:
            messagebox.showwarning("Ошибка", "Все поля обязательны для заполнения")
            return
        
        success, message = self.auth_manager.register_user(
            username, password, full_name, is_admin)
        
        if success:
            messagebox.showinfo("Успех", message)
            self.destroy()
        else:
            messagebox.showerror("Ошибка", message)

class RepairApp:
    def __init__(self, root):
        self.last_click_pos = None # Будем хранить последние координаты клика
        self.root = root
        self.root.title("Статистика ремонтов")
        self.last_selected = None  # Для хранения последнего выделенного элемента
        
        # Инициализация менеджера аутентификации
        self.auth_manager = AuthManager()
                    
        self.root.bind("<Control-f>", self.open_search_window)
        
        # Создаем UI для входа
        self.create_login_ui()
        
        # Остальная инициализация будет после успешного входа
        self.initialized = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def add_tooltips(self):
        """Добавляет всплывающие подсказки для длинного текста в Treeview."""
        self.tooltip = None  # Инициализируем атрибут
    
        def on_motion(event):
            """Обработчик движения мыши."""
            # Определяем строку и колонку
            row_id = self.tree.identify_row(event.y)
            col_id = self.tree.identify_column(event.x)
            
            # Проверяем нужные колонки
            if not row_id or not col_id:
                return
                
            col_idx = int(col_id[1:]) - 1
            if FIELDS[col_idx] not in ["Виды работ", "Взятые запчасти"]:
                return
                
            # Получаем текст
            item = self.tree.item(row_id)
            text = item["values"][col_idx] if item and "values" in item else ""
            
            # Удаляем старый тултип
            if self.tooltip:
                self.tooltip.destroy()
                
            # Создаем новый тултип
            if text:  # Только если есть текст
                self.tooltip = tk.Toplevel(self.tree)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.geometry(f"+{event.x_root+20}+{event.y_root+10}")
                ttk.Label(
                    self.tooltip, 
                    text=text, 
                    background="lightyellow", 
                    relief="solid", 
                    borderwidth=1,
                    padding=5
                ).pack()

        def on_leave(event):
            """Обработчик выхода за пределы Treeview."""
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None

        # Привязываем события
        self.tree.bind("<Motion>", on_motion)
        self.tree.bind("<Leave>", on_leave)
    
    def create_login_ui(self):
        """Создает интерфейс для входа в систему"""
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(pady=50)
        
        ttk.Label(
            self.login_frame, 
            text="Добро пожаловать в систему учета ремонтов",
            font=('Helvetica', 12)
        ).pack(pady=10)
        
        ttk.Button(
            self.login_frame,
            text="Войти в систему",
            command=self.show_login_window
        ).pack(pady=10)
    
    def show_login_window(self):
        """Показывает окно входа"""
        LoginWindow(
            self.root, 
            self.auth_manager, 
            self.on_login_success
        )
    
    def on_login_success(self):
        """Действия после успешного входа"""
        self.login_frame.destroy()
        self.initialize_app()
        
        # Получаем данные текущего пользователя
        current_user = self.auth_manager.get_current_user()
        if current_user:
            # Обновляем заголовок окна с добавлением ФИО
            self.root.title(f"Статистика ремонтов - {current_user['full_name']}")
        self.root.state('zoomed')
    
    def initialize_app(self):
        """Инициализирует основное приложение после входа"""
        if self.initialized:
            return
            
        self.create_dirs()
        self.create_db()
        
        # Сначала создаем status_var
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
        
        # Затем инициализируем Treeview и другие элементы
        self.tree = self.create_tree()
        self.score_label = ttk.Label(self.root, text="Сумма баллов по кварталам: ")
        self.score_label.pack(pady=5)
        
        self.create_buttons()
        self.create_context_menu()
        self.create_menu()  # Добавляем создание меню
        
        # Теперь можно обновить статус
        self.update_status()
        
        # Добавляем привязки клавиш для выделения
        self.tree.bind("<Shift-Button-1>", self.on_shift_click)
        self.tree.bind("<Control-Button-1>", self.on_ctrl_click)
        self.root.bind("<Control-a>", self.select_all)
        self.root.bind("<Control-c>", lambda e: self.copy_selected_rows())
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        self.load_data()
        self.add_tooltips()
        self.initialized = True
    
    def select_all(self, event):
        """Выделить все строки"""
        self.tree.selection_set(self.tree.get_children())
        return "break"  # Предотвращаем стандартную обработку
    
    def on_shift_click(self, event):
        """Обработчик для выделения диапазона строк с Shift"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        if not self.last_selected:
            self.last_selected = item
            self.tree.selection_set(item)
            return
            
        # Получаем все элементы дерева
        all_items = self.tree.get_children()
        
        # Находим индексы первой и последней выбранной строки
        try:
            start_idx = all_items.index(self.last_selected)
            end_idx = all_items.index(item)
        except ValueError:
            return
            
        # Определяем направление выделения
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        # Выделяем все строки в диапазоне
        self.tree.selection_set(all_items[start_idx:end_idx+1])

    def on_ctrl_click(self, event):
        """Обработчик для множественного выделения с Ctrl"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        current_selection = self.tree.selection()
        if item in current_selection:
            self.tree.selection_remove(item)
        else:
            self.tree.selection_add(item)
        
        self.last_selected = item
    
        
    def update_status(self):
        """Обновляет статусную строку"""
        current_user = self.auth_manager.get_current_user()
        if current_user:
            status_text = f"Пользователь: {current_user['full_name']}"
            if current_user['is_admin']:
                status_text += " (Администратор)"
            self.status_var.set(status_text)
    
    def create_menu(self):
        """Создает меню с информацией о пользователе"""
        menubar = tk.Menu(self.root)
        
        # Меню пользователя
        user_menu = tk.Menu(menubar, tearoff=0)
        current_user = self.auth_manager.get_current_user()
        
        if current_user:
            user_menu.add_command(
                label=f"Пользователь: {current_user['full_name']}",
                state="disabled"
            )
            
            if current_user["is_admin"]:
                user_menu.add_command(
                    label="Управление пользователями",
                    command=self.show_user_management
                )
            
            user_menu.add_separator()
            user_menu.add_command(
                label="Выход",
                command=self.logout
            )
        
        menubar.add_cascade(label="Аккаунт", menu=user_menu)
        self.root.config(menu=menubar)
    
    def show_user_management(self):
        """Показывает окно управления пользователями"""
        UserManagementWindow(self.root, self.auth_manager)
    
    def logout(self):
        """Выход из системы с обработкой ошибок"""
        try:
            if hasattr(self, 'auth_manager'):  # Проверяем наличие атрибута
                self.auth_manager.logout()  # Правильный вызов метода
                
                # Сбрасываем интерфейс
                self.root.title("Статистика ремонтов")
                for widget in self.root.winfo_children():
                    widget.destroy()
                
                self.initialized = False
                self.create_login_ui()
            else:
                raise AttributeError("Объект auth_manager не инициализирован")
                
        except Exception as e:
            logging.error(f"Ошибка при выходе: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Не удалось завершить сеанс: {str(e)}")    

    def create_dirs(self):
        """Создает необходимые директории, если они не существуют."""
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(ACTS_DIR, exist_ok=True)

    def create_db(self):
        """Создает базу данных и таблицу, если они не существуют."""
        conn = None  # Инициализируем переменную заранее
        try:
            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id INTEGER NOT NULL,
            serial1 TEXT,
            serial2 TEXT,
            hd_number TEXT,
            repair_type TEXT,
            work_type TEXT,
            parts TEXT,
            start_date TEXT,
            pre_tests INTEGER,
            end_date TEXT,
            post_tests INTEGER,
            quarter TEXT,
            status TEXT,
            model TEXT,
            client TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            conn.commit()
        except psycopg2.Error as e:
            logging.error(f"Ошибка при создании БД: {e}")
            messagebox.showerror("Ошибка БД", f"Не удалось создать БД: {e}")
        finally:
            if conn:
                conn.close()

    def create_tree(self):
        """Создает и настраивает treeview для отображения данных."""
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar_y = ttk.Scrollbar(frame, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(frame, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            frame,
            columns=FIELDS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            selectmode="extended"
        )
        
        # --- ДОБАВЛЯЕМ поле поиска и кнопку ---
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill="x", pady=5)

        self.search_var = tk.StringVar()

        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left", padx=(10, 5), pady=5, expand=True, fill="x")

        search_button = ttk.Button(search_frame, text="Найти", command=self.perform_search)
        search_button.pack(side="left", padx=5, pady=5)

        self.add_context_menu(self.search_entry)  # <- вставить контекстное меню

        self.root.bind("<Control-f>", self.open_search_window)  # привязка Ctrl+F
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        # Загружаем сохранённые ширины
        column_widths = self.load_column_widths()

        for field in FIELDS:
            width = column_widths.get(field, 120 if field in ["Тип ремонта", "Квартал", "Статус"] else 200)
            self.tree.heading(field, text=field)
            self.tree.column(field, width=width, anchor="center", stretch=True)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Button-3>", self.show_context_menu)

        return self.tree

    def create_context_menu(self):
        """Создает контекстное меню для дерева с функцией копирования."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        
        # Основные команды
        self.context_menu.add_command(label="Добавить", command=self.add_entry)
        self.context_menu.add_command(label="Редактировать", command=self.edit_entry)
        self.context_menu.add_command(label="Удалить", command=self.delete_entry)
        self.context_menu.add_command(label="Печать акта", command=self.generate_act_window)
        self.context_menu.add_separator()
        
        # Команды копирования
        self.context_menu.add_command(label="Копировать строку", command=self.copy_row)
        self.context_menu.add_command(label="Копировать выделенные строки", command=self.copy_selected_rows)
        self.context_menu.add_command(label="Копировать ячейку", command=self.copy_cell)
        self.context_menu.add_separator()
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отправить в WhatsApp", command=self.send_whatsapp_message)
        
        self.context_menu.add_command(label="Обновить данные", command=self.load_data)

    def show_context_menu(self, event):
        """Показывает контекстное меню и сохраняет позицию клика"""
        self.last_click_pos = (event.x, event.y)  # Сохраняем координаты
        item = self.tree.identify_row(event.y)
        
        if item:
            # Настраиваем доступность пунктов меню
            selected_count = len(self.tree.selection())
            self.context_menu.entryconfig("Копировать строку", state=tk.NORMAL if selected_count == 1 else tk.DISABLED)
            self.context_menu.entryconfig("Копировать выделенные строки", state=tk.NORMAL if selected_count > 1 else tk.DISABLED)
            self.context_menu.entryconfig("Копировать ячейку", state=tk.NORMAL)
            
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_row(self):
        """Копирует всю строку в буфер обмена."""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        values = item['values']
        
        # Форматируем строку для копирования
        headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        row_data = "\t".join(f"{header}: {value}" for header, value in zip(headers, values))
        
        self.root.clipboard_clear()
        self.root.clipboard_append(row_data)
        self.status_var.set("Строка скопирована в буфер обмена")
    
    def copy_selected_rows(self):
        """Копирует все выделенные строки в буфер обмена."""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        try:
            # Получаем заголовки колонок
            headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
            
            # Ограничиваем количество строк для копирования (например, 1000)
            max_rows_to_copy = 1000
            if len(selected_items) > max_rows_to_copy:
                if not messagebox.askyesno(
                    "Подтверждение",
                    f"Выделено {len(selected_items)} строк. Копировать первые {max_rows_to_copy}?"
                ):
                    return
                selected_items = selected_items[:max_rows_to_copy]
            
            # Собираем данные с прогрессом для больших объемов
            rows_data = []
            progress_step = max(1, len(selected_items) // 10)  # Обновляем статус каждые 10%
            
            for i, item_id in enumerate(selected_items, 1):
                item = self.tree.item(item_id)
                values = item['values']
                row_str = "\t".join(str(value) for value in values)
                rows_data.append(row_str)
                
                if i % progress_step == 0:
                    self.status_var.set(f"Подготовка данных... {i/len(selected_items)*100:.0f}%")
                    self.root.update()
            
            # Форматируем с заголовками и разделителями
            result = "\n".join(["\t".join(headers)] + rows_data)
            
            # Копируем в буфер обмена
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            
            self.status_var.set(f"Скопировано {len(selected_items)} строк")
            
        except Exception as e:
            self.status_var.set("Ошибка при копировании")
            messagebox.showerror("Ошибка", f"Не удалось скопировать данные: {str(e)}")

    def copy_cell(self):
        """Копирует содержимое конкретной ячейки под курсором"""
        if not self.last_click_pos:
            return
            
        x, y = self.last_click_pos
        
        # Идентифицируем строку и колонку напрямую без пересчёта координат
        item = self.tree.identify_row(y)
        column = self.tree.identify_column(x)
        
        if not item or not column:
            return
            
        # Получаем данные ячейки
        col_index = int(column[1:]) - 1
        item_data = self.tree.item(item)
        values = item_data['values']
        
        if col_index < len(values):
            cell_value = str(values[col_index])
            
            # Копируем в буфер обмена
            self.root.clipboard_clear()
            self.root.clipboard_append(cell_value)
            
            # Обновляем статус
            header = self.tree.heading(column)['text']
            self.status_var.set(f"Скопировано из '{header}': {cell_value}")
            
            # Временное выделение ячейки для визуальной обратной связи
            self.highlight_cell(item, column)
    
    def highlight_cell(self, item, column):
        """Временно выделяет ячейку для визуальной обратной связи"""
        # Сохраняем текущее выделение
        prev_selection = self.tree.selection()
        prev_focus = self.tree.focus()
        
        # Временно выделяем ячейку
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        
        # Через 500 мс восстанавливаем предыдущее выделение
        self.root.after(500, lambda: [
            self.tree.selection_set(prev_selection),
            self.tree.focus(prev_focus)
        ])
    
    def create_buttons(self):
        """Создает панель кнопок управления."""
        frame = ttk.Frame(self.root)
        frame.pack(pady=5)

        buttons = [
            ("Добавить", self.add_entry),
            ("Редактировать", self.edit_entry),
            ("Удалить", self.delete_entry),
            ("Импорт из Excel", self.import_from_excel),
            ("Экспорт в Excel", self.export_to_excel),
            ("Печать акта", self.generate_act_window),
            ("Создать резервную копию", self.create_backup),
            ("Обновить", self.load_data),
            ("Отправить в WhatsApp", self.send_whatsapp_message)  # <- Новая кнопка
        ]

        for text, command in buttons:
            ttk.Button(frame, text=text, command=command).pack(side="left", padx=5)

    def load_data(self):
        """Загружает данные из БД и отображает их в treeview с использованием SQLAlchemy."""
        engine = None
        try:
            current_user = self.auth_manager.get_current_user()
            if not current_user:
                logging.warning("Попытка загрузки данных без авторизации")
                return

            from sqlalchemy import create_engine
            from sqlalchemy.engine import URL

            connection_url = URL.create(
                drivername="postgresql+psycopg2",
                username="postgres.njhjquehihrdauasqfvj",
                password="44238",
                host="aws-0-eu-north-1.pooler.supabase.com",
                port=5432,
                database="postgres"
            )

            engine = create_engine(connection_url)

            if current_user['is_admin']:
                # Админ видит все записи и фамилии пользователей
                query = """
                    SELECT r.id, u.full_name, r.serial1, r.serial2, r.hd_number, r.repair_type,
                           r.work_type, r.parts, r.start_date, r.pre_tests, r.end_date,
                           r.post_tests, r.quarter, r.status, r.model, r.client
                    FROM repairs r
                    JOIN users u ON r.user_id = u.id
                """
                df = pd.read_sql(query, engine)
            else:
                # Обычный пользователь видит только свои записи
                query = """
                    SELECT id, serial1, serial2, hd_number, repair_type, 
                           work_type, parts, start_date, pre_tests, 
                           end_date, post_tests, quarter, status, model, client 
                    FROM repairs
                    WHERE user_id = %s
                """
                df = pd.read_sql(query, engine, params=(current_user['id'],))

            # Заменяем NaN на пустые строки
            df = df.fillna('')

            # Сохраняем данные и отображаем
            self.data = df
            self.display_data(df)

            logging.info("Данные успешно загружены из БД")

        except Exception as e:
            logging.error(f"Ошибка при загрузке данных: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {str(e)}")
        finally:
            if engine:
                engine.dispose()
                
        

    def display_data(self, df):
        """Отображает данные в Treeview, заменяя NaN/None на пустые строки"""
        self.tree.delete(*self.tree.get_children())

        # Проверяем, админ ли пользователь
        current_user = self.auth_manager.get_current_user()
        is_admin = current_user and current_user.get('is_admin', False)

        # Обновляем заголовки столбцов
        if is_admin:
            columns = ("full_name", "serial1", "serial2", "hd_number", "repair_type", "work_type",
                       "parts", "start_date", "pre_tests", "end_date", "post_tests",
                       "quarter", "status", "model", "client")
            headings = ("ФИО", "Серийный 1", "Серийный 2", "Номер HD", "Тип ремонта", "Виды работ",
                        "Взятые запчасти", "Дата начала", "Кол-во до", "Дата готовности", "Кол-во после",
                        "Квартал", "Статус", "Модель", "Клиент")
        else:
            columns = ("serial1", "serial2", "hd_number", "repair_type", "work_type",
                       "parts", "start_date", "pre_tests", "end_date", "post_tests",
                       "quarter", "status", "model", "client")
            headings = ("Серийный 1", "Серийный 2", "Номер HD", "Тип ремонта", "Виды работ",
                        "Взятые запчасти", "Дата начала", "Кол-во до", "Дата готовности", "Кол-во после",
                        "Квартал", "Статус", "Модель", "Клиент")

        self.tree["columns"] = columns
        for col, heading in zip(columns, headings):
            self.tree.heading(col, text=heading)
            
        self.apply_column_widths()    

        # Заменяем все NaN/None на пустые строки
        df = df.fillna('')

        for _, row in df.iterrows():
            record_id = str(row.get('id', ''))
            if not record_id:
                continue

            if is_admin:
                values = [
                    str(row.get("full_name", "")),
                    str(row.get("serial1", "")),
                    str(row.get("serial2", "")),
                    str(row.get("hd_number", "")),
                    str(row.get("repair_type", "")),
                    str(row.get("work_type", "")),
                    str(row.get("parts", "")),
                    str(row.get("start_date", "")),
                    str(row.get("pre_tests", "")),
                    str(row.get("end_date", "")),
                    str(row.get("post_tests", "")),
                    str(row.get("quarter", "")),
                    str(row.get("status", "")),
                    str(row.get("model", "")),
                    str(row.get("client", ""))
                ]
            else:
                values = [
                    str(row.get("serial1", "")),
                    str(row.get("serial2", "")),
                    str(row.get("hd_number", "")),
                    str(row.get("repair_type", "")),
                    str(row.get("work_type", "")),
                    str(row.get("parts", "")),
                    str(row.get("start_date", "")),
                    str(row.get("pre_tests", "")),
                    str(row.get("end_date", "")),
                    str(row.get("post_tests", "")),
                    str(row.get("quarter", "")),
                    str(row.get("status", "")),
                    str(row.get("model", "")),
                    str(row.get("client", ""))
                ]

            tag = "готов" if str(row.get("status", "")).lower() == "готов" else "ожидание"
            self.tree.insert("", "end", iid=record_id, values=values, tags=(tag,))

        # Настраиваем цвета тегов
        self.tree.tag_configure("готов", background="lightgreen")
        self.tree.tag_configure("ожидание", background="lightyellow")
        self.update_score(df)

    def update_score(self, df):
        """Обновляет информацию о баллах по кварталам."""
        score_by_quarter = {}
        for _, row in df.iterrows():
            if row["status"] == "Готов" and row["repair_type"] in REPAIR_TYPES:
                q = str(row["quarter"])
                score_by_quarter[q] = score_by_quarter.get(q, 0) + REPAIR_TYPES[row["repair_type"]]

        display = "Сумма баллов по кварталам: "
        if score_by_quarter:
            display += ", ".join([f"Кв. {k}: {v:.1f}" for k, v in sorted(score_by_quarter.items())])
        else:
            display += "нет данных"
        
        self.score_label.config(text=display)

    def add_entry(self):
        """Открывает окно для добавления новой записи."""
        EntryWindow(self.root, self, mode="add", auth_manager=self.auth_manager)

    def edit_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запись для редактирования")
            return
        
        try:
            record_id = int(selected[0])
            item = self.tree.item(selected[0])["values"]
            EntryWindow(
                self.root, 
                self, 
                mode="edit", 
                values=item, 
                record_id=record_id,
                auth_manager=self.auth_manager  # <- Добавьте auth_manager
            )
        except Exception as e:
            logging.error(f"Ошибка при редактировании записи: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть запись для редактирования: {e}")

    def delete_entry(self):
        """Удаляет выбранную запись."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запись для удаления")
            return

        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return

        confirm = messagebox.askyesno(
            "Удаление", 
            "Вы уверены, что хотите удалить выбранную запись?",
            icon="warning"
        )
        if not confirm:
            return

        conn = None
        try:
            record_id = int(selected[0])
            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )
            c = conn.cursor()
            
            # Проверяем, что запись принадлежит пользователю
            c.execute("SELECT user_id FROM repairs WHERE id = %s", (record_id,))
            result = c.fetchone()
            
            if not result or result[0] != current_user['id']:
                messagebox.showerror("Ошибка", "Вы не можете удалить эту запись")
                return
                
            c.execute("DELETE FROM repairs WHERE id = %s", (record_id,))
            conn.commit()
            messagebox.showinfo("Успех", "Запись успешно удалена")
            self.load_data()
        except Exception as e:
            logging.error(f"Ошибка при удалении записи: {e}")
            messagebox.showerror("Ошибка", f"Не удалось удалить запись: {e}")
        finally:
            if conn:
                conn.close()

    def perform_search(self):
        """Поиск по введённому тексту"""
        query = self.search_var.get().lower()
        self.search_in_tree(query)

    def open_search_window(self, event=None):
        """Фокусирует поле поиска"""
        self.search_entry.focus_set()                           

    def export_to_excel(self):
        """Экспортирует данные в Excel файл с фамилией пользователя для администратора."""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")]
        )
        if not file_path:
            return

        engine = None
        try:
            from sqlalchemy import create_engine
            db_url = (
                "postgresql+psycopg2://"
                "postgres.njhjquehihrdauasqfvj:44238@"
                "aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
            )
            engine = create_engine(db_url)
            
            # Определяем запрос в зависимости от роли
            if current_user.get('is_admin', False):
                query = """
                SELECT 
                    r.*, 
                    split_part(u.full_name, ' ', 1) AS user_surname  -- Извлекаем фамилию (первое слово)
                FROM repairs r
                LEFT JOIN users u ON r.user_id = u.id
                """
                params = ()
            else:
                query = "SELECT * FROM repairs WHERE user_id = %s"
                params = (current_user['id'],)
            
            df = pd.read_sql(query, engine, params=params)
            
            # Обрабатываем колонки
            for column in ['serial1', 'serial2', 'hd_number']:
                if column in df.columns:
                    df[column] = df[column].astype(str)
            
            # Переименовываем колонку для красоты
            if 'user_surname' in df.columns:
                df = df.rename(columns={'user_surname': 'Фамилия'})
            
            # Сохраняем в Excel
            df.to_excel(file_path, index=False, engine='openpyxl')
            messagebox.showinfo("Успешно", f"Данные успешно экспортированы в:\n{file_path}")
            logging.info(f"Данные экспортированы в {file_path}")
            
        except Exception as e:
            logging.error(f"Ошибка при экспорте в Excel: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {e}")
        finally:
            if engine:
                engine.dispose()
    def import_from_excel(self):
        """Импортирует данные из Excel файла с полной обработкой ошибок."""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            messagebox.showerror("Ошибка", "Вы не авторизованы.")
            return

        file_path = filedialog.askopenfilename(
            filetypes=[("Excel файлы", "*.xlsx *.xls"), ("Все файлы", "*.*")]
        )
        if not file_path:
            return

        conn = None
        try:
            # Чтение файла Excel
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                df = df.replace([np.nan, pd.NaT, 'NaT', 'nan', '', 'None', 'NULL'], '')
            except Exception as e:
                logging.error(f"Ошибка при чтении Excel: {e}")
                messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
                return

            # Проверка необходимых столбцов
            REQUIRED_COLUMNS = [
                'Серийный номер', 'Серийный номер 2', 'Номер HD', 'Тип ремонта', 'Виды работ',
                'Взятые запчасти', 'Дата взятия', 'Кол-во исследований', 'Дата готовности',
                'Кол-во после ремонта', 'Квартал', 'Статус', 'Модель'
            ]
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                messagebox.showerror(
                    "Ошибка",
                    f"В файле отсутствуют необходимые столбцы: {', '.join(missing_columns)}"
                )
                return

            # Подготовка данных
            df['Дата взятия'] = pd.to_datetime(df['Дата взятия'], errors='coerce', dayfirst=True)
            df['Дата готовности'] = pd.to_datetime(df['Дата готовности'], errors='coerce', dayfirst=True)

            df['Дата взятия'] = df['Дата взятия'].apply(lambda x: x.strftime('%d.%m.%Y') if not pd.isna(x) else None)
            df['Дата готовности'] = df['Дата готовности'].apply(lambda x: x.strftime('%d.%m.%Y') if not pd.isna(x) else None)

            df['Кол-во исследований'] = pd.to_numeric(df['Кол-во исследований'], errors='coerce').fillna(0)
            df['Кол-во после ремонта'] = pd.to_numeric(df['Кол-во после ремонта'], errors='coerce').fillna(0)

            # Формирование записей
            records = []
            for idx, row in df.iterrows():
                try:
                    record = [
                        current_user['id'],
                        str(row.get('Серийный номер', '')).strip(),
                        str(row.get('Серийный номер 2', '')).strip(),
                        str(row.get('Номер HD', '')).strip(),
                        str(row.get('Тип ремонта', '')).strip(),
                        str(row.get('Виды работ', '')).strip(),
                        str(row.get('Взятые запчасти', '')).strip(),
                        row.get('Дата взятия', None),
                        int(float(row.get('Кол-во исследований', 0)) if row.get('Кол-во исследований') not in [None, ''] else 0),
                        row.get('Дата готовности', None),
                        int(float(row.get('Кол-во после ремонта', 0)) if row.get('Кол-во после ремонта') not in [None, ''] else 0),
                        str(row.get('Квартал', '')).strip(),
                        str(row.get('Статус', '')).strip(),
                        str(row.get('Модель', '')).strip()
                    ]
                    records.append(record)
                except Exception as row_err:
                    logging.warning(f"Ошибка обработки строки {idx + 1}: {row_err}")
                    continue

            if not records:
                messagebox.showwarning("Предупреждение", "Нет данных для импорта.")
                return

            # Подключение и вставка в базу данных
            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )

            with conn.cursor() as cur:
                success_count = 0
                for record in records:
                    try:
                        cur.execute('''INSERT INTO repairs (
                            user_id, serial1, serial2, hd_number, repair_type, work_type, parts,
                            start_date, pre_tests, end_date, post_tests, quarter, status, model, client
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', record)
                        success_count += 1
                    except psycopg2.Error as e:
                        logging.warning(f"Ошибка вставки записи {record}: {str(e)}")
                        continue

                conn.commit()

            if success_count < len(records):
                messagebox.showwarning(
                    "Частичный успех",
                    f"Импортировано {success_count} из {len(records)} записей.\n"
                    f"{len(records) - success_count} не удалось вставить."
                )
            else:
                messagebox.showinfo("Успех", f"Успешно импортировано {success_count} записей.")

            self.load_data()

        except Exception as e:
            logging.error(f"Ошибка при импорте из Excel: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка при импорте: {e}")
        finally:
            if conn:
                conn.close()
    def _parse_date(self, date_value):
        """Преобразует дату из строки в datetime.date."""
        if pd.isna(date_value) or date_value is None:
            return None
        if isinstance(date_value, datetime):
            return date_value.date()
        try:
            return datetime.strptime(str(date_value), "%d.%m.%Y").date()
        except ValueError:
            return None

    def generate_act_window(self):
        """Генерация акта с учетом различий между администратором и обычным пользователем"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запись для печати акта")
            return

        try:
            # Получаем данные и информацию о пользователе
            item = self.tree.item(selected[0])["values"]
            current_user = self.auth_manager.get_current_user()
            is_admin = current_user.get('is_admin', False)
            
            employee_signature = current_user["full_name"]
            
            # Определяем индексы полей в зависимости от роли
            if is_admin:
                # Индексы для администратора (примерные, нужно уточнить)
                field_indexes = {
                    'serial': 1,    # Серийный номер
                    'date': 9,      # Дата готовности
                    'equipment': 13, # Тип оборудования
                    'parts': 6,      # Замененные детали
                    'technician': 0
                }
            else:
                # Индексы для обычного пользователя
                field_indexes = {
                    'serial': 0,
                    'date': 8,
                    'equipment': 12,
                    'parts': 5,
                    'technician': employee_signature
                }

            # Проверка обязательных полей
            if not item[field_indexes['serial']]:
                messagebox.showerror("Ошибка", "Не указан серийный номер оборудования")
                return

            if not item[field_indexes['date']]:
                messagebox.showerror("Ошибка", "Не указана дата готовности ремонта")
                return

            # Универсальная обработка даты
            date_value = item[field_indexes['date']]
            end_date = None
            
            try:
                # Пробуем разные форматы даты
                if isinstance(date_value, str):
                    # Формат "ДД.ММ.ГГГГ"
                    end_date = datetime.strptime(date_value, "%d.%m.%Y")
                elif isinstance(date_value, (int, float)):
                    if date_value > 1000000000:  # Предположим, это timestamp
                        end_date = datetime.fromtimestamp(date_value)
                    else:  # Формат ДДММГГГГ
                        date_str = f"{date_value:08d}"
                        end_date = datetime.strptime(date_str, "%d%m%Y")
            except (ValueError, TypeError) as e:
                logging.error(f"Ошибка преобразования даты: {date_value} ({type(date_value)}): {e}")
                messagebox.showerror("Ошибка", 
                    f"Неверный формат даты: {date_value}\n"
                    f"Ожидается: ДД.ММ.ГГГГ, ДДММГГГГ или timestamp")
                return


            # Запрос дополнительных данных
            employee_id = simpledialog.askstring("Акт", "Введите табельный номер исполнителя:", parent=self.root)
            if not employee_id:
                return

            act_number = simpledialog.askstring("Акт", "Введите порядковый номер акта:", parent=self.root)
            if not act_number:
                return

            customer = simpledialog.askstring("Акт", "Введите заказчика:", parent=self.root)
            if not customer:
                return
           

            # Формирование данных для акта
            act_data = {
                'act_number': f"{end_date.strftime('%Y%m%d')}-{employee_id}-{act_number}",
                'act_date_formatted': (
                    f"«__{end_date.day:02d}__»_"
                    f"_{end_date.month:02d}_"
                    f"__{end_date.year}_г."
                ),
                'customer': customer,
                'equipment_type': item[field_indexes['equipment']],
                'serial_number': item[field_indexes['serial']],
                'replaced_parts': item[field_indexes['parts']] or "не производилась",
                'current_date': datetime.now().strftime("%d.%m.%Y"),
                'employee_signature': current_user["full_name"] if not is_admin else item[field_indexes['technician']]
            }

            # Генерация акта
            self.generate_custom_act(act_data)

        except Exception as e:
            logging.error(f"Ошибка при подготовке акта: {e}", exc_info=True)
            messagebox.showerror("Ошибка", f"Ошибка при формировании акта:\n{str(e)}")


    def generate_custom_act(self, data):
        """Генерация акта по шаблону"""
        try:
            if not os.path.exists(TEMPLATE_PATH):
                raise FileNotFoundError(f"Файл шаблона {TEMPLATE_PATH} не найден")

            doc = Document(TEMPLATE_PATH)

            replacements = {
                "{ACT_NUMBER}": data['act_number'],
                "{ACT_DATE_FORMATTED}": data['act_date_formatted'],
                "{CUSTOMER}": data['customer'],
                "{EQUIPMENT_TYPE}": data['equipment_type'],
                "{SERIAL_NUMBER}": data['serial_number'],
                "{REPLACED_PARTS}": data['replaced_parts'],
                "{CURRENT_DATE}": data['current_date'],
                "{EMPLOYEE_SIGNATURE}": data['employee_signature']
            }

            for paragraph in doc.paragraphs:
                for key, value in replacements.items():
                    if key in paragraph.text:
                        paragraph.text = paragraph.text.replace(key, str(value))

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for key, value in replacements.items():
                            if key in cell.text:
                                cell.text = cell.text.replace(key, str(value))

            os.makedirs(ACTS_DIR, exist_ok=True)
            filename = f"Акт_{data['serial_number']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            filepath = os.path.join(ACTS_DIR, filename)
            doc.save(filepath)

            messagebox.showinfo("Акт создан", f"Акт успешно сохранён:\n{filepath}")
            os.startfile(filepath)  # Только Windows

        except Exception as e:
            logging.error(f"Ошибка генерации акта: {e}", exc_info=True)
            messagebox.showerror("Ошибка", f"Не удалось сгенерировать акт:\n{e}")


    def create_backup(self):
        """Создает .sql резервную копию базы данных в один файл (перезаписывается каждый раз)."""
        conn = None
        try:
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, "latest_backup.sql")

            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )
            cursor = conn.cursor()

            # Получаем все данные
            cursor.execute("SELECT * FROM repairs")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            # Строим SQL дамп
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write("BEGIN;\n")
                f.write("DELETE FROM repairs;\n")  # очищаем при восстановлении

                for row in rows:
                    values = []
                    for val in row:
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                        else:
                            values.append(str(val))
                    sql = f"INSERT INTO repairs ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                    f.write(sql)

                f.write("COMMIT;\n")

            messagebox.showinfo("Резервная копия", f"Файл обновлён:\n{backup_path}")

        except Exception as e:
            logging.error(f"Ошибка при создании .sql резервной копии: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать .sql резервную копию: {e}")
        finally:
            if conn:
                conn.close()
 
 
    def save_column_widths(self):
        if not hasattr(self, 'tree') or not self.tree:
            return

        user = self.auth_manager.get_current_user()
        if not user:
            return

        username = user.get("username")
        is_admin = bool(user.get("is_admin", False))  # <- Явное приведение к bool

        try:
            conn = psycopg2.connect(**self.auth_manager.conn_params)
            with conn:
                with conn.cursor() as c:
                    c.execute("DELETE FROM column_widths WHERE username = %s AND is_admin = %s", (username, is_admin))

                    for col in self.tree["columns"]:
                        try:
                            width = self.tree.column(col)['width']
                            c.execute("""
                                INSERT INTO column_widths (username, column_name, width, is_admin)
                                VALUES (%s, %s, %s, %s)
                            """, (username, col, width, is_admin))
                        except Exception as e:
                            print(f"Ошибка сохранения ширины {col}: {e}")
            print(f"✅ Ширины столбцов сохранены для {username}, админ={is_admin}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении ширин: {e}")
        finally:
            if conn:
                conn.close()

    def load_column_widths(self):
        user = self.auth_manager.get_current_user()
        if not user:
            return {}

        username = user.get("username")
        is_admin = bool(user.get("is_admin", False))
        widths = {}

        try:
            conn = psycopg2.connect(**self.auth_manager.conn_params)
            with conn:
                with conn.cursor() as c:
                    c.execute("""
                        SELECT column_name, width FROM column_widths
                        WHERE username = %s AND is_admin = %s
                    """, (username, is_admin))
                    widths = {row[0]: row[1] for row in c.fetchall()}
            print(f"✅ Загружены ширины для {username} (админ={is_admin}):", widths)
        except Exception as e:
            print(f"❌ Ошибка загрузки ширин: {e}")
        finally:
            if conn:
                conn.close()

        return widths

    def apply_column_widths(self):
        """Применяет сохраненные ширины столбцов"""
        if not hasattr(self, 'tree') or not self.tree:
            return

        widths = self.load_column_widths()
        columns = self.tree["columns"]
        
        for col in columns:
            if col in widths:
                try:
                    self.tree.column(col, width=widths[col])
                except Exception as e:
                    print(f"Ошибка установки ширины {col}: {e}")

    def on_close(self):
        try:
            if getattr(self, 'initialized', False):
                self.save_column_widths()

            try:
                self.create_backup()
            except Exception as e:
                logging.error(f"Ошибка при создании резервной копии при закрытии: {e}")
            
            self.root.destroy()
        except Exception as e:
            print(f"Ошибка при закрытии окна: {e}")

    def add_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_from_widget(widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_to_widget(widget))
        menu.add_command(label="Вырезать", command=lambda: self.cut_from_widget(widget))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Control-c>", lambda event: self.copy_from_widget(widget))
        widget.bind("<Control-C>", lambda event: self.copy_from_widget(widget))
        widget.bind("<Control-v>", lambda event: self.paste_to_widget(widget))
        widget.bind("<Control-V>", lambda event: self.paste_to_widget(widget))
        widget.bind("<Control-x>", lambda event: self.cut_from_widget(widget))
        widget.bind("<Control-X>", lambda event: self.cut_from_widget(widget))

    def copy_from_widget(self, widget):
        try:
            widget.event_generate('<<Copy>>')
        except Exception:
            pass

    def paste_to_widget(self, widget):
        try:
            widget.event_generate('<<Paste>>')
        except Exception:
            pass

    def cut_from_widget(self, widget):
        try:
            widget.event_generate('<<Cut>>')
        except Exception:
            pass

    def open_search_window(self, event=None):
        """Открывает окно поиска"""
        search_win = tk.Toplevel(self.root)
        search_win.title("Поиск")
        search_win.geometry("300x80")
        search_win.resizable(False, False)
        search_win.transient(self.root)

        tk.Label(search_win, text="Что найти:").pack(pady=5)
        search_entry = tk.Entry(search_win)
        search_entry.pack(padx=10, pady=5, fill="x")
        search_entry.focus_set()

        def do_search():
            query = search_entry.get().lower()
            self.search_in_tree(query)

        tk.Button(search_win, text="Искать", command=do_search).pack(pady=1)

        search_entry.bind("<Return>", lambda event: do_search())

    def search_in_tree(self, query):
        """Ищет и выделяет элементы, содержащие запрос"""
        for item in self.tree.get_children():
            self.tree.selection_remove(item)

        found = False
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            for value in values:
                if query in str(value).lower():
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    found = True
                    break  # Останавливаемся на первом найденном

        if not found:
            messagebox.showinfo("Поиск", "Ничего не найдено.")


    def send_whatsapp_message(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите строку для отправки сообщения")
            return

        item = self.tree.item(selected[0])["values"]
        if not item:
            return

        # Получаем нужные поля
        serial_number = item[0]  # Серийный номер
        status = item[11]        # Статус (последний столбец)
        full_name = self.auth_manager.get_current_user().get('full_name', 'неизвестный пользователь')
        ready_date = item[9]    # Кол-во исследований

        # Создаем сообщение
        message = (
            f"{serial_number} {status} {full_name} {ready_date}"
        )
        
        # Кодируем и открываем WhatsApp
        encoded_message = urllib.parse.quote(message)

        # Замените на ссылку вашей группы (получается из экспорта ссылки приглашения)
        group_link = "https://web.whatsapp.com/send?phone=&text=" + encoded_message

        webbrowser.open(group_link)


class UserManagementWindow(tk.Toplevel):
    """Окно управления пользователями (только для администраторов)"""
    def __init__(self, master, auth_manager):
        super().__init__(master)
        self.auth_manager = auth_manager
        
        self.title("Управление пользователями")
        self.geometry("600x400")
        
        self.create_widgets()
        self.load_users()
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        # Treeview для отображения пользователей
        self.tree = ttk.Treeview(self, columns=("username", "full_name", "is_admin"), show="headings")
        self.tree.heading("username", text="Логин")
        self.tree.heading("full_name", text="ФИО")
        self.tree.heading("is_admin", text="Администратор")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text="Добавить пользователя",
            command=self.add_user
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="Удалить пользователя",
            command=self.delete_user
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="Обновить список",
            command=self.load_users
        ).pack(side="left", padx=5)
    
    def load_users(self):
        """Загружает список пользователей"""
        try:
            conn = psycopg2.connect(
            host="aws-0-eu-north-1.pooler.supabase.com",
            port="5432",
            dbname="postgres",
            user="postgres.njhjquehihrdauasqfvj",
            password="44238"
            )
            c = conn.cursor()
            
            c.execute("SELECT username, full_name, is_admin FROM users")
            users = c.fetchall()
            
            self.tree.delete(*self.tree.get_children())
            for user in users:
                self.tree.insert("", "end", values=user)
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить пользователей: {e}")
        finally:
            if conn:
                conn.close()
    
    def add_user(self):
        """Добавляет нового пользователя"""
        RegisterWindow(self, self.auth_manager)
    
    def delete_user(self):
        """Удаляет выбранного пользователя"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите пользователя для удаления")
            return
        
        username = self.tree.item(selected[0])["values"][0]
        current_user = self.auth_manager.get_current_user()
        
        if username == current_user["username"]:
            messagebox.showerror("Ошибка", "Нельзя удалить самого себя")
            return
        
        confirm = messagebox.askyesno(
            "Подтверждение", 
            f"Вы уверены, что хотите удалить пользователя {username}?",
            icon="warning"
        )
        
        if not confirm:
            return
        
        try:
            conn = psycopg2.connect(
            host="aws-0-eu-north-1.pooler.supabase.com",
            port="5432",
            dbname="postgres",
            user="postgres.njhjquehihrdauasqfvj",
            password="44238"
            )
            c = conn.cursor()
            username = str(self.tree.item(selected[0])["values"][0])
            c.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            
            messagebox.showinfo("Успех", "Пользователь успешно удален")
            self.load_users()
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить пользователя: {e}")
        finally:
            if conn:
                conn.close()


class EntryWindow(tk.Toplevel):
    def __init__(self, master, app, mode="add", values=None, record_id=None, auth_manager=None):
        super().__init__(master)
        self.app = app
        self.mode = mode
        self.record_id = record_id
        self.auth_manager = auth_manager
        self.title("Добавление записи" if mode == "add" else "Редактирование записи")
        self.resizable(False, False)

        self.entries = {}
        self.create_widgets(values)

        ttk.Button(
            self,
            text="Сохранить",
            command=self.validate_and_save
        ).grid(row=len(FIELDS), columnspan=2, pady=10)

    def create_widgets(self, values):
        """Создает элементы формы."""
        for idx, field in enumerate(FIELDS):
            ttk.Label(self, text=field).grid(row=idx, column=0, padx=5, pady=3, sticky="w")

            if field == "Тип ремонта":
                cb = ttk.Combobox(self, values=list(REPAIR_TYPES.keys()), state="readonly")
                cb.grid(row=idx, column=1, padx=5, pady=3)
                self.entries[field] = cb
                cb.set(values[idx] if values and values[idx] else "C")

            elif field == "Статус":
                cb = ttk.Combobox(self, values=["Готов", "В работе"], state="readonly")
                cb.grid(row=idx, column=1, padx=5, pady=3)
                self.entries[field] = cb
                cb.set(values[idx] if values and values[idx] else "В работе")

            elif field == "Клиент":
                cb = ttk.Combobox(self, values=["loaner", "demo", "client"], state="readonly")
                cb.grid(row=idx, column=1, padx=5, pady=3)
                self.entries[field] = cb
                cb.set(values[idx] if values and values[idx] else "client")

            elif "Дата" in field:
                cal = DateEntry(self, date_pattern="dd.mm.yyyy")
                cal.grid(row=idx, column=1, padx=5, pady=3)
                self.entries[field] = cal
                if values and values[idx]:
                    try:
                        dt = datetime.strptime(values[idx], "%d.%m.%Y")
                        cal.set_date(dt)
                    except ValueError:
                        pass

            elif field in ["Виды работ", "Взятые запчасти"]:
                frame = ttk.Frame(self)
                frame.grid(row=idx, column=1, padx=5, pady=3, sticky="nsew")

                text = tk.Text(frame, wrap="word", height=4, width=30)
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
                text.configure(yscrollcommand=scrollbar.set)

                text.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                self.entries[field] = text
                if values and values[idx]:
                    text.insert("1.0", values[idx])

            else:
                entry = ttk.Entry(self)
                entry.grid(row=idx, column=1, padx=5, pady=3)
                self.entries[field] = entry
                if values and values[idx]:
                    entry.insert(0, values[idx])

    def validate_and_save(self):
        """Проверяет данные и сохраняет запись."""
        try:
            values = []
            for field in FIELDS:
                widget = self.entries[field]

                if field in ["Взятые запчасти", "Виды работ"]:
                    value = widget.get("1.0", "end-1c")
                else:
                    value = widget.get()

                if field == "Серийный номер" and not value:
                    messagebox.showerror("Ошибка", "Поле 'Серийный номер' обязательно для заполнения")
                    return

                if "Дата" in field and value:
                    try:
                        value = datetime.strptime(value, "%d.%m.%Y").strftime("%d.%m.%Y")
                    except ValueError:
                        messagebox.showerror("Ошибка", f"Неверный формат даты в поле '{field}'. Используйте ДД.ММ.ГГГГ")
                        return

                values.append(value if value else None)

            self.save_to_db(values)
        except Exception as e:
            logging.error(f"Ошибка при сохранении записи: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить запись: {e}")

    def save_to_db(self, values):
        """Сохраняет данные в базу данных."""
        conn = None
        try:
            current_user = self.auth_manager.get_current_user()
            if not current_user:
                return

            conn = psycopg2.connect(
                host="aws-0-eu-north-1.pooler.supabase.com",
                port="5432",
                dbname="postgres",
                user="postgres.njhjquehihrdauasqfvj",
                password="44238"
            )
            c = conn.cursor()

            if self.mode == "add":
                values_with_user = [current_user['id']] + values
                c.execute('''INSERT INTO repairs (
                    user_id, serial1, serial2, hd_number, repair_type, work_type, parts,
                    start_date, pre_tests, end_date, post_tests, quarter, status, model, client
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', values_with_user)
            else:
                c.execute("SELECT user_id FROM repairs WHERE id = %s", (self.record_id,))
                result = c.fetchone()

                if not result or result[0] != current_user['id']:
                    messagebox.showerror("Ошибка", "Вы не можете редактировать эту запись")
                    return

                values.append(self.record_id)
                c.execute('''UPDATE repairs SET
                    serial1 = %s, serial2 = %s, hd_number = %s, repair_type = %s, work_type = %s, parts = %s,
                    start_date = %s, pre_tests = %s, end_date = %s, post_tests = %s, quarter = %s, status = %s, model = %s, client = %s
                    WHERE id = %s''', values)

            conn.commit()
            self.app.load_data()
            self.destroy()
            messagebox.showinfo("Успех", "Запись успешно сохранена")
        except psycopg2.Error as e:
            logging.error(f"Ошибка БД при сохранении: {e}")
            messagebox.showerror("Ошибка БД", f"Не удалось сохранить данные: {e}")
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = RepairApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Критическая ошибка в приложении: {e}", exc_info=True)
        messagebox.showerror(
            "Критическая ошибка", 
            f"Произошла критическая ошибка:\n{str(e)}\n\nПодробности в лог-файле."
        )