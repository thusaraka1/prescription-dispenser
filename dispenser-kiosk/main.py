#!/usr/bin/env python3
# ==========================================
# SMD Kiosk — Native GUI Application
# ==========================================
# CustomTkinter fullscreen kiosk for the
# Smart Medicine Dispenser on Raspberry Pi.
# OS: Raspbian / Ubuntu

import customtkinter as ctk
import threading
import logging
import requests as http_requests
import time
import sys

from config import (
    FIREBASE_URL, MANUAL_MIN_QUANTITY, MANUAL_MAX_QUANTITY,
    AUTO_RETURN_TIMEOUT
)
from hardware import HardwareController

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---- Theme ----
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---- Color Palette ----
COLORS = {
    'bg_dark':       '#040e1a',
    'bg_primary':    '#08457e',
    'bg_card':       '#0c2d52',
    'bg_card_hover': '#103a68',
    'primary_900':   '#08457e',
    'primary_700':   '#1160a4',
    'primary_600':   '#1a70b7',
    'primary_500':   '#436093',
    'primary_400':   '#6a7ea8',
    'primary_300':   '#8f9cbd',
    'primary_200':   '#b4bcd3',
    'primary_100':   '#d9dde9',
    'accent':        '#38bdf8',
    'accent_dark':   '#0ea5e9',
    'success':       '#22c55e',
    'success_dark':  '#16a34a',
    'danger':        '#ef4444',
    'warning':       '#f59e0b',
    'white':         '#ffffff',
    'text_muted':    '#8f9cbd',
    'text_secondary':'#b4bcd3',
}


