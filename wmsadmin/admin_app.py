import customtkinter as ctk
import firebase_admin
from firebase_admin import credentials, firestore, messaging
import threading
import time
from datetime import datetime


if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Критическая ошибка Firebase: {e}")

db = firestore.client()

class Admin67Post(ctk.CTk):
    def __init__(self):
        super().__init__()

    
        self.title("67Post Support System v2.0")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        
        self.selected_user = None
        self.known_users = [] 


        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)


        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="67POST ADMIN", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.pack(pady=30)

        self.status_indicator = ctk.CTkLabel(self.sidebar, text="● База данных подключена", text_color="#4CAF50")
        self.status_indicator.pack(pady=(0, 20))


        self.user_list_frame = ctk.CTkScrollableFrame(self.sidebar, label_text="Активные обращения")
        self.user_list_frame.pack(expand=True, fill="both", padx=15, pady=15)


        self.chat_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.chat_area.grid_rowconfigure(1, weight=1)
        self.chat_area.grid_columnconfigure(0, weight=1)


        self.header = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.current_user_label = ctk.CTkLabel(self.header, text="Выберите диалог слева", font=ctk.CTkFont(size=15))
        self.current_user_label.pack(side="left")

        self.btn_close = ctk.CTkButton(
            self.header, text="Завершить сессию", 
            fg_color="#B71C1C", hover_color="#880E4F",
            width=150, command=self.close_dialog
        )
        self.btn_close.pack(side="right")


        self.display = ctk.CTkTextbox(self.chat_area, state="disabled", font=("Consolas", 12))
        self.display.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)


        self.bottom_bar = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        self.bottom_bar.grid(row=2, column=0, sticky="ew", pady=10)
        self.bottom_bar.grid_columnconfigure(0, weight=1)

        self.input_field = ctk.CTkEntry(self.bottom_bar, placeholder_text="Ответить рабочему...", height=45)
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_field.bind("<Return>", lambda e: self.send_message())

        self.btn_send = ctk.CTkButton(self.bottom_bar, text="ПОСЛАТЬ", width=100, height=45, command=self.send_message)
        self.btn_send.grid(row=0, column=1)


        threading.Thread(target=self.deep_db_scanner, daemon=True).start()
        threading.Thread(target=self.live_chat_updater, daemon=True).start()



    def deep_db_scanner(self):
        """Глубокая проверка: ищем документы, у которых есть подколлекция messages"""
        while True:
            try:

                docs = db.collection("support_chats").list_documents()
                active_users = []

                for doc in docs:

                    msgs = doc.collection("messages").limit(1).get()
                    if len(msgs) > 0:
                        active_users.append(doc.id)

                if active_users != self.known_users:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Обнаружены чаты: {active_users}")
                    self.known_users = active_users
                    for widget in self.user_list_frame.winfo_children():
                        widget.destroy()
                    
                    for uid in self.known_users:
                        b = ctk.CTkButton(
                            self.user_list_frame, text=uid, anchor="w",
                            fg_color="transparent", hover_color="#333333",
                            command=lambda u=uid: self.select_chat(u)
                        )
                        b.pack(fill="x", pady=2)
            except Exception as e:
                print(f"Ошибка сканера: {e}")
            time.sleep(4)

    def select_chat(self, uid):
        self.selected_user = uid
        self.current_user_label.configure(text=f"Активен: {uid}")
        self.update_chat_view()

    def send_push(self, email, title, body):
        try:
            u_doc = db.collection("users").document(email).get()
            if u_doc.exists:
                tkn = u_doc.to_dict().get('fcmToken')
                if tkn:
                    m = messaging.Message(notification=messaging.Notification(title=title, body=body), token=tkn)
                    messaging.send(m)
        except: pass

    def send_message(self):
        txt = self.input_field.get()
        if txt and self.selected_user:
            db.collection("support_chats").document(self.selected_user).collection("messages").add({
                "text": txt, "sender": "admin", "createdAt": firestore.SERVER_TIMESTAMP
            })
            self.send_push(self.selected_user, "67Post: Ответ", txt)
            self.input_field.delete(0, 'end')

    def close_dialog(self):
        if not self.selected_user: return
        u = self.selected_user
        def _close():
            r = db.collection("support_chats").document(u).collection("messages")
            r.add({"text": "Спасибо за обращение в поддержку 67Post!", "sender": "bot", "createdAt": firestore.SERVER_TIMESTAMP})
            time.sleep(0.6)
            r.add({"text": "Пожалуйста, оцените качество работы.", "sender": "bot", "createdAt": firestore.SERVER_TIMESTAMP})
            time.sleep(0.6)
            r.add({"text": "SERVICE_RATING_REQUEST", "sender": "bot", "createdAt": firestore.SERVER_TIMESTAMP})
            self.send_push(u, "Чат закрыт", "Поставьте оценку работе оператора")
        threading.Thread(target=_close).start()

    def live_chat_updater(self):
        """Постоянное обновление текста сообщений"""
        while True:
            if self.selected_user:
                self.update_chat_view()
            time.sleep(2)

    def update_chat_view(self):
        try:
            m_docs = db.collection("support_chats").document(self.selected_user)\
                       .collection("messages").order_by("createdAt").stream()
            out = ""
            for d in m_docs:
                v = d.to_dict()
                s = "ОПЕРАТОР" if v.get("sender") == "admin" else "РАБОЧИЙ"
                if v.get("sender") == "bot": s = "СИСТЕМА"
                out += f"[{s}]: {v.get('text')}\n\n"

            self.display.configure(state="normal")
            self.display.delete("1.0", "end")
            self.display.insert("end", out)
            self.display.see("end")
            self.display.configure(state="disabled")
        except: pass

if __name__ == "__main__":
    app = Admin67Post()
    app.mainloop()