class SMDKiosk(ctk.CTk):
    """Main kiosk application window."""

    def __init__(self):
        super().__init__()

        # ---- Window Setup ----
        self.title("Smart Medicine Dispenser")
        self.geometry("1024x600")
        self.configure(fg_color=COLORS['bg_dark'])

        # Fullscreen on Raspberry Pi (Linux)
        if sys.platform.startswith('linux'):
            self.attributes('-fullscreen', True)
            self.config(cursor='none')  # Hide cursor for touch kiosk
        else:
            # Dev mode on Windows
            self.state('zoomed')

        # Escape to exit fullscreen (dev convenience)
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', False) if sys.platform.startswith('linux') else None)
        self.bind('<F11>', lambda e: self.attributes('-fullscreen', True))

        # ---- State ----
        self.hardware = HardwareController()
        self.prescription_data = None
        self.medicines_list = []
        self.selected_medicine = None
        self.manual_quantity = MANUAL_MIN_QUANTITY
        self.countdown_seconds = AUTO_RETURN_TIMEOUT
        self.countdown_job = None
        self.dispense_poll_job = None
        self.current_frame = None

        # ---- Container ----
        self.container = ctk.CTkFrame(self, fg_color=COLORS['bg_dark'])
        self.container.pack(fill='both', expand=True)

        # ---- Frames (screens) ----
        self.frames = {}
        self.show_welcome()

    # ==========================================
    # Navigation
    # ==========================================

    def clear_container(self):
        """Remove all widgets from the container."""
        if self.countdown_job:
            self.after_cancel(self.countdown_job)
            self.countdown_job = None
        if self.dispense_poll_job:
            self.after_cancel(self.dispense_poll_job)
            self.dispense_poll_job = None
        for widget in self.container.winfo_children():
            widget.destroy()

    # ==========================================
    # SCREEN 1: WELCOME
    # ==========================================

    def show_welcome(self):
        self.clear_container()
        self.prescription_data = None
        self.selected_medicine = None
        self.manual_quantity = MANUAL_MIN_QUANTITY

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        # Logo icon
        logo_frame = ctk.CTkFrame(frame, width=100, height=100,
                                   corner_radius=50,
                                   fg_color=COLORS['primary_900'],
                                   border_width=2,
                                   border_color=COLORS['accent'])
        logo_frame.pack(pady=(0, 8))
        logo_frame.pack_propagate(False)
        logo_label = ctk.CTkLabel(logo_frame, text="+",
                                   font=ctk.CTkFont(size=48, weight='bold'),
                                   text_color=COLORS['accent'])
        logo_label.place(relx=0.5, rely=0.5, anchor='center')

        # Title
        title = ctk.CTkLabel(frame, text="Welcome to SMD",
                              font=ctk.CTkFont(family='Inter', size=42, weight='bold'),
                              text_color=COLORS['white'])
        title.pack(pady=(12, 4))

        subtitle = ctk.CTkLabel(frame, text="SMART MEDICINE DISPENSER",
                                 font=ctk.CTkFont(size=14, weight='normal'),
                                 text_color=COLORS['text_muted'])
        subtitle.pack(pady=(0, 40))

        # ---- Action Buttons ----
        btn_container = ctk.CTkFrame(frame, fg_color='transparent')
        btn_container.pack()

        # Scan Barcode Button
        scan_btn = self._create_action_button(
            btn_container,
            icon_text="\u2750",  # barcode-like character
            title="Scan Bar Code",
            subtitle="Use your prescription barcode",
            color=COLORS['primary_900'],
            border_color=COLORS['accent'],
            command=self.show_scan
        )
        scan_btn.pack(pady=(0, 16), fill='x')

        # Select Medicine Button
        med_btn = self._create_action_button(
            btn_container,
            icon_text="\u2695",  # medical symbol
            title="Select Medicine",
            subtitle="Manually choose medication",
            color=COLORS['bg_card'],
            border_color=COLORS['primary_500'],
            command=self.show_medicine_list
        )
        med_btn.pack(fill='x')

        # Footer
        footer = ctk.CTkLabel(frame, text="--- Touch to begin ---",
                               font=ctk.CTkFont(size=12),
                               text_color=COLORS['text_muted'])
        footer.pack(pady=(40, 0))

    def _create_action_button(self, parent, icon_text, title, subtitle, color, border_color, command):
        """Create a large touchscreen-friendly action button."""
        btn_frame = ctk.CTkFrame(parent, fg_color=color,
                                  corner_radius=20,
                                  border_width=1,
                                  border_color=border_color,
                                  height=90, width=440)
        btn_frame.pack_propagate(False)

        inner = ctk.CTkFrame(btn_frame, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=24, pady=16)

        # Icon
        icon_box = ctk.CTkFrame(inner, width=56, height=56,
                                 corner_radius=14,
                                 fg_color=self._alpha_color(border_color, 0.2))
        icon_box.pack(side='left', padx=(0, 18))
        icon_box.pack_propagate(False)
        icon_label = ctk.CTkLabel(icon_box, text=icon_text,
                                   font=ctk.CTkFont(size=26),
                                   text_color=border_color)
        icon_label.place(relx=0.5, rely=0.5, anchor='center')

        # Text
        text_frame = ctk.CTkFrame(inner, fg_color='transparent')
        text_frame.pack(side='left', fill='both', expand=True)

        title_lbl = ctk.CTkLabel(text_frame, text=title,
                                  font=ctk.CTkFont(size=20, weight='bold'),
                                  text_color=COLORS['white'],
                                  anchor='w')
        title_lbl.pack(anchor='w')

        sub_lbl = ctk.CTkLabel(text_frame, text=subtitle,
                                font=ctk.CTkFont(size=12),
                                text_color=COLORS['text_muted'],
                                anchor='w')
        sub_lbl.pack(anchor='w')

        # Arrow
        arrow = ctk.CTkLabel(inner, text=">",
                              font=ctk.CTkFont(size=22, weight='bold'),
                              text_color=COLORS['text_muted'])
        arrow.pack(side='right')

        # Make entire frame clickable
        for widget in [btn_frame, inner, icon_box, icon_label, text_frame, title_lbl, sub_lbl, arrow]:
            widget.bind('<Button-1>', lambda e, cmd=command: cmd())

        return btn_frame

    def _alpha_color(self, hex_color, alpha):
        """Approximate alpha blending with dark background."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        bg_r, bg_g, bg_b = 4, 14, 26  # bg_dark
        nr = int(r * alpha + bg_r * (1 - alpha))
        ng = int(g * alpha + bg_g * (1 - alpha))
        nb = int(b * alpha + bg_b * (1 - alpha))
        return f'#{nr:02x}{ng:02x}{nb:02x}'

    # ==========================================
    # SCREEN 2a: SCAN BARCODE
    # ==========================================

    def show_scan(self):
        self.clear_container()

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        # Back button
        self._add_back_button(self.container, self.show_welcome)

        # Scanner visual
        scanner_frame = ctk.CTkFrame(frame, width=180, height=180,
                                      corner_radius=20,
                                      fg_color=self._alpha_color(COLORS['accent'], 0.08),
                                      border_width=3,
                                      border_color=COLORS['accent'])
        scanner_frame.pack(pady=(0, 20))
        scanner_frame.pack_propagate(False)

        barcode_icon = ctk.CTkLabel(scanner_frame, text="|||||||||||",
                                     font=ctk.CTkFont(size=40, weight='bold'),
                                     text_color=COLORS['primary_400'])
        barcode_icon.place(relx=0.5, rely=0.5, anchor='center')

        # Animated scan line (simulated with label color changes)
        self.scan_line = ctk.CTkFrame(scanner_frame, height=3, width=140,
                                       fg_color=COLORS['accent'],
                                       corner_radius=2)
        self.scan_line.place(relx=0.5, rely=0.2, anchor='center')
        self._animate_scan_line()

        # Title
        title = ctk.CTkLabel(frame, text="Ready to Scan",
                              font=ctk.CTkFont(size=32, weight='bold'),
                              text_color=COLORS['white'])
        title.pack(pady=(0, 4))

        self.scan_status = ctk.CTkLabel(frame, text="Please scan your prescription barcode",
                                         font=ctk.CTkFont(size=14),
                                         text_color=COLORS['text_secondary'])
        self.scan_status.pack(pady=(0, 24))

        # Manual barcode input
        input_frame = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'],
                                    corner_radius=16,
                                    border_width=1,
                                    border_color=COLORS['primary_500'])
        input_frame.pack(fill='x', padx=20)

        inner_input = ctk.CTkFrame(input_frame, fg_color='transparent')
        inner_input.pack(fill='x', padx=4, pady=4)

        self.barcode_entry = ctk.CTkEntry(
            inner_input,
            placeholder_text="Type barcode ID (e.g. RX-123456)",
            font=ctk.CTkFont(size=16),
            height=50,
            fg_color='transparent',
            border_width=0,
            text_color=COLORS['white']
        )
        self.barcode_entry.pack(side='left', fill='x', expand=True, padx=(12, 4))
        self.barcode_entry.bind('<Return>', lambda e: self._process_barcode())

        search_btn = ctk.CTkButton(
            inner_input, text="Search", width=90, height=46,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color=COLORS['primary_700'],
            hover_color=COLORS['primary_600'],
            corner_radius=12,
            command=self._process_barcode
        )
        search_btn.pack(side='right', padx=(0, 4))

        # Focus the entry
        self.barcode_entry.focus_set()

        # Hidden entry for USB barcode scanner (captures rapid keypresses)
        self._barcode_buffer = ''
        self.container.bind('<Key>', self._on_key_for_barcode)

        # Hint
        hint = ctk.CTkLabel(frame, text="Hold your barcode under the scanner",
                             font=ctk.CTkFont(size=12),
                             text_color=COLORS['text_muted'])
        hint.pack(pady=(16, 0))

    def _animate_scan_line(self):
        """Animate the scan line up and down."""
        if not hasattr(self, 'scan_line') or not self.scan_line.winfo_exists():
            return
        if not hasattr(self, '_scan_dir'):
            self._scan_dir = 1
            self._scan_pos = 0.2

        self._scan_pos += 0.02 * self._scan_dir
        if self._scan_pos >= 0.8:
            self._scan_dir = -1
        elif self._scan_pos <= 0.2:
            self._scan_dir = 1

        self.scan_line.place(relx=0.5, rely=self._scan_pos, anchor='center')
        self.after(50, self._animate_scan_line)

    def _on_key_for_barcode(self, event):
        """Capture USB barcode scanner rapid keystrokes."""
        if event.keysym == 'Return':
            if len(self._barcode_buffer) >= 3:
                self.barcode_entry.delete(0, 'end')
                self.barcode_entry.insert(0, self._barcode_buffer)
                self._process_barcode()
            self._barcode_buffer = ''
        elif len(event.char) == 1 and event.char.isprintable():
            self._barcode_buffer += event.char

    def _process_barcode(self):
        barcode = self.barcode_entry.get().strip()
        if len(barcode) < 3:
            return

        self.scan_status.configure(text="Searching for prescription...", text_color=COLORS['accent'])

        def fetch():
            try:
                url = f"{FIREBASE_URL}/prescriptions/{barcode}.json"
                response = http_requests.get(url, timeout=10)
                data = response.json()

                if data is None:
                    self.after(0, lambda: self._show_error("Prescription Not Found",
                        f"No prescription found for barcode: {barcode}"))
                    self.after(0, lambda: self.scan_status.configure(
                        text="Please scan your prescription barcode",
                        text_color=COLORS['text_secondary']))
                    return

                if data.get('status') == 'Dispersed':
                    self.after(0, lambda: self._show_error("Already Dispensed",
                        "This prescription has already been dispensed."))
                    self.after(0, lambda: self.scan_status.configure(
                        text="Please scan your prescription barcode",
                        text_color=COLORS['text_secondary']))
                    return

                self.prescription_data = data
                self.after(0, self.show_verified)

            except Exception as e:
                logger.error(f"Barcode fetch error: {e}")
                self.after(0, lambda: self._show_error("Connection Error",
                    "Could not connect to the database. Please try again."))
                self.after(0, lambda: self.scan_status.configure(
                    text="Please scan your prescription barcode",
                    text_color=COLORS['text_secondary']))

        threading.Thread(target=fetch, daemon=True).start()

    # ==========================================
    # SCREEN 3a: PATIENT VERIFIED
    # ==========================================

    def show_verified(self):
        self.clear_container()
        p = self.prescription_data
        if not p:
            self.show_welcome()
            return

        # Scrollable frame for content
        scroll = ctk.CTkScrollableFrame(self.container, fg_color='transparent',
                                         scrollbar_button_color=COLORS['primary_500'])
        scroll.pack(fill='both', expand=True, padx=20, pady=20)

        self._add_back_button(self.container, self.show_scan)

        # Verified badge
        badge_frame = ctk.CTkFrame(scroll, fg_color='transparent')
        badge_frame.pack(pady=(40, 8))

        check_circle = ctk.CTkFrame(badge_frame, width=72, height=72,
                                     corner_radius=36,
                                     fg_color=COLORS['success'])
        check_circle.pack()
        check_circle.pack_propagate(False)
        check_lbl = ctk.CTkLabel(check_circle, text="✓",
                                  font=ctk.CTkFont(size=36, weight='bold'),
                                  text_color=COLORS['white'])
        check_lbl.place(relx=0.5, rely=0.5, anchor='center')

        verified_title = ctk.CTkLabel(badge_frame, text="Patient Verified",
                                       font=ctk.CTkFont(size=24, weight='bold'),
                                       text_color=COLORS['success'])
        verified_title.pack(pady=(8, 0))

        # ---- Patient Details Card ----
        patient_card = self._create_info_card(scroll, "Patient Details", [
            ("Name", p.get('patientName', '-')),
            ("Phone", p.get('phone', '-')),
            ("Date Issued", p.get('date', '-')),
            ("Prescription ID", p.get('id', '-')),
        ])
        patient_card.pack(fill='x', padx=40, pady=(16, 8))

        # ---- Medication Details Card ----
        med_card = ctk.CTkFrame(scroll, fg_color=COLORS['bg_card'],
                                 corner_radius=16,
                                 border_width=1,
                                 border_color=COLORS['primary_500'])
        med_card.pack(fill='x', padx=40, pady=(8, 16))

        med_header = ctk.CTkFrame(med_card, fg_color='transparent')
        med_header.pack(fill='x', padx=20, pady=(16, 8))

        ctk.CTkLabel(med_header, text="Medication Details",
                      font=ctk.CTkFont(size=16, weight='bold'),
                      text_color=COLORS['white']).pack(side='left')

        medicines = p.get('medicines', [])
        for med in medicines:
            self._create_med_row(med_card, med)

        # ---- Dispense Button ----
        dispense_btn = ctk.CTkButton(
            scroll, text="  Dispense Medications  ",
            font=ctk.CTkFont(size=20, weight='bold'),
            height=60, corner_radius=20,
            fg_color=COLORS['success'],
            hover_color=COLORS['success_dark'],
            command=self._start_prescription_dispense
        )
        dispense_btn.pack(pady=(8, 20))

    def _create_info_card(self, parent, title, items):
        """Create a glass card with key-value pairs."""
        card = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'],
                             corner_radius=16,
                             border_width=1,
                             border_color=COLORS['primary_500'])

        # Header
        header = ctk.CTkFrame(card, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(16, 12))
        ctk.CTkLabel(header, text=title,
                      font=ctk.CTkFont(size=16, weight='bold'),
                      text_color=COLORS['white']).pack(side='left')

        # Separator
        sep = ctk.CTkFrame(card, height=1, fg_color=COLORS['primary_500'])
        sep.pack(fill='x', padx=20)

        # Grid of items
        grid_frame = ctk.CTkFrame(card, fg_color='transparent')
        grid_frame.pack(fill='x', padx=20, pady=(12, 16))

        for i, (label, value) in enumerate(items):
            row = i // 2
            col = i % 2

            item_frame = ctk.CTkFrame(grid_frame, fg_color='transparent')
            item_frame.grid(row=row, column=col, sticky='w', padx=(0, 20), pady=6)

            ctk.CTkLabel(item_frame, text=label.upper(),
                          font=ctk.CTkFont(size=10, weight='bold'),
                          text_color=COLORS['text_muted']).pack(anchor='w')
            ctk.CTkLabel(item_frame, text=str(value),
                          font=ctk.CTkFont(size=14, weight='bold'),
                          text_color=COLORS['white']).pack(anchor='w')

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        return card

    def _create_med_row(self, parent, med):
        """Create a single medicine row in the verified screen."""
        row = ctk.CTkFrame(parent, fg_color=self._alpha_color(COLORS['accent'], 0.05),
                            corner_radius=12)
        row.pack(fill='x', padx=16, pady=4)

        inner = ctk.CTkFrame(row, fg_color='transparent')
        inner.pack(fill='x', padx=16, pady=12)

        # Left: medicine info
        info = ctk.CTkFrame(inner, fg_color='transparent')
        info.pack(side='left', fill='x', expand=True)

        ctk.CTkLabel(info, text=med.get('name', 'Unknown'),
                      font=ctk.CTkFont(size=15, weight='bold'),
                      text_color=COLORS['white']).pack(anchor='w')

        detail_text = f"{med.get('dosage', '')}  |  {med.get('type', '')}  |  {med.get('dose', 1)} units x {med.get('frequency', 1)}/day x {med.get('duration', 1)} days"
        ctk.CTkLabel(info, text=detail_text,
                      font=ctk.CTkFont(size=11),
                      text_color=COLORS['text_muted']).pack(anchor='w')

        # Right: quantity badge
        qty_frame = ctk.CTkFrame(inner, fg_color=self._alpha_color(COLORS['accent'], 0.15),
                                  corner_radius=12, width=70, height=50,
                                  border_width=1,
                                  border_color=self._alpha_color(COLORS['accent'], 0.3))
        qty_frame.pack(side='right')
        qty_frame.pack_propagate(False)

        qty_val = ctk.CTkLabel(qty_frame, text=str(med.get('totalQuantity', 0)),
                                font=ctk.CTkFont(size=22, weight='bold'),
                                text_color=COLORS['accent'])
        qty_val.place(relx=0.5, rely=0.35, anchor='center')

        qty_label = ctk.CTkLabel(qty_frame, text="UNITS",
                                  font=ctk.CTkFont(size=8, weight='bold'),
                                  text_color=COLORS['text_muted'])
        qty_label.place(relx=0.5, rely=0.75, anchor='center')

    # ==========================================
    # SCREEN 2b: MEDICINE LIST (Manual Flow)
    # ==========================================

    def show_medicine_list(self):
        self.clear_container()

        self._add_back_button(self.container, self.show_welcome)

        # Header area
        header = ctk.CTkFrame(self.container, fg_color='transparent')
        header.pack(fill='x', padx=40, pady=(70, 8))

        ctk.CTkLabel(header, text="Select Medicine",
                      font=ctk.CTkFont(size=32, weight='bold'),
                      text_color=COLORS['white']).pack()
        ctk.CTkLabel(header, text="Choose from available medications",
                      font=ctk.CTkFont(size=14),
                      text_color=COLORS['text_secondary']).pack(pady=(4, 0))

        # Search bar
        search_frame = ctk.CTkFrame(self.container, fg_color=COLORS['bg_card'],
                                     corner_radius=16,
                                     border_width=1,
                                     border_color=COLORS['primary_500'],
                                     height=50)
        search_frame.pack(fill='x', padx=60, pady=(16, 12))

        self.med_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search medicines...",
            font=ctk.CTkFont(size=15),
            fg_color='transparent',
            border_width=0,
            height=46,
            text_color=COLORS['white']
        )
        self.med_search_entry.pack(fill='x', padx=16, pady=2)
        self.med_search_entry.bind('<KeyRelease>', self._on_med_search)

        # Medicine list (scrollable)
        self.med_list_frame = ctk.CTkScrollableFrame(
            self.container, fg_color='transparent',
            scrollbar_button_color=COLORS['primary_500']
        )
        self.med_list_frame.pack(fill='both', expand=True, padx=40, pady=(4, 20))

        # Loading indicator
        self.med_loading = ctk.CTkLabel(self.med_list_frame, text="Loading medicines...",
                                         font=ctk.CTkFont(size=16),
                                         text_color=COLORS['text_muted'])
        self.med_loading.pack(pady=40)

        # Fetch medicines in background
        threading.Thread(target=self._fetch_medicines, daemon=True).start()

    def _fetch_medicines(self):
        try:
            url = f"{FIREBASE_URL}/medicines.json"
            response = http_requests.get(url, timeout=10)
            data = response.json()

            self.medicines_list = []
            if data:
                for key, value in data.items():
                    self.medicines_list.append({'id': key, **value})

            self.after(0, lambda: self._render_medicine_list(self.medicines_list))

        except Exception as e:
            logger.error(f"Error fetching medicines: {e}")
            self.after(0, lambda: self.med_loading.configure(
                text="Failed to load medicines. Check connection."))

    def _render_medicine_list(self, medicines):
        # Clear existing
        for widget in self.med_list_frame.winfo_children():
            widget.destroy()

        if not medicines:
            ctk.CTkLabel(self.med_list_frame, text="No medicines available.",
                          font=ctk.CTkFont(size=14),
                          text_color=COLORS['text_muted']).pack(pady=40)
            return

        for idx, med in enumerate(medicines):
            self._create_medicine_item(self.med_list_frame, med, idx)

    def _create_medicine_item(self, parent, med, slot_index):
        """Create a clickable medicine row."""
        # Choose icon based on type
        type_icons = {
            'Tablet': 'T', 'Capsule': 'C', 'Syrup': 'S',
            'Injection': 'I', 'Drops': 'D', 'Ointment': 'O'
        }
        icon = type_icons.get(med.get('type', ''), 'Rx')

        item = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'],
                             corner_radius=16,
                             border_width=1,
                             border_color=COLORS['primary_500'],
                             height=72)
        item.pack(fill='x', pady=5)
        item.pack_propagate(False)

        inner = ctk.CTkFrame(item, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=16, pady=10)

        # Icon
        icon_box = ctk.CTkFrame(inner, width=46, height=46,
                                 corner_radius=14,
                                 fg_color=self._alpha_color(COLORS['accent'], 0.15))
        icon_box.pack(side='left', padx=(0, 14))
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, text=icon,
                      font=ctk.CTkFont(size=18, weight='bold'),
                      text_color=COLORS['accent']).place(relx=0.5, rely=0.5, anchor='center')

        # Info
        info = ctk.CTkFrame(inner, fg_color='transparent')
        info.pack(side='left', fill='both', expand=True)

        ctk.CTkLabel(info, text=med.get('name', 'Unknown'),
                      font=ctk.CTkFont(size=16, weight='bold'),
                      text_color=COLORS['white']).pack(anchor='w')

        meta_text = f"{med.get('dosage', '-')}  |  {med.get('type', '-')}"
        ctk.CTkLabel(info, text=meta_text,
                      font=ctk.CTkFont(size=11),
                      text_color=COLORS['text_muted']).pack(anchor='w')

        # Arrow
        ctk.CTkLabel(inner, text=">",
                      font=ctk.CTkFont(size=20, weight='bold'),
                      text_color=COLORS['text_muted']).pack(side='right')

        # Make clickable
        def on_click(e=None):
            self.selected_medicine = {**med, 'slot': slot_index}
            self.show_quantity()

        for widget in [item, inner, icon_box, info]:
            widget.bind('<Button-1>', on_click)
        # Bind children too
        for child in info.winfo_children():
            child.bind('<Button-1>', on_click)

    def _on_med_search(self, event=None):
        query = self.med_search_entry.get().lower().strip()
        if not query:
            self._render_medicine_list(self.medicines_list)
            return
        filtered = [m for m in self.medicines_list if query in m.get('name', '').lower()]
        self._render_medicine_list(filtered)

    # ==========================================
    # SCREEN 3b: SELECT QUANTITY
    # ==========================================

    def show_quantity(self):
        self.clear_container()
        self.manual_quantity = MANUAL_MIN_QUANTITY

        self._add_back_button(self.container, self.show_medicine_list)

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        # Title
        ctk.CTkLabel(frame, text="Select Quantity",
                      font=ctk.CTkFont(size=32, weight='bold'),
                      text_color=COLORS['white']).pack(pady=(0, 4))

        med_name = self.selected_medicine.get('name', '-') if self.selected_medicine else '-'
        med_detail = f"{med_name} -- {self.selected_medicine.get('dosage', '')} ({self.selected_medicine.get('type', '')})" if self.selected_medicine else '-'
        ctk.CTkLabel(frame, text=med_detail,
                      font=ctk.CTkFont(size=14),
                      text_color=COLORS['text_secondary']).pack(pady=(0, 36))

        # ---- Quantity Selector ----
        qty_row = ctk.CTkFrame(frame, fg_color='transparent')
        qty_row.pack()

        # Minus button
        minus_btn = ctk.CTkButton(
            qty_row, text="-",
            width=72, height=72,
            corner_radius=36,
            font=ctk.CTkFont(size=32, weight='bold'),
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_card_hover'],
            border_width=2,
            border_color=COLORS['primary_500'],
            text_color=COLORS['danger'],
            command=lambda: self._adjust_qty(-1)
        )
        minus_btn.pack(side='left', padx=(0, 24))

        # Quantity display
        qty_box = ctk.CTkFrame(qty_row, width=140, height=140,
                                corner_radius=28,
                                fg_color=COLORS['bg_card'],
                                border_width=2,
                                border_color=COLORS['accent'])
        qty_box.pack(side='left')
        qty_box.pack_propagate(False)

        self.qty_label = ctk.CTkLabel(qty_box, text=str(self.manual_quantity),
                                       font=ctk.CTkFont(size=52, weight='bold'),
                                       text_color=COLORS['white'])
        self.qty_label.place(relx=0.5, rely=0.5, anchor='center')

        # Plus button
        plus_btn = ctk.CTkButton(
            qty_row, text="+",
            width=72, height=72,
            corner_radius=36,
            font=ctk.CTkFont(size=32, weight='bold'),
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_card_hover'],
            border_width=2,
            border_color=COLORS['primary_500'],
            text_color=COLORS['success'],
            command=lambda: self._adjust_qty(1)
        )
        plus_btn.pack(side='left', padx=(24, 0))

        # Limits
        limits_frame = ctk.CTkFrame(frame, fg_color='transparent')
        limits_frame.pack(pady=(20, 0))

        ctk.CTkLabel(limits_frame, text=f"Min: {MANUAL_MIN_QUANTITY}",
                      font=ctk.CTkFont(size=13),
                      text_color=COLORS['text_muted']).pack(side='left', padx=(0, 32))
        ctk.CTkLabel(limits_frame, text=f"Max: {MANUAL_MAX_QUANTITY}",
                      font=ctk.CTkFont(size=13),
                      text_color=COLORS['text_muted']).pack(side='left')

        # Dispense button
        dispense_btn = ctk.CTkButton(
            frame, text="  Dispense  ",
            font=ctk.CTkFont(size=20, weight='bold'),
            height=60, width=320, corner_radius=20,
            fg_color=COLORS['success'],
            hover_color=COLORS['success_dark'],
            command=self._start_manual_dispense
        )
        dispense_btn.pack(pady=(36, 0))

    def _adjust_qty(self, delta):
        self.manual_quantity += delta
        self.manual_quantity = max(MANUAL_MIN_QUANTITY, min(MANUAL_MAX_QUANTITY, self.manual_quantity))
        self.qty_label.configure(text=str(self.manual_quantity))

    # ==========================================
    # SCREEN 4: DISPENSING
    # ==========================================

    def show_dispensing(self):
        self.clear_container()

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        # Pill animation (3 bouncing dots)
        dots_frame = ctk.CTkFrame(frame, fg_color='transparent', height=80)
        dots_frame.pack(pady=(0, 20))

        self.anim_dots = []
        dot_colors = [COLORS['accent'], '#a78bfa', COLORS['success']]
        for i, color in enumerate(dot_colors):
            dot = ctk.CTkFrame(dots_frame, width=24, height=24,
                                corner_radius=12, fg_color=color)
            dot.pack(side='left', padx=8, pady=28)
            self.anim_dots.append(dot)

        self._animate_dots(0)

        # Title
        title_frame = ctk.CTkFrame(frame, fg_color='transparent')
        title_frame.pack(pady=(0, 24))

        ctk.CTkLabel(title_frame, text="Medications are",
                      font=ctk.CTkFont(size=28, weight='bold'),
                      text_color=COLORS['white']).pack()
        ctk.CTkLabel(title_frame, text="Dispensing",
                      font=ctk.CTkFont(size=32, weight='bold'),
                      text_color=COLORS['accent']).pack()

        # Progress section
        progress_container = ctk.CTkFrame(frame, fg_color='transparent', width=460)
        progress_container.pack(fill='x', padx=40)

        # Progress info row
        info_row = ctk.CTkFrame(progress_container, fg_color='transparent')
        info_row.pack(fill='x', pady=(0, 8))

        self.dispense_med_label = ctk.CTkLabel(info_row, text="Preparing...",
                                                font=ctk.CTkFont(size=14, weight='bold'),
                                                text_color=COLORS['white'])
        self.dispense_med_label.pack(side='left')

        self.dispense_percent_label = ctk.CTkLabel(info_row, text="0%",
                                                     font=ctk.CTkFont(size=14, weight='bold'),
                                                     text_color=COLORS['accent'])
        self.dispense_percent_label.pack(side='right')

        # Progress bar
        self.dispense_progress = ctk.CTkProgressBar(
            progress_container, height=14,
            corner_radius=7,
            progress_color=COLORS['accent'],
            fg_color=self._alpha_color(COLORS['accent'], 0.1)
        )
        self.dispense_progress.pack(fill='x')
        self.dispense_progress.set(0)

        # Detail text
        self.dispense_detail = ctk.CTkLabel(progress_container,
                                             text="Starting dispensing process...",
                                             font=ctk.CTkFont(size=12),
                                             text_color=COLORS['text_muted'])
        self.dispense_detail.pack(pady=(8, 0))

        # Warning
        warning_frame = ctk.CTkFrame(frame,
                                      fg_color=self._alpha_color(COLORS['warning'], 0.08),
                                      corner_radius=12,
                                      border_width=1,
                                      border_color=self._alpha_color(COLORS['warning'], 0.2))
        warning_frame.pack(pady=(24, 0), padx=20, fill='x')

        ctk.CTkLabel(warning_frame,
                      text="Please do not leave. Medications are being prepared.",
                      font=ctk.CTkFont(size=12, weight='bold'),
                      text_color=COLORS['warning']).pack(padx=16, pady=10)

    def _animate_dots(self, step):
        """Animate the 3 dispensing dots."""
        if not hasattr(self, 'anim_dots') or not self.anim_dots:
            return
        try:
            for i, dot in enumerate(self.anim_dots):
                if not dot.winfo_exists():
                    return
                offset = 20 if (step % 3) == i else 0
                dot.pack_configure(pady=(28 - offset, offset))
            self.after(300, lambda: self._animate_dots(step + 1))
        except Exception:
            pass

    def _start_prescription_dispense(self):
        """Begin dispensing from a scanned prescription."""
        if not self.prescription_data:
            return

        medicines = self.prescription_data.get('medicines', [])
        barcode_id = self.prescription_data.get('id')

        self.show_dispensing()

        def run():
            total_meds = len(medicines)
            total_units = sum(m.get('totalQuantity', 0) for m in medicines)
            units_done = 0

            for idx, med in enumerate(medicines):
                name = med.get('name', 'Unknown')
                qty = med.get('totalQuantity', 1)
                slot = idx % len(self.hardware.servo_pins)

                self.after(0, lambda n=name: self.dispense_med_label.configure(text=f"Dispensing {n}..."))
                self.after(0, lambda n=name: self.dispense_detail.configure(
                    text=f"Medicine {idx+1} of {total_meds}"))

                def progress_cb(dispensed, total, ud=units_done):
                    pct = int(((ud + dispensed) / total_units) * 100) if total_units > 0 else 100
                    self.after(0, lambda p=pct: self.dispense_progress.set(p / 100))
                    self.after(0, lambda p=pct: self.dispense_percent_label.configure(text=f"{p}%"))

                self.hardware.dispense(slot, qty, progress_callback=progress_cb)
                units_done += qty

            # Mark as dispersed in Firebase
            if barcode_id:
                try:
                    url = f"{FIREBASE_URL}/prescriptions/{barcode_id}.json"
                    http_requests.patch(url, json={'status': 'Dispersed'}, timeout=10)
                    logger.info(f"Prescription {barcode_id} marked as Dispersed")
                except Exception as e:
                    logger.error(f"Failed to update Firebase: {e}")

            self.after(0, lambda: self.dispense_progress.set(1.0))
            self.after(0, lambda: self.dispense_percent_label.configure(text="100%"))
            self.after(0, lambda: self.dispense_detail.configure(text="All medications dispensed!"))
            self.after(1500, self.show_complete)

        threading.Thread(target=run, daemon=True).start()

    def _start_manual_dispense(self):
        """Begin dispensing a manually selected medicine."""
        if not self.selected_medicine:
            return

        med_name = self.selected_medicine.get('name', 'Unknown')
        slot = self.selected_medicine.get('slot', 0)
        qty = self.manual_quantity

        self.show_dispensing()

        def run():
            self.after(0, lambda: self.dispense_med_label.configure(text=f"Dispensing {med_name}..."))
            self.after(0, lambda: self.dispense_detail.configure(text=f"Dispensing {qty} units"))

            def progress_cb(dispensed, total):
                pct = int((dispensed / total) * 100)
                self.after(0, lambda p=pct: self.dispense_progress.set(p / 100))
                self.after(0, lambda p=pct: self.dispense_percent_label.configure(text=f"{p}%"))

            self.hardware.dispense(slot, qty, progress_callback=progress_cb)

            self.after(0, lambda: self.dispense_progress.set(1.0))
            self.after(0, lambda: self.dispense_percent_label.configure(text="100%"))
            self.after(0, lambda: self.dispense_detail.configure(text="Dispensing complete!"))
            self.after(1500, self.show_complete)

        threading.Thread(target=run, daemon=True).start()

    # ==========================================
    # SCREEN 5: COMPLETE
    # ==========================================

    def show_complete(self):
        self.clear_container()
        self.countdown_seconds = AUTO_RETURN_TIMEOUT

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        # Success circle
        success_frame = ctk.CTkFrame(frame, width=100, height=100,
                                      corner_radius=50,
                                      fg_color=COLORS['success'])
        success_frame.pack(pady=(0, 16))
        success_frame.pack_propagate(False)
        ctk.CTkLabel(success_frame, text="✓",
                      font=ctk.CTkFont(size=48, weight='bold'),
                      text_color=COLORS['white']).place(relx=0.5, rely=0.5, anchor='center')

        # Title
        ctk.CTkLabel(frame, text="Collect Your",
                      font=ctk.CTkFont(size=32, weight='bold'),
                      text_color=COLORS['white']).pack()
        ctk.CTkLabel(frame, text="Medications",
                      font=ctk.CTkFont(size=36, weight='bold'),
                      text_color=COLORS['accent']).pack()

        ctk.CTkLabel(frame, text="Thank You!",
                      font=ctk.CTkFont(size=22, weight='normal'),
                      text_color=COLORS['text_secondary']).pack(pady=(12, 24))

        # Countdown
        self.countdown_label = ctk.CTkLabel(frame,
                                             text=f"Returning to home in {self.countdown_seconds}s",
                                             font=ctk.CTkFont(size=13),
                                             text_color=COLORS['text_muted'])
        self.countdown_label.pack(pady=(0, 20))

        # Done button
        done_btn = ctk.CTkButton(
            frame, text="  Done  ",
            font=ctk.CTkFont(size=18, weight='bold'),
            height=56, width=200, corner_radius=20,
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_card_hover'],
            border_width=1,
            border_color=COLORS['primary_500'],
            command=self.show_welcome
        )
        done_btn.pack()

        self._tick_countdown()

    def _tick_countdown(self):
        if self.countdown_seconds <= 0:
            self.show_welcome()
            return
        self.countdown_seconds -= 1
        if hasattr(self, 'countdown_label') and self.countdown_label.winfo_exists():
            self.countdown_label.configure(
                text=f"Returning to home in {self.countdown_seconds}s")
        self.countdown_job = self.after(1000, self._tick_countdown)

    # ==========================================
    # COMMON WIDGETS
    # ==========================================

    def _add_back_button(self, parent, command):
        """Add a back button in the top-left corner."""
        back_btn = ctk.CTkButton(
            parent, text="<",
            width=52, height=52,
            corner_radius=26,
            font=ctk.CTkFont(size=22, weight='bold'),
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_card_hover'],
            border_width=1,
            border_color=COLORS['primary_500'],
            text_color=COLORS['white'],
            command=command
        )
        back_btn.place(x=20, y=20)

    def _show_error(self, title, message):
        """Show an error dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Error")
        dialog.geometry("420x280")
        dialog.configure(fg_color=COLORS['bg_dark'])
        dialog.transient(self)
        dialog.grab_set()

        # Center it
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 210
        y = self.winfo_y() + (self.winfo_height() // 2) - 140
        dialog.geometry(f"420x280+{x}+{y}")

        frame = ctk.CTkFrame(dialog, fg_color=COLORS['bg_card'],
                              corner_radius=20,
                              border_width=1,
                              border_color=COLORS['danger'])
        frame.pack(fill='both', expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="!",
                      font=ctk.CTkFont(size=40, weight='bold'),
                      text_color=COLORS['danger']).pack(pady=(20, 8))

        ctk.CTkLabel(frame, text=title,
                      font=ctk.CTkFont(size=18, weight='bold'),
                      text_color=COLORS['white']).pack()

        ctk.CTkLabel(frame, text=message,
                      font=ctk.CTkFont(size=13),
                      text_color=COLORS['text_muted'],
                      wraplength=350).pack(pady=(8, 16))

        ctk.CTkButton(frame, text="Try Again",
                       font=ctk.CTkFont(size=14, weight='bold'),
                       height=44, width=180,
                       corner_radius=12,
                       fg_color=COLORS['danger'],
                       hover_color='#dc2626',
                       command=dialog.destroy).pack()


# ==========================================
# Entry Point
# ==========================================

if __name__ == '__main__':
    print('')
    print('  +==================================================+')
    print('  |   Smart Medicine Dispenser (SMD)                  |')
    print('  |   Native GUI Kiosk Application                   |')
    print('  |   OS: Raspbian / Ubuntu                          |')
    print('  +==================================================+')
    print('')

    app = SMDKiosk()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        app.hardware.cleanup()
        print("\nKiosk stopped.")